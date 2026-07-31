from django.utils.html import strip_tags


BLOCK_TYPE_DEFINITIONS = {
    "text": {
        "label": "Обычный текст",
        "visible_fields": ("text",),
        "title_label": "Заголовок секции",
        "title_help": "Например: Что важно знать о модели или Как презентовать товар.",
        "caption_label": "Короткая подпись",
        "caption_help": "Необязательно. Можно оставить пустым.",
        "empty_message": "Добавь основной текст блока.",
    },
    "image": {
        "label": "Изображения",
        "visible_fields": ("gallery_uploads", "gallery_preview", "caption"),
        "title_label": "Заголовок галереи",
        "title_help": "Например: Внешний вид модели или Фото в интерьере.",
        "caption_label": "Подпись под галереей",
        "caption_help": "Необязательно. Коротко поясни, что показано на изображениях.",
        "empty_message": "Загрузи хотя бы одно изображение.",
    },
    "video": {
        "label": "Видео",
        "visible_fields": ("video_url", "caption"),
        "title_label": "Заголовок видео",
        "title_help": "Например: Видеообзор или Демонстрация работы.",
        "caption_label": "Короткое пояснение",
        "caption_help": "Необязательно. Можно добавить контекст перед просмотром видео.",
        "empty_message": "Добавь ссылку на видео.",
    },
    "quote": {
        "label": "Цитата",
        "visible_fields": ("text", "caption"),
        "title_label": "Заголовок цитаты",
        "title_help": "Например: Ключевой тезис или Что важно проговорить клиенту.",
        "caption_label": "Подпись к цитате",
        "caption_help": "Необязательно. Например: совет продавцу или источник.",
        "empty_message": "Добавь текст цитаты.",
    },
    "feature": {
        "label": "Фишки товаров",
        "visible_fields": ("items_data",),
        "title_label": "Заголовок секции",
        "title_help": "Например: Фишки модели или Чем товар выделяется.",
        "caption_label": "Короткая подпись",
        "caption_help": "Для этого типа обычно не нужна. Главная работа идёт в карточках ниже.",
        "empty_message": "Добавь хотя бы одну фишку.",
    },
    "sales_script": {
        "label": "Скрипты и возражения",
        "visible_fields": ("items_data",),
        "title_label": "Заголовок секции",
        "title_help": "Например: Скрипты продаж или Готовые формулировки для диалога.",
        "caption_label": "Короткая подпись",
        "caption_help": "Для этого типа обычно не нужна. Главная работа идёт в карточках ниже.",
        "empty_message": "Добавь хотя бы один скрипт продаж.",
    },
    "instruction_step": {
        "label": "Шаг инструкции",
        "visible_fields": ("text", "image", "caption"),
        "title_label": "Название шага",
        "title_help": "Необязательно. Если оставить пустым, шаг будет продолжением предыдущего блока.",
        "caption_label": "Подпись к изображению",
        "caption_help": "Необязательно. Можно коротко пояснить, что показано на изображении.",
        "empty_message": "Добавь текст шага или изображение.",
    },
    "specification": {
        "label": "Характеристики",
        "visible_fields": ("items_data",),
        "title_label": "Заголовок секции",
        "title_help": "Например: Характеристики или Ключевые параметры.",
        "caption_label": "Короткая подпись",
        "caption_help": "Для этого типа обычно не нужна. Характеристики заполняются ниже парами.",
        "empty_message": "Заполни хотя бы одну характеристику.",
    },
    "table": {
        "label": "Обычная таблица",
        "visible_fields": ("items_data",),
        "title_label": "Заголовок таблицы",
        "title_help": "Например: Проценты по срокам или Условия подписки.",
        "caption_label": "Короткая подпись",
        "caption_help": "Необязательно. Можно пояснить таблицу одной строкой.",
        "empty_message": "Добавь хотя бы одну строку таблицы.",
    },
    "comparison_table": {
        "label": "Сравнение товаров",
        "visible_fields": ("items_data",),
        "title_label": "Заголовок таблицы",
        "title_help": "Например: Сравнение моделей или Отличия линейки.",
        "caption_label": "Короткая подпись",
        "caption_help": "Необязательно. Можно пояснить, когда использовать эту таблицу.",
        "empty_message": "Добавь модели и хотя бы одну строку сравнения.",
    },
    "file": {
        "label": "Файл",
        "visible_fields": ("document", "caption"),
        "title_label": "Заголовок файла",
        "title_help": "Например: PDF-презентация или Инструкция для продавца.",
        "caption_label": "Подпись к файлу",
        "caption_help": "Необязательно. Коротко поясни, что внутри.",
        "empty_message": "Прикрепи файл.",
    },
}


ADMIN_BLOCK_TYPE_KEYS = (
    "text",
    "image",
    "video",
    "feature",
    "sales_script",
    "specification",
    "comparison_table",
    "table",
)


PRESET_BLOCKS = {
    "product": (
        {
            "sort_order": 10,
            "block_type": "image",
            "title": "Галерея товара",
            "caption": "Добавь фото товара, комплектации или сценариев использования.",
        },
        {
            "sort_order": 20,
            "block_type": "feature",
            "title": "Фишки модели",
            "items_data": [{"title": "", "description": "", "pitch": ""}],
        },
        {
            "sort_order": 30,
            "block_type": "sales_script",
            "title": "Скрипты продаж",
            "items_data": [{"title": "", "pitch": ""}],
        },
        {
            "sort_order": 40,
            "block_type": "specification",
            "title": "Характеристики",
            "items_data": [],
        },
        {
            "sort_order": 50,
            "block_type": "comparison_table",
            "title": "Сравнение моделей",
            "items_data": {
                "models": ["Модель 1", "Модель 2"],
                "rows": [{"parameter": "", "values": ["", ""]}],
            },
        },
    ),
    "process": (
        {
            "sort_order": 10,
            "block_type": "text",
            "title": "Цель процесса",
            "text": "<p>Опиши, когда сотруднику нужен этот процесс и какой результат он должен получить.</p>",
        },
        {
            "sort_order": 20,
            "block_type": "instruction_step",
            "title": "Шаг 1",
            "text": "<p>Опиши первое действие.</p>",
        },
        {
            "sort_order": 30,
            "block_type": "table",
            "title": "Роли и ответственность",
            "items_data": {
                "headers": ["Что сделать", "Кто отвечает"],
                "rows": [{"left": "", "right": ""}],
            },
        },
    ),
    "instruction": (
        {
            "sort_order": 10,
            "block_type": "text",
            "title": "Когда использовать",
            "text": "<p>Коротко объясни, в какой ситуации нужна эта инструкция.</p>",
        },
        {
            "sort_order": 20,
            "block_type": "instruction_step",
            "title": "Шаг 1",
            "text": "<p>Опиши первое действие.</p>",
        },
        {
            "sort_order": 30,
            "block_type": "instruction_step",
            "title": "Шаг 2",
            "text": "<p>Опиши следующее действие.</p>",
        },
        {
            "sort_order": 40,
            "block_type": "file",
            "title": "Файлы и шаблоны",
            "caption": "Прикрепи PDF, инструкцию или рабочий шаблон, если он нужен.",
        },
    ),
}


def get_admin_block_schema():
    return {
        key: {
            "label": value["label"],
            "visibleFields": list(value["visible_fields"]),
            "titleLabel": value["title_label"],
            "titleHelp": value["title_help"],
            "captionLabel": value["caption_label"],
            "captionHelp": value["caption_help"],
        }
        for key in ADMIN_BLOCK_TYPE_KEYS
        for value in (BLOCK_TYPE_DEFINITIONS[key],)
    }


def normalize_block_items_data(block_type, items_data, characteristic_name_map=None):
    characteristic_name_map = characteristic_name_map or {}

    if block_type == "table":
        if not isinstance(items_data, dict):
            return {"headers": [], "rows": []}

        raw_headers = items_data.get("headers") or []
        if not isinstance(raw_headers, list):
            raw_headers = []
        headers = [
            str(raw_headers[index] or "").strip()
            if index < len(raw_headers)
            else ""
            for index in range(2)
        ]
        rows = []

        for row in items_data.get("rows", []):
            if not isinstance(row, dict):
                continue

            left = str(row.get("left") or "").strip()
            right = str(row.get("right") or "").strip()
            if left or right:
                rows.append({"left": left, "right": right})

        return {"headers": headers, "rows": rows}

    if block_type == "comparison_table":
        if not isinstance(items_data, dict):
            return {"models": [], "rows": []}

        raw_models = [str(model or "").strip() for model in items_data.get("models", [])]
        model_indexes = [index for index, model in enumerate(raw_models) if model]
        models = [raw_models[index] for index in model_indexes]
        rows = []
        for row in items_data.get("rows", []):
            if not isinstance(row, dict):
                continue

            parameter = str(row.get("parameter") or "").strip()
            raw_values = row.get("values") or []
            if not isinstance(raw_values, list):
                raw_values = []
            values = [
                str(raw_values[source_index] or "").strip()
                if source_index < len(raw_values)
                else ""
                for source_index in model_indexes
            ]

            if parameter or any(values):
                rows.append({"parameter": parameter, "values": values})

        return {"models": models, "rows": rows}

    if not isinstance(items_data, list):
        return []

    cleaned_items = []

    for item in items_data:
        if not isinstance(item, dict):
            continue

        normalized = {key: str(item.get(key) or "").strip() for key in item}

        if block_type == "feature":
            if normalized.get("title") or normalized.get("description") or normalized.get("pitch"):
                cleaned_items.append(
                    {
                        "title": normalized.get("title", ""),
                        "description": normalized.get("description", ""),
                        "pitch": normalized.get("pitch", ""),
                    }
                )
        elif block_type == "sales_script":
            description = normalized.get("description") or normalized.get("pitch", "")
            if normalized.get("title") or description:
                cleaned_items.append(
                    {
                        "title": normalized.get("title", ""),
                        "description": description,
                    }
                )
        elif block_type == "specification":
            characteristic_id = normalized.get("characteristic_id", "")
            characteristic_name = (
                characteristic_name_map.get(int(characteristic_id))
                if characteristic_id.isdigit()
                else ""
            ) or ""

            if characteristic_name or normalized.get("name") or normalized.get("value"):
                cleaned_items.append(
                    {
                        "sort_order": normalized.get("sort_order", ""),
                        "characteristic_id": characteristic_id,
                        "name": characteristic_name or normalized.get("name", ""),
                        "value": normalized.get("value", ""),
                    }
                )

    return cleaned_items


def create_preset_blocks(material, preset_key):
    created_blocks = []

    for block_config in PRESET_BLOCKS.get(preset_key, ()):
        created_blocks.append(
            material.blocks.create(
                sort_order=block_config.get("sort_order", 0),
                block_type=block_config.get("block_type", "text"),
                title=block_config.get("title", ""),
                text=block_config.get("text", ""),
                caption=block_config.get("caption", ""),
                video_url=block_config.get("video_url", ""),
                items_data=block_config.get("items_data", []),
            )
        )

    return created_blocks


def has_text(value):
    return bool(strip_tags(str(value or "")).strip())


def has_structured_items(items):
    if not isinstance(items, list):
        return False
    for item in items:
        if not isinstance(item, dict):
            continue
        if any(str(value or "").strip() for value in item.values()):
            return True
    return False


def has_manual_table_rows(table):
    if not isinstance(table, dict):
        return False
    return any(
        isinstance(row, dict)
        and (str(row.get("left") or "").strip() or str(row.get("right") or "").strip())
        for row in table.get("rows", [])
    )


def has_comparison_rows(table):
    if not isinstance(table, dict):
        return False
    models = [model for model in table.get("models", []) if str(model or "").strip()]
    rows = table.get("rows", [])
    if not models or not isinstance(rows, list):
        return False
    return any(
        isinstance(row, dict)
        and (
            str(row.get("parameter") or "").strip()
            or any(str(value or "").strip() for value in row.get("values", []))
        )
        for row in rows
    )


def block_has_content(block):
    block_type = block.block_type

    if block_type in {"text", "quote"}:
        return has_text(block.text)
    if block_type == "image":
        return bool(block.image) or block.gallery_images.exists()
    if block_type == "video":
        return bool(str(block.video_url or "").strip())
    if block_type == "file":
        return bool(block.document)
    if block_type == "instruction_step":
        return has_text(block.text) or bool(block.image)
    if block_type in {"feature", "sales_script", "specification"}:
        return has_structured_items(block.items_data)
    if block_type == "table":
        return has_manual_table_rows(block.items_data)
    if block_type == "comparison_table":
        return has_comparison_rows(block.items_data)

    return has_text(block.text) or has_structured_items(block.items_data)


def get_block_empty_message(block):
    return BLOCK_TYPE_DEFINITIONS.get(block.block_type, {}).get(
        "empty_message",
        "Заполни содержимое блока.",
    )
