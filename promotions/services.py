import csv
import io
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.utils import timezone
from django.utils.text import slugify
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from .models import Promotion, PromotionSource


HEADER_SYNONYMS = {
    "row_key": [
        "id",
        "uid",
        "promo id",
        "promotion id",
        "код",
        "код акции",
        "артикул",
        "sku",
    ],
    "title": [
        "title",
        "name",
        "promotion",
        "promo",
        "название",
        "название акции",
        "акция",
        "предложение",
        "товар",
        "модель",
        "продукт",
    ],
    "badge": [
        "badge",
        "label",
        "tag",
        "метка",
        "лейбл",
        "фишка",
        "плашка",
    ],
    "promotion_type": [
        "type",
        "promo type",
        "promotion type",
        "тип акции",
        "тип",
        "механика акции",
    ],
    "summary": [
        "summary",
        "short description",
        "short text",
        "preview",
        "кратко",
        "краткое описание",
        "анонс",
        "описание для превью",
    ],
    "details": [
        "details",
        "description",
        "full description",
        "long description",
        "условия",
        "подробности",
        "подробное описание",
        "описание",
        "механика",
        "скидка подарок",
        "скидка / подарок",
    ],
    "brand": [
        "brand",
        "бренд",
        "vendor",
        "производитель",
    ],
    "category": [
        "category",
        "категория",
        "product category",
        "группа",
        "направление",
    ],
    "promo_code": [
        "promo code",
        "code",
        "coupon",
        "промокод",
        "код купона",
    ],
    "promo_price": [
        "promo price",
        "price",
        "промоцена",
        "цена",
        "цена акции",
    ],
    "benefit_value": [
        "benefit",
        "discount",
        "gift",
        "скидка подарок",
        "скидка / подарок",
        "скидка/ подарок",
        "скидка",
        "подарок",
        "выгода",
        "размер скидки",
    ],
    "cta_label": [
        "cta label",
        "button text",
        "button",
        "текст кнопки",
        "кнопка",
    ],
    "cta_url": [
        "link",
        "url",
        "cta url",
        "button url",
        "ссылка",
        "ссылка на акцию",
        "url кнопки",
    ],
    "start_date": [
        "start",
        "start date",
        "date start",
        "дата начала",
        "начало",
        "с",
    ],
    "end_date": [
        "end",
        "end date",
        "date end",
        "дата окончания",
        "окончание",
        "по",
    ],
    "sort_order": [
        "sort",
        "sort order",
        "order",
        "порядок",
        "сортировка",
    ],
    "is_featured": [
        "featured",
        "important",
        "highlight",
        "хит",
        "важная",
        "выделить",
    ],
    "is_published": [
        "published",
        "show",
        "visible",
        "active",
        "показывать",
        "опубликовано",
        "активна",
        "публикация",
    ],
    "customer_name": [
        "фио клиента",
        "клиент",
        "имя клиента",
        "покупатель",
    ],
    "phone": [
        "номер телефона",
        "телефон",
        "phone",
    ],
    "salesperson": [
        "ответственный продавец",
        "продавец",
        "менеджер",
    ],
    "acquisition_method": [
        "способ приобретения",
        "способ покупки",
        "способ оплаты",
    ],
    "store": [
        "то",
        "магазин",
        "салон",
        "точка",
    ],
    "status": [
        "статус",
        "состояние",
    ],
    "comment": [
        "комментарий",
        "примечание",
        "коммент",
    ],
    "product_status": [
        "статус по товару",
        "статус товара",
        "наличие",
    ],
    "order_date": [
        "дата заказа",
        "дата",
        "order date",
    ],
}


BRAND_HINTS = (
    "Samsung",
    "Apple",
    "Xiaomi",
    "HONOR",
    "POCO",
    "Infinix",
    "TECNO",
    "Huawei",
    "realme",
    "OnePlus",
    "Nothing",
    "Polaris",
)


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    unpublished: int = 0


def normalize_header(value):
    text = (value or "").strip().casefold().replace("ё", "е")
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def parse_bool(value):
    normalized = normalize_header(value)
    if not normalized:
        return None
    if normalized in {"1", "true", "yes", "y", "да", "активна", "показывать"}:
        return True
    if normalized in {"0", "false", "no", "n", "нет", "скрыть", "неактивна"}:
        return False
    return None


def parse_date_value(value):
    raw_value = (value or "").strip()
    if not raw_value:
        return None

    for date_format in (
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d.%m.%y",
    ):
        try:
            return datetime.strptime(raw_value, date_format).date()
        except ValueError:
            continue
    return None


def parse_excel_date_value(value):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, (int, float)):
        if 20000 <= float(value) <= 60000:
            try:
                converted = from_excel(value)
            except (TypeError, ValueError):
                return None
            if isinstance(converted, datetime):
                return converted.date()
            if isinstance(converted, date):
                return converted
        return None

    return parse_date_value(str(value))


def parse_int_value(value, default=0):
    raw_value = (value or "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def clean_inline_html(text):
    value = (text or "").strip()
    if not value:
        return ""
    return value.replace("\n", "<br>")


def load_payload(url):
    request = Request(
        url,
        headers={"User-Agent": "CorpPortal/1.0 (+https://localhost)"},
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
            charset = response.headers.get_content_charset("utf-8")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Не удалось загрузить таблицу: {exc}") from exc

    return payload, charset


def decode_payload(payload, charset):
    text = payload.decode(charset, errors="replace")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return text


def format_cell_text(value):
    if value in (None, ""):
        return ""

    parsed_date = parse_excel_date_value(value)
    if parsed_date:
        return parsed_date.strftime("%d.%m.%Y")

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()

    if isinstance(value, int):
        return str(value)

    return str(value).strip()


def extract_value(normalized_row, field_name):
    for alias in HEADER_SYNONYMS.get(field_name, []):
        candidate = normalized_row.get(normalize_header(alias), "")
        if candidate:
            return candidate.strip()
    return ""


def detect_promotion_kind(*values):
    normalized_values = [
        normalize_header(format_cell_text(value))
        for value in values
        if value not in (None, "") and normalize_header(format_cell_text(value))
    ]

    if not normalized_values:
        return ""

    primary_values = normalized_values[:2]
    fallback_values = normalized_values[2:]

    for value in primary_values:
        if "подар" in value:
            return Promotion.KIND_GIFT
        if "скид" in value or "промоцен" in value or "промо" in value:
            return Promotion.KIND_PROMO_PRICE
        if "предзаказ" in value:
            return Promotion.KIND_PREORDER

    for value in fallback_values:
        if "подар" in value:
            return Promotion.KIND_GIFT

    for value in fallback_values:
        if "скид" in value or "промоцен" in value or "промо" in value:
            return Promotion.KIND_PROMO_PRICE

    for value in fallback_values:
        if "предзаказ" in value:
            return Promotion.KIND_PREORDER

    return ""


def infer_brand(*values):
    merged = " ".join(format_cell_text(value) for value in values if value not in (None, ""))
    for brand in BRAND_HINTS:
        if brand.casefold() in merged.casefold():
            return brand
    return ""


def fetch_source_rows(source):
    payload, charset = load_payload(source.csv_url)
    text = decode_payload(payload, charset)

    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < source.header_row:
        raise RuntimeError("В таблице нет указанной строки с заголовками.")

    header = rows[source.header_row - 1]
    data_rows = rows[source.header_row :]

    prepared_rows = []
    for index, values in enumerate(data_rows, start=source.header_row + 1):
        if not any(cell.strip() for cell in values):
            continue

        padded = values + [""] * max(0, len(header) - len(values))
        row = {
            header[position].strip(): padded[position].strip()
            for position in range(len(header))
            if header[position].strip()
        }
        prepared_rows.append((index, row))

    return prepared_rows


def build_row_key(source, row_number, raw_row, normalized_row, title, brand, promo_code, start_date, end_date):
    explicit_key = extract_value(normalized_row, "row_key")
    if explicit_key:
        return slugify(explicit_key) or explicit_key

    base_parts = [
        title,
        brand,
        promo_code,
        str(start_date or ""),
        str(end_date or ""),
    ]
    base = "-".join(part for part in base_parts if part).strip()
    slug = slugify(base)
    if slug:
        return slug

    fallback = next((value for value in raw_row.values() if value.strip()), "")
    return slugify(fallback) or f"{source.pk or 'source'}-row-{row_number}"


def map_row_to_promotion(source, row_number, raw_row):
    normalized_row = {
        normalize_header(key): value.strip()
        for key, value in raw_row.items()
        if key
    }

    title = extract_value(normalized_row, "title")
    if not title:
        return None

    action_type = extract_value(normalized_row, "promotion_type")
    summary = extract_value(normalized_row, "summary")
    details = extract_value(normalized_row, "details")
    brand = extract_value(normalized_row, "brand") or infer_brand(
        title,
        summary,
        details,
        promo_price,
        benefit_value,
    )
    category = extract_value(normalized_row, "category")
    promo_code = extract_value(normalized_row, "promo_code")
    promo_price = extract_value(normalized_row, "promo_price")
    benefit_value = extract_value(normalized_row, "benefit_value")
    cta_url = extract_value(normalized_row, "cta_url")
    cta_label = extract_value(normalized_row, "cta_label")
    badge = extract_value(normalized_row, "badge")
    promotion_kind = detect_promotion_kind(action_type, badge, title, summary, details, promo_price)
    start_date = parse_date_value(extract_value(normalized_row, "start_date"))
    end_date = parse_date_value(extract_value(normalized_row, "end_date"))
    is_featured = parse_bool(extract_value(normalized_row, "is_featured")) or False
    explicit_published = parse_bool(extract_value(normalized_row, "is_published"))
    sort_order = parse_int_value(extract_value(normalized_row, "sort_order"), default=row_number * 10)

    row_key = build_row_key(
        source,
        row_number,
        raw_row,
        normalized_row,
        title,
        brand,
        promo_code,
        start_date,
        end_date,
    )

    clean_raw_data = {
        key.strip(): value.strip()
        for key, value in raw_row.items()
        if key and value and value.strip()
    }

    if not badge and action_type:
        badge = action_type

    if not summary:
        summary_parts = []
        if action_type:
            summary_parts.append(action_type.title())
        if brand:
            summary_parts.append(brand)
        summary_parts.append(title)
        if promo_price:
            summary_parts.append(f"Промоцена: {promo_price}")
        if benefit_value:
            benefit_label = "Подарок" if promotion_kind == Promotion.KIND_GIFT else "Скидка"
            summary_parts.append(f"{benefit_label}: {benefit_value}")
        if details:
            summary_parts.append(details)
        summary = ". ".join(part for part in summary_parts if part)
        summary = summary[:220]

    if not details:
        detail_parts = []
        if brand:
            detail_parts.append(f"<p><strong>Бренд:</strong> {brand}</p>")
        if action_type:
            detail_parts.append(f"<p><strong>Тип акции:</strong> {action_type}</p>")
        detail_parts.append(f"<p><strong>Товар:</strong> {title}</p>")
        if promo_price:
            detail_parts.append(f"<p><strong>Промоцена:</strong> {promo_price}</p>")
        if benefit_value:
            benefit_label = "Подарок" if promotion_kind == Promotion.KIND_GIFT else "Скидка"
            detail_parts.append(
                f"<p><strong>{benefit_label}:</strong> {clean_inline_html(benefit_value)}</p>"
            )
        if details:
            detail_parts.append(f"<p><strong>Условия:</strong> {clean_inline_html(details)}</p>")
        details = "".join(detail_parts)

    if not badge and promo_code:
        badge = f"Промокод {promo_code}"

    return {
        "source": source,
        "source_row_key": row_key,
        "title": title,
        "promotion_kind": promotion_kind,
        "badge": badge,
        "summary": summary,
        "details": details,
        "brand": brand,
        "category": category,
        "promo_price": promo_price,
        "benefit_value": benefit_value,
        "promo_code": promo_code,
        "cta_label": cta_label,
        "cta_url": cta_url,
        "start_date": start_date,
        "end_date": end_date,
        "sort_order": sort_order,
        "is_featured": is_featured,
        "is_published": (
            explicit_published if explicit_published is not None else source.auto_publish_imported
        ),
        "raw_data": clean_raw_data,
        "imported_at": timezone.now(),
    }


def build_worksheet_rows(worksheet):
    values_rows = list(worksheet.iter_rows(values_only=True))
    if not values_rows:
        return []

    header_index = 0
    for index, row in enumerate(values_rows[:5]):
        normalized_values = {
            normalize_header(format_cell_text(value))
            for value in row
            if format_cell_text(value)
        }
        if "модель" in normalized_values and (
            "дата заказа" in normalized_values or "фио клиента" in normalized_values
        ):
            header_index = index
            break

    header = [format_cell_text(value) for value in values_rows[header_index]]
    data_rows = values_rows[header_index + 1 :]

    prepared_rows = []
    for row_number, values in enumerate(data_rows, start=header_index + 2):
        if not any(format_cell_text(value) for value in values):
            continue

        row = {}
        for position, header_value in enumerate(header):
            if not header_value:
                continue
            cell_value = values[position] if position < len(values) else ""
            row[header_value] = format_cell_text(cell_value)

        if row:
            prepared_rows.append((row_number, row))

    return prepared_rows


def summarize_counter(counter):
    return ", ".join(f"{key}: {count}" for key, count in counter.most_common() if key)


def map_worksheet_to_preorder_promotion(source, worksheet, sort_order):
    prepared_rows = build_worksheet_rows(worksheet)
    preorder_entries = []
    model_names = []
    statuses = Counter()
    acquisition_methods = Counter()
    parsed_dates = []

    for row_number, raw_row in prepared_rows:
        normalized_row = {
            normalize_header(key): value.strip()
            for key, value in raw_row.items()
            if key
        }

        model_name = extract_value(normalized_row, "title")
        customer_name = extract_value(normalized_row, "customer_name")
        phone = extract_value(normalized_row, "phone")
        salesperson = extract_value(normalized_row, "salesperson")
        acquisition_method = extract_value(normalized_row, "acquisition_method")
        store = extract_value(normalized_row, "store")
        status = extract_value(normalized_row, "status")
        comment = extract_value(normalized_row, "comment")
        product_status = extract_value(normalized_row, "product_status")
        order_date_raw = extract_value(normalized_row, "order_date")
        order_date = parse_excel_date_value(order_date_raw) or parse_date_value(order_date_raw)

        if not any(
            [
                model_name,
                customer_name,
                phone,
                salesperson,
                acquisition_method,
                status,
                comment,
                product_status,
            ]
        ):
            continue

        if model_name:
            model_names.append(model_name)
        if status:
            statuses[status] += 1
        if acquisition_method:
            acquisition_methods[acquisition_method] += 1
        if order_date:
            parsed_dates.append(order_date)

        preorder_entries.append(
            {
                "row_number": row_number,
                "model": model_name,
                "order_date": order_date.strftime("%d.%m.%Y") if order_date else order_date_raw,
                "customer_name": customer_name,
                "phone": phone,
                "salesperson": salesperson,
                "acquisition_method": acquisition_method,
                "store": store,
                "status": status,
                "comment": comment,
                "product_status": product_status,
            }
        )

    if not preorder_entries:
        return None

    unique_models = []
    seen_models = set()
    for model_name in model_names:
        normalized = normalize_header(model_name)
        if normalized and normalized not in seen_models:
            unique_models.append(model_name)
            seen_models.add(normalized)

    title = worksheet.title.strip()
    brand = infer_brand(title, *unique_models)
    status_summary = summarize_counter(statuses)
    acquisition_summary = summarize_counter(acquisition_methods)
    preview_models = ", ".join(unique_models[:3])

    summary_parts = [
        f"Предзаказ по листу «{title}».",
        f"Заявок: {len(preorder_entries)}.",
    ]
    if preview_models:
        summary_parts.append(f"Модели: {preview_models}.")
    if status_summary:
        summary_parts.append(f"Статусы: {status_summary}.")
    summary = " ".join(summary_parts)

    details_parts = [
        f"<p><strong>Лист таблицы:</strong> {title}</p>",
        f"<p><strong>Всего заявок:</strong> {len(preorder_entries)}</p>",
    ]
    if preview_models:
        details_parts.append(
            f"<p><strong>Основные модели:</strong> {clean_inline_html(preview_models)}</p>"
        )
    if status_summary:
        details_parts.append(f"<p><strong>Статусы:</strong> {clean_inline_html(status_summary)}</p>")
    if acquisition_summary:
        details_parts.append(
            f"<p><strong>Способы приобретения:</strong> {clean_inline_html(acquisition_summary)}</p>"
        )

    return {
        "source": source,
        "source_row_key": slugify(f"{worksheet.title}-{sort_order}") or f"worksheet-{sort_order}",
        "title": title,
        "promotion_kind": Promotion.KIND_PREORDER,
        "badge": "Предзаказ",
        "summary": summary[:220],
        "details": "".join(details_parts),
        "brand": brand,
        "category": "Предзаказы",
        "promo_code": "",
        "cta_label": "",
        "cta_url": "",
        "start_date": min(parsed_dates) if parsed_dates else None,
        "end_date": None,
        "sort_order": sort_order,
        "is_featured": True,
        "is_published": source.auto_publish_imported,
        "raw_data": {
            "Лист таблицы": title,
            "Всего заявок": str(len(preorder_entries)),
            "Модели": ", ".join(unique_models[:6]),
            "Статусы": status_summary,
            "Способы приобретения": acquisition_summary,
            "preorder_entries": preorder_entries,
        },
        "imported_at": timezone.now(),
    }


def upsert_mapped_promotion(source, mapped_data, result, seen_keys):
    seen_keys.append(mapped_data["source_row_key"])

    existing = (
        Promotion.objects.filter(source=source, source_row_key=mapped_data["source_row_key"])
        .order_by("pk")
        .first()
    )

    if existing and not existing.sync_with_source:
        result.skipped += 1
        return

    if existing:
        for field_name, field_value in mapped_data.items():
            setattr(existing, field_name, field_value)
        existing.save()
        result.updated += 1
        return

    Promotion.objects.create(**mapped_data)
    result.created += 1


def finalize_source_import(source, seen_keys, result):
    if source.archive_missing_on_import and seen_keys:
        result.unpublished = (
            Promotion.objects.filter(source=source, sync_with_source=True, is_published=True)
            .exclude(source_row_key__in=seen_keys)
            .update(is_published=False)
        )

    source.last_imported_at = timezone.now()
    source.last_import_error = ""
    source.save(update_fields=["last_imported_at", "last_import_error", "updated_at"])


def import_preorders_from_last_worksheets(source):
    payload, _ = load_payload(source.xlsx_url)

    try:
        workbook = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as exc:
        raise RuntimeError(f"Не удалось прочитать Excel-книгу: {exc}") from exc

    result = ImportResult()
    seen_keys = []

    try:
        worksheet_count = max(source.worksheets_to_import, 1)
        worksheets = workbook.worksheets[-worksheet_count:]

        for index, worksheet in enumerate(worksheets, start=1):
            mapped_data = map_worksheet_to_preorder_promotion(
                source,
                worksheet,
                index * 10,
            )
            if not mapped_data:
                result.skipped += 1
                continue

            upsert_mapped_promotion(source, mapped_data, result, seen_keys)

        finalize_source_import(source, seen_keys, result)
        return result
    finally:
        workbook.close()


def import_promotions_from_source(source):
    if source.import_mode == PromotionSource.IMPORT_MODE_LAST_WORKSHEETS:
        return import_preorders_from_last_worksheets(source)

    result = ImportResult()
    seen_keys = []
    rows = fetch_source_rows(source)

    for row_number, raw_row in rows:
        mapped_data = map_row_to_promotion(source, row_number, raw_row)
        if not mapped_data:
            result.skipped += 1
            continue

        upsert_mapped_promotion(source, mapped_data, result, seen_keys)

    finalize_source_import(source, seen_keys, result)
    return result
