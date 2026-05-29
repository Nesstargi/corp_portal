(function () {
  var BLOCK_FIELD_NAMES = [
    "caption",
    "items_data",
    "text",
    "gallery_uploads",
    "gallery_preview",
    "image",
    "video_url",
    "document",
  ];
  var BLOCK_TYPE_FIELDS = {
    text: ["text"],
    image: ["gallery_uploads", "gallery_preview", "caption"],
    video: ["video_url", "caption"],
    quote: ["text", "caption"],
    feature: ["items_data"],
    sales_script: ["items_data"],
    specification: ["items_data"],
    comparison_table: ["items_data"],
    file: ["document", "caption"],
  };
  var BLOCK_FIELD_COPY = {
    text: {
      titleLabel: "Заголовок секции",
      titleHelp: "Например: Что важно знать о модели или Как презентовать товар.",
      captionLabel: "Короткая подпись",
      captionHelp: "Необязательно. Можно оставить пустым.",
    },
    image: {
      titleLabel: "Заголовок галереи",
      titleHelp: "Например: Внешний вид модели или Фото в интерьере.",
      captionLabel: "Подпись под галереей",
      captionHelp: "Необязательно. Коротко поясни, что показано на изображениях.",
    },
    video: {
      titleLabel: "Заголовок видео",
      titleHelp: "Например: Видеообзор или Демонстрация работы.",
      captionLabel: "Короткое пояснение",
      captionHelp: "Необязательно. Можно добавить контекст перед просмотром видео.",
    },
    quote: {
      titleLabel: "Заголовок цитаты",
      titleHelp: "Например: Ключевой тезис или Что важно проговорить клиенту.",
      captionLabel: "Подпись к цитате",
      captionHelp: "Необязательно. Например: совет продавцу или источник.",
    },
    feature: {
      titleLabel: "Заголовок секции",
      titleHelp: "Например: Фишки модели или Чем товар выделяется.",
      captionLabel: "Короткая подпись",
      captionHelp: "Для этого типа обычно не нужна. Главная работа идёт в карточках ниже.",
    },
    sales_script: {
      titleLabel: "Заголовок секции",
      titleHelp: "Например: Скрипты продаж или Готовые формулировки для диалога.",
      captionLabel: "Короткая подпись",
      captionHelp: "Для этого типа обычно не нужна. Главная работа идёт в карточках ниже.",
    },
    specification: {
      titleLabel: "Заголовок секции",
      titleHelp: "Например: Характеристики или Ключевые параметры.",
      captionLabel: "Короткая подпись",
      captionHelp: "Для этого типа обычно не нужна. Характеристики заполняются ниже парами.",
    },
    comparison_table: {
      titleLabel: "Заголовок таблицы",
      titleHelp: "Например: Сравнение моделей или Отличия линейки.",
      captionLabel: "Короткая подпись",
      captionHelp: "Необязательно. Можно пояснить, когда использовать эту таблицу.",
    },
    file: {
      titleLabel: "Заголовок файла",
      titleHelp: "Например: PDF-презентация или Инструкция для продавца.",
      captionLabel: "Подпись к файлу",
      captionHelp: "Необязательно. Коротко поясни, что внутри.",
    },
  };
  var BLOCK_ITEM_SCHEMAS = {
    feature: {
      sectionTitle: "Фишки внутри блока",
      emptyLabel:
        "Каждая фишка состоит из названия, короткого описания и фразы, как её подать клиенту.",
      addLabel: "Добавить ещё фишку",
      itemLabel: "Фишка",
      cardModifier: "learning-block-items__card--feature",
      fields: [
        {
          key: "title",
          label: "Название фишки",
          placeholder: "Например: Лазерная навигация",
          multiline: false,
          wide: true,
        },
        {
          key: "description",
          label: "Краткое описание",
          placeholder: "Коротко опиши, в чём суть этой фишки.",
          multiline: true,
          rows: 3,
        },
        {
          key: "pitch",
          label: "Как преподносить клиенту",
          placeholder: "Фраза, которой продавец может объяснить пользу клиенту.",
          multiline: true,
          rows: 3,
        },
      ],
    },
    sales_script: {
      sectionTitle: "Скрипты внутри блока",
      emptyLabel:
        "Добавляй готовые формулировки, которые продавец сможет быстро использовать в разговоре.",
      addLabel: "Добавить ещё скрипт",
      itemLabel: "Скрипт",
      cardModifier: "learning-block-items__card--script",
      fields: [
        {
          key: "title",
          label: "Название скрипта",
          placeholder: "Например: Для клиента с животными",
          multiline: false,
        },
        {
          key: "pitch",
          label: "Как проговаривать",
          placeholder: "Напиши готовую фразу или короткий сценарий разговора.",
          multiline: true,
          rows: 4,
        },
      ],
    },
    specification: {
      sectionTitle: "Характеристики внутри блока",
      emptyLabel:
        "Ниже уже можно подтянуть характеристики из выбранной категории и при необходимости добавить свои строки.",
      addLabel: "Добавить ещё одну характеристику",
      itemLabel: "Характеристика",
      layout: "table",
      actions: ["import", "catalog"],
      fields: [
        {
          key: "sort_order",
          label: "Порядок",
          placeholder: "0",
          multiline: false,
          type: "number",
          inline: true,
        },
        {
          key: "characteristic_id",
          label: "Характеристика",
          placeholder: "Выберите характеристику",
          type: "select",
          inline: true,
        },
        {
          key: "value",
          label: "Значение",
          placeholder: "",
          multiline: false,
          inline: true,
        },
      ],
    },
  };
  var categoryCharacteristicMapCache = null;
  var allCharacteristicsCache = null;
  var adminConfigCache = null;

  function setSectionVisibility(selector, hidden) {
    document.querySelectorAll(selector).forEach(function (section) {
      section.classList.toggle("is-hidden", hidden);
    });
  }

  function getMaterialTypeValue() {
    var materialType = document.getElementById("id_material_type");
    return materialType ? materialType.value : "";
  }

  function isProductMode() {
    return getMaterialTypeValue() === "product";
  }

  function toggleLearningMode() {
    var productMode = isProductMode();
    setSectionVisibility(".learning-admin-section.general-only", productMode);
    setSectionVisibility(".learning-admin-anchor.general-only", productMode);
  }

  function getBlockInlineRows() {
    return document.querySelectorAll('.inline-related[id^="blocks-"]');
  }

  function getFieldRow(fieldElement) {
    if (!fieldElement) {
      return null;
    }

    return (
      fieldElement.closest(".form-row") ||
      fieldElement.closest(".fieldBox") ||
      fieldElement.closest(".aligned") ||
      fieldElement.parentElement
    );
  }

  function findFieldContainer(row, fieldName) {
    return (
      row.querySelector('[id$="-' + fieldName + '"]') ||
      row.querySelector(".field-" + fieldName)
    );
  }

  function setFieldVisibility(fieldElement, hidden) {
    var fieldRow = getFieldRow(fieldElement) || fieldElement;
    if (fieldRow) {
      fieldRow.classList.toggle("is-hidden", hidden);
    }
  }

  function getBlockType(row) {
    var typeSelect = row.querySelector('select[id$="-block_type"]');
    return typeSelect ? typeSelect.value : "";
  }

  function getStructuredItemsInput(row) {
    return row.querySelector('[id$="-items_data"]');
  }

  function readJsonScript(id, fallback) {
    var element = document.getElementById(id);
    if (!element) {
      return fallback;
    }

    try {
      return JSON.parse(element.textContent || "");
    } catch (error) {
      return fallback;
    }
  }

  function getCategoryCharacteristicMap() {
    if (categoryCharacteristicMapCache !== null) {
      return categoryCharacteristicMapCache;
    }
    categoryCharacteristicMapCache = readJsonScript("learning-category-characteristics-map", {});
    return categoryCharacteristicMapCache;
  }

  function getAllCharacteristics() {
    if (allCharacteristicsCache !== null) {
      return allCharacteristicsCache;
    }
    allCharacteristicsCache = readJsonScript("learning-all-product-characteristics", []);
    return allCharacteristicsCache;
  }

  function getAdminConfig() {
    if (adminConfigCache !== null) {
      return adminConfigCache;
    }
    adminConfigCache = readJsonScript("learning-admin-config", {});
    return adminConfigCache;
  }

  function getSelectedCategoryIds() {
    var selectedValues = [];
    var selectedBox = document.getElementById("id_categories_to");

    if (selectedBox) {
      Array.prototype.forEach.call(selectedBox.options, function (option) {
        selectedValues.push(String(option.value));
      });
      return selectedValues;
    }

    var select = document.getElementById("id_categories");
    if (!select) {
      return selectedValues;
    }

    Array.prototype.forEach.call(select.selectedOptions || [], function (option) {
      selectedValues.push(String(option.value));
    });
    return selectedValues;
  }

  function getRecommendedCharacteristics() {
    var categoryMap = getCategoryCharacteristicMap();
    var selectedCategoryIds = getSelectedCategoryIds();
    var unique = new Map();

    selectedCategoryIds.forEach(function (categoryId) {
      (categoryMap[categoryId] || []).forEach(function (item) {
        var key = String(item.id);
        var current = unique.get(key);

        if (!current) {
          unique.set(key, item);
          return;
        }

        var currentOrder = Number(current.sort_order || 0);
        var nextOrder = Number(item.sort_order || 0);
        if (nextOrder < currentOrder) {
          unique.set(key, item);
        }
      });
    });

    return Array.from(unique.values()).sort(function (left, right) {
      var leftOrder = Number(left.sort_order || 0);
      var rightOrder = Number(right.sort_order || 0);
      if (leftOrder !== rightOrder) {
        return leftOrder - rightOrder;
      }
      return String(left.name || "").localeCompare(String(right.name || ""), "ru");
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function parseItems(input) {
    if (!input || !input.value) {
      return [];
    }

    try {
      var parsed = JSON.parse(input.value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function parseComparisonTable(input) {
    var fallback = {
      models: ["Модель 1", "Модель 2"],
      rows: [
        {
          parameter: "",
          values: ["", ""],
        },
      ],
    };

    if (!input || !input.value) {
      return fallback;
    }

    try {
      var parsed = JSON.parse(input.value);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        return fallback;
      }

      var models = Array.isArray(parsed.models)
        ? parsed.models
            .map(function (model) {
              return String(model || "").trim();
            })
            .filter(Boolean)
        : [];
      if (!models.length) {
        models = fallback.models.slice();
      }

      var rows = Array.isArray(parsed.rows)
        ? parsed.rows.map(function (row) {
            var values = Array.isArray(row.values) ? row.values : [];
            return {
              parameter: String(row.parameter || "").trim(),
              values: models.map(function (_model, index) {
                return String(values[index] || "").trim();
              }),
            };
          })
        : [];

      if (!rows.length) {
        rows = [
          {
            parameter: "",
            values: models.map(function () {
              return "";
            }),
          },
        ];
      }

      return {
        models: models,
        rows: rows,
      };
    } catch (error) {
      return fallback;
    }
  }

  function writeItems(input, items) {
    if (!input) {
      return;
    }
    input.value = JSON.stringify(items);
  }

  function writeComparisonTable(input, table) {
    if (!input) {
      return;
    }
    input.value = JSON.stringify(table || { models: [], rows: [] });
  }

  function isItemFilled(item) {
    return Object.keys(item || {}).some(function (key) {
      return String(item[key] || "").trim();
    });
  }

  function isSpecificationItemsEmpty(items) {
    return !items.length || items.every(function (item) {
      return !isItemFilled(item);
    });
  }

  function buildRecommendedSpecificationItems() {
    return getRecommendedCharacteristics().map(function (item) {
      return {
        sort_order: String(item.sort_order || ""),
        characteristic_id: String(item.id),
        name: item.name,
        value: "",
      };
    });
  }

  function normalizeCompareParameter(value) {
    return String(value || "").trim().toLocaleLowerCase("ru");
  }

  function buildRecommendedComparisonRows(models) {
    return getRecommendedCharacteristics().map(function (item) {
      return {
        parameter: item.name,
        values: models.map(function () {
          return "";
        }),
      };
    });
  }

  function ensureSpecificationItemsSeeded(row) {
    if (getBlockType(row) !== "specification") {
      return;
    }

    var input = getStructuredItemsInput(row);
    var items = parseItems(input);

    if (!isSpecificationItemsEmpty(items)) {
      return;
    }

    var recommendedItems = buildRecommendedSpecificationItems();
    writeItems(input, recommendedItems.length ? recommendedItems : [{}]);
  }

  function buildCharacteristicOptionsHtml(selectedValue, fallbackName) {
    var allCharacteristics = getAllCharacteristics();
    var recommendedCharacteristics = getRecommendedCharacteristics();
    var recommendedIds = new Set(
      recommendedCharacteristics.map(function (item) {
        return String(item.id);
      })
    );
    var others = allCharacteristics.filter(function (item) {
      return !recommendedIds.has(String(item.id));
    });
    var html = ['<option value="">Выберите характеристику</option>'];

    function buildOptions(items) {
      return items
        .map(function (item) {
          var optionValue = String(item.id);
          return (
            '<option value="' +
            escapeHtml(optionValue) +
            '"' +
            (optionValue === String(selectedValue || "") ? " selected" : "") +
            ">" +
            escapeHtml(item.name) +
            "</option>"
          );
        })
        .join("");
    }

    if (recommendedCharacteristics.length) {
      html.push(
        '<optgroup label="Характеристики выбранной категории">' +
          buildOptions(recommendedCharacteristics) +
          "</optgroup>"
      );
    }

    if (others.length) {
      html.push(
        '<optgroup label="Другие характеристики каталога">' +
          buildOptions(others) +
          "</optgroup>"
      );
    }

    if (
      selectedValue &&
      !allCharacteristics.some(function (item) {
        return String(item.id) === String(selectedValue);
      })
    ) {
      html.push(
        '<option value="' +
          escapeHtml(selectedValue) +
          '" selected>' +
          escapeHtml(fallbackName || "Текущая характеристика") +
          "</option>"
      );
    }

    return html.join("");
  }

  function updateFieldCopy(row) {
    var blockType = getBlockType(row);
    var copy = BLOCK_FIELD_COPY[blockType] || BLOCK_FIELD_COPY.text;

    [
      {
        fieldName: "title",
        label: copy.titleLabel,
        help: copy.titleHelp,
      },
      {
        fieldName: "caption",
        label: copy.captionLabel,
        help: copy.captionHelp,
      },
    ].forEach(function (config) {
      var field = findFieldContainer(row, config.fieldName);
      var fieldRow = getFieldRow(field);
      if (!fieldRow) {
        return;
      }

      var label = fieldRow.querySelector("label");
      if (label) {
        label.textContent = config.label + ":";
      }

      var help = fieldRow.querySelector(".help");
      if (help) {
        help.textContent = config.help;
      }
    });
  }

  function buildControl(field, item, itemIndex) {
    var value = item[field.key] || "";
    var placeholder = escapeHtml(field.placeholder || "");
    var placeholderAttr = placeholder ? ' placeholder="' + placeholder + '"' : "";

    if (field.type === "select") {
      return (
        '<select data-block-item-field="' +
        field.key +
        '" data-item-index="' +
        itemIndex +
        '">' +
        buildCharacteristicOptionsHtml(value, item.name) +
        "</select>"
      );
    }

    if (field.type === "number") {
      return (
        '<input type="number" value="' +
        escapeHtml(value) +
        '"' +
        placeholderAttr +
        ' data-block-item-field="' +
        field.key +
        '" data-item-index="' +
        itemIndex +
        '">'
      );
    }

    if (field.multiline) {
      return (
        '<textarea rows="' +
        (field.rows || 4) +
        '"' +
        placeholderAttr +
        ' data-block-item-field="' +
        field.key +
        '" data-item-index="' +
        itemIndex +
        '">' +
        escapeHtml(value) +
        "</textarea>"
      );
    }

    return (
      '<input type="text" value="' +
      escapeHtml(value) +
      '"' +
      placeholderAttr +
      ' data-block-item-field="' +
      field.key +
      '" data-item-index="' +
      itemIndex +
      '">'
    );
  }

  function renderItemFields(item, itemIndex, schema) {
    return schema.fields
      .map(function (field) {
        var classes = ["learning-block-items__field"];
        if (field.inline) {
          classes.push("learning-block-items__field--inline");
        }
        if (field.wide) {
          classes.push("learning-block-items__field--wide");
        }

        return (
          '<div class="' +
          classes.join(" ") +
          '">' +
          '<label class="learning-block-items__field-label">' +
          field.label +
          "</label>" +
          buildControl(field, item, itemIndex) +
          "</div>"
        );
      })
      .join("");
  }

  function renderSchemaActions(schema) {
    var config = getAdminConfig();
    var actions = [];

    if ((schema.actions || []).indexOf("import") >= 0) {
      actions.push(
        '<button type="button" class="learning-block-items__toolbar-button" data-import-category-characteristics="true">' +
          "Подтянуть характеристики из категории" +
          "</button>"
      );
    }

    if ((schema.actions || []).indexOf("catalog") >= 0 && config.productCharacteristicAddUrl) {
      actions.push(
        '<a class="learning-block-items__toolbar-button" href="' +
          escapeHtml(config.productCharacteristicAddUrl) +
          '" target="_blank" rel="noreferrer">' +
          "Создать новую характеристику" +
          "</a>"
      );
    }

    if (!actions.length) {
      return "";
    }

    return (
      '<div class="learning-block-items__toolbar' +
      (schema.layout === "table" ? " learning-block-items__toolbar--table" : "") +
      '">' +
      actions.join("") +
      "</div>"
    );
  }

  function renderSpecificationRows(items, schema) {
    var rows = items
      .map(function (item, itemIndex) {
        return (
          '<tr class="learning-spec-table__row" data-block-item="' +
          itemIndex +
          '">' +
          '<td class="learning-spec-table__cell learning-spec-table__cell--order">' +
          buildControl(schema.fields[0], item, itemIndex) +
          "</td>" +
          '<td class="learning-spec-table__cell learning-spec-table__cell--characteristic">' +
          buildControl(schema.fields[1], item, itemIndex) +
          "</td>" +
          '<td class="learning-spec-table__cell learning-spec-table__cell--value">' +
          buildControl(schema.fields[2], item, itemIndex) +
          "</td>" +
          '<td class="learning-spec-table__cell learning-spec-table__cell--delete">' +
          '<button type="button" class="learning-spec-table__remove" data-remove-block-item="' +
          itemIndex +
          '">Удалить</button>' +
          "</td>" +
          "</tr>"
        );
      })
      .join("");

    return (
      '<table class="learning-spec-table">' +
      "<thead>" +
      "<tr>" +
      '<th class="learning-spec-table__heading learning-spec-table__heading--order">Порядок</th>' +
      '<th class="learning-spec-table__heading learning-spec-table__heading--characteristic">Характеристика</th>' +
      '<th class="learning-spec-table__heading learning-spec-table__heading--value">Значение</th>' +
      '<th class="learning-spec-table__heading learning-spec-table__heading--delete">Удалить?</th>' +
      "</tr>" +
      "</thead>" +
      '<tbody class="learning-spec-table__body">' +
      rows +
      "</tbody>" +
      "</table>"
    );
  }

  function renderItemCard(item, itemIndex, schema) {
    var cardClasses = ["learning-block-items__card"];
    if (schema.cardModifier) {
      cardClasses.push(schema.cardModifier);
    }

    return (
      '<div class="' +
      cardClasses.join(" ") +
      '" data-block-item="' +
      itemIndex +
      '">' +
      '<div class="learning-block-items__card-header">' +
      '<div class="learning-block-items__card-title">' +
      schema.itemLabel +
      " " +
      (itemIndex + 1) +
      "</div>" +
      '<button type="button" class="button learning-block-items__remove" data-remove-block-item="' +
      itemIndex +
      '">Удалить</button>' +
      "</div>" +
      '<div class="learning-block-items__fields">' +
      renderItemFields(item, itemIndex, schema) +
      "</div>" +
      "</div>"
    );
  }

  function renderComparisonTableEditor(row) {
    var input = getStructuredItemsInput(row);
    var editor = row.querySelector("[data-block-items-editor]");
    if (!input || !editor) {
      return;
    }

    var table = parseComparisonTable(input);
    writeComparisonTable(input, table);

    var renderKey = "comparison_table::" + JSON.stringify(table);
    if (editor.dataset.renderKey === renderKey) {
      return;
    }

    var modelFields = table.models
      .map(function (model, modelIndex) {
        return (
          '<article class="learning-compare-editor__model" data-comparison-model="' +
          modelIndex +
          '">' +
          '<label class="learning-compare-editor__model-label">' +
          '<span>Колонка ' +
          (modelIndex + 1) +
          "</span>" +
          '<input type="text" value="' +
          escapeHtml(model) +
          '" placeholder="Название модели" data-comparison-model-name="' +
          modelIndex +
          '">' +
          "</label>" +
          '<button type="button" class="learning-compare-editor__icon-button" title="Удалить модель" aria-label="Удалить модель" data-remove-comparison-model="' +
          modelIndex +
          '">×</button>' +
          "</article>"
        );
      })
      .join("");

    var dataColumnCount = table.models.length + 1;
    var columnMarkup =
      "<colgroup>" +
      '<col class="learning-compare-editor__column learning-compare-editor__column--data">' +
      table.models
        .map(function () {
          return '<col class="learning-compare-editor__column learning-compare-editor__column--data">';
        })
        .join("") +
      '<col class="learning-compare-editor__column learning-compare-editor__column--action">' +
      "</colgroup>";

    var rowMarkup = table.rows
      .map(function (tableRow, rowIndex) {
        var valueCells = table.models
          .map(function (modelName, modelIndex) {
            return (
              '<td class="learning-compare-editor__cell">' +
              '<label class="learning-compare-editor__mobile-label">' +
              escapeHtml(modelName || "Модель " + (modelIndex + 1)) +
              "</label>" +
              '<textarea rows="2" data-comparison-cell="' +
              rowIndex +
              ":" +
              modelIndex +
              '">' +
              escapeHtml(tableRow.values[modelIndex] || "") +
              "</textarea>" +
              "</td>"
            );
          })
          .join("");

        return (
          '<tr data-comparison-row="' +
          rowIndex +
          '">' +
          '<td class="learning-compare-editor__cell learning-compare-editor__cell--parameter">' +
          '<label class="learning-compare-editor__field-label">Параметр</label>' +
          '<textarea rows="2" placeholder="Например: Время работы" data-comparison-parameter="' +
          rowIndex +
          '">' +
          escapeHtml(tableRow.parameter || "") +
          "</textarea>" +
          "</td>" +
          valueCells +
          '<td class="learning-compare-editor__cell learning-compare-editor__cell--delete">' +
          '<button type="button" class="learning-compare-editor__icon-button learning-compare-editor__icon-button--danger" title="Удалить строку" aria-label="Удалить строку" data-remove-comparison-row="' +
          rowIndex +
          '">×</button>' +
          "</td>" +
          "</tr>"
        );
      })
      .join("");

    editor.innerHTML =
      '<div class="learning-compare-editor">' +
      '<div class="learning-compare-editor__head">' +
      "<div>" +
      '<div class="learning-compare-editor__title">Сравнительная таблица</div>' +
      '<p class="learning-compare-editor__help">Модели будут колонками, параметры — строками. Пустые значения на сайте покажутся как «Не указано».</p>' +
      "</div>" +
      '<div class="learning-compare-editor__count">' +
      table.models.length +
      " моделей · " +
      table.rows.length +
      " строк" +
      "</div>" +
      "</div>" +
      '<div class="learning-compare-editor__section-title">Модели для сравнения</div>' +
      '<div class="learning-compare-editor__models">' +
      modelFields +
      '<button type="button" class="learning-compare-editor__add-card" data-add-comparison-model="true"><span>+</span>Добавить модель</button>' +
      "</div>" +
      '<div class="learning-compare-editor__section-title">Параметры и значения</div>' +
      '<div class="learning-compare-editor__toolbar">' +
      '<button type="button" class="learning-block-items__toolbar-button" data-import-category-characteristics="true">Подтянуть характеристики из категории</button>' +
      "</div>" +
      '<div class="learning-compare-editor__table-wrap">' +
      '<table class="learning-compare-editor__table" style="--comparison-data-columns: ' +
      dataColumnCount +
      '">' +
      columnMarkup +
      '<thead><tr><th class="learning-compare-editor__heading learning-compare-editor__heading--parameter">Параметр</th>' +
      table.models
        .map(function (model) {
          return '<th class="learning-compare-editor__heading">' + escapeHtml(model) + "</th>";
        })
        .join("") +
      '<th class="learning-compare-editor__heading learning-compare-editor__heading--delete"><span class="learning-compare-editor__sr">Действие</span></th></tr></thead>' +
      "<tbody>" +
      rowMarkup +
      "</tbody></table></div>" +
      '<button type="button" class="learning-compare-editor__add-row" data-add-comparison-row="true"><span>+</span>Добавить параметр</button>' +
      "</div>";
    editor.dataset.renderKey = renderKey;
  }

  function collectComparisonTableFromEditor(row) {
    var input = getStructuredItemsInput(row);
    var editor = row.querySelector("[data-block-items-editor]");
    if (!input || !editor) {
      return;
    }

    var models = [];
    editor.querySelectorAll("[data-comparison-model-name]").forEach(function (field) {
      var name = String(field.value || "").trim();
      if (name) {
        models.push(name);
      }
    });

    if (!models.length) {
      models = ["Модель 1", "Модель 2"];
    }

    var rows = [];
    editor.querySelectorAll("[data-comparison-row]").forEach(function (rowElement) {
      var rowIndex = Number(rowElement.dataset.comparisonRow || 0);
      var parameterInput = rowElement.querySelector("[data-comparison-parameter]");
      var values = models.map(function (_model, modelIndex) {
        var cell = rowElement.querySelector('[data-comparison-cell="' + rowIndex + ":" + modelIndex + '"]');
        return cell ? String(cell.value || "").trim() : "";
      });
      var parameter = parameterInput ? String(parameterInput.value || "").trim() : "";

      if (parameter || values.some(Boolean)) {
        rows.push({
          parameter: parameter,
          values: values,
        });
      }
    });

    if (!rows.length) {
      rows = [
        {
          parameter: "",
          values: models.map(function () {
            return "";
          }),
        },
      ];
    }

    writeComparisonTable(input, {
      models: models,
      rows: rows,
    });
  }

  function addComparisonModel(row) {
    var input = getStructuredItemsInput(row);
    var table = parseComparisonTable(input);
    table.models.push("Модель " + (table.models.length + 1));
    table.rows = table.rows.map(function (tableRow) {
      return {
        parameter: tableRow.parameter || "",
        values: table.models.map(function (_model, index) {
          return tableRow.values[index] || "";
        }),
      };
    });
    writeComparisonTable(input, table);
    renderComparisonTableEditor(row);
  }

  function removeComparisonModel(row, modelIndex) {
    var input = getStructuredItemsInput(row);
    var table = parseComparisonTable(input);
    if (table.models.length <= 1) {
      return;
    }

    table.models = table.models.filter(function (_model, index) {
      return index !== modelIndex;
    });
    table.rows = table.rows.map(function (tableRow) {
      return {
        parameter: tableRow.parameter || "",
        values: tableRow.values.filter(function (_value, index) {
          return index !== modelIndex;
        }),
      };
    });
    writeComparisonTable(input, table);
    renderComparisonTableEditor(row);
  }

  function addComparisonRow(row) {
    var input = getStructuredItemsInput(row);
    var table = parseComparisonTable(input);
    table.rows.push({
      parameter: "",
      values: table.models.map(function () {
        return "";
      }),
    });
    writeComparisonTable(input, table);
    renderComparisonTableEditor(row);
  }

  function removeComparisonRow(row, rowIndex) {
    var input = getStructuredItemsInput(row);
    var table = parseComparisonTable(input);
    table.rows = table.rows.filter(function (_tableRow, index) {
      return index !== rowIndex;
    });
    if (!table.rows.length) {
      table.rows.push({
        parameter: "",
        values: table.models.map(function () {
          return "";
        }),
      });
    }
    writeComparisonTable(input, table);
    renderComparisonTableEditor(row);
  }

  function renderItemsEditor(row) {
    var input = getStructuredItemsInput(row);
    if (!input) {
      return;
    }

    var editor = row.querySelector("[data-block-items-editor]");
    if (!editor) {
      return;
    }

    var blockType = getBlockType(row);
    if (blockType === "comparison_table") {
      renderComparisonTableEditor(row);
      return;
    }

    var schema = BLOCK_ITEM_SCHEMAS[blockType];
    if (!schema) {
      if (editor.innerHTML) {
        editor.innerHTML = "";
      }
      editor.dataset.renderKey = "";
      return;
    }

    if (blockType === "specification") {
      ensureSpecificationItemsSeeded(row);
    }

    var items = parseItems(input);
    if (!items.length) {
      items = [{}];
      writeItems(input, items);
    }

    var cards =
      schema.layout === "table"
        ? renderSpecificationRows(items, schema)
        : items
            .map(function (item, itemIndex) {
              return renderItemCard(item, itemIndex, schema);
            })
            .join("");

    var nextMarkup =
      '<div class="learning-block-items' +
      (schema.layout === "table" ? " learning-block-items--table" : "") +
      '">' +
      '<div class="learning-block-items__intro">' +
      '<div class="learning-block-items__title">' +
      schema.sectionTitle +
      "</div>" +
      '<p class="help">' +
      schema.emptyLabel +
      "</p>" +
      renderSchemaActions(schema) +
      "</div>" +
      '<div class="learning-block-items__list">' +
      cards +
      "</div>" +
      '<button type="button" class="button learning-block-items__add' +
      (schema.layout === "table" ? ' learning-block-items__add--table' : "") +
      '" data-add-block-item="true">' +
      schema.addLabel +
      "</button>" +
      "</div>";

    var renderKey = blockType + "::" + JSON.stringify(items) + "::" + JSON.stringify(getSelectedCategoryIds());
    if (editor.dataset.renderKey === renderKey) {
      return;
    }

    editor.innerHTML = nextMarkup;
    editor.dataset.renderKey = renderKey;
  }

  function collectItemsFromEditor(row) {
    var schema = BLOCK_ITEM_SCHEMAS[getBlockType(row)];
    var input = getStructuredItemsInput(row);
    var editor = row.querySelector("[data-block-items-editor]");

    if (!schema || !input || !editor) {
      return;
    }

    var items = [];
    editor.querySelectorAll("[data-block-item]").forEach(function (card) {
      var item = {};
      var hasContent = false;

      schema.fields.forEach(function (field) {
        var fieldInput = card.querySelector('[data-block-item-field="' + field.key + '"]');
        var value = fieldInput ? String(fieldInput.value || "").trim() : "";
        item[field.key] = value;
        if (value) {
          hasContent = true;
        }

        if (field.key === "characteristic_id" && fieldInput && value) {
          var selectedOption = fieldInput.options[fieldInput.selectedIndex];
          item.name = selectedOption ? String(selectedOption.text || "").trim() : "";
        }
      });

      if (hasContent) {
        items.push(item);
      }
    });

    if (schema.layout === "table") {
      items.sort(function (left, right) {
        var leftOrder = Number(left.sort_order || 0);
        var rightOrder = Number(right.sort_order || 0);
        if (leftOrder !== rightOrder) {
          return leftOrder - rightOrder;
        }
        return String(left.name || "").localeCompare(String(right.name || ""), "ru");
      });
    }

    if (!items.length) {
      items = [{}];
    }

    writeItems(input, items);
  }

  function addStructuredItem(row) {
    var input = getStructuredItemsInput(row);
    var items = parseItems(input);

    if (!items.length) {
      items = [{}];
    }

    if (getBlockType(row) === "specification") {
      var maxOrder = items.reduce(function (maxValue, item) {
        return Math.max(maxValue, Number(item.sort_order || 0));
      }, 0);
      items.push({ sort_order: String(maxOrder + 10) });
    } else {
      items.push({});
    }

    writeItems(input, items);
    renderItemsEditor(row);
  }

  function removeStructuredItem(row, itemIndex) {
    var input = getStructuredItemsInput(row);
    var items = parseItems(input).filter(function (_item, index) {
      return index !== itemIndex;
    });

    if (!items.length) {
      items = [{}];
    }

    writeItems(input, items);
    renderItemsEditor(row);
  }

  function importCategoryCharacteristics(row) {
    var blockType = getBlockType(row);

    if (blockType !== "specification" && blockType !== "comparison_table") {
      return;
    }

    var input = getStructuredItemsInput(row);

    if (blockType === "comparison_table") {
      var table = parseComparisonTable(input);
      var rows = table.rows.filter(function (tableRow) {
        return normalizeCompareParameter(tableRow.parameter) || tableRow.values.some(Boolean);
      });
      var seenParameters = new Set(
        rows
          .map(function (tableRow) {
            return normalizeCompareParameter(tableRow.parameter);
          })
          .filter(Boolean)
      );

      buildRecommendedComparisonRows(table.models).forEach(function (tableRow) {
        var key = normalizeCompareParameter(tableRow.parameter);
        if (!key || seenParameters.has(key)) {
          return;
        }
        rows.push(tableRow);
        seenParameters.add(key);
      });

      if (!rows.length) {
        rows = [
          {
            parameter: "",
            values: table.models.map(function () {
              return "";
            }),
          },
        ];
      }

      writeComparisonTable(input, {
        models: table.models,
        rows: rows,
      });
      renderComparisonTableEditor(row);
      return;
    }

    var items = parseItems(input).filter(isItemFilled);
    var seenIds = new Set(
      items
        .map(function (item) {
          return String(item.characteristic_id || "");
        })
        .filter(Boolean)
    );

    buildRecommendedSpecificationItems().forEach(function (item) {
      if (seenIds.has(String(item.characteristic_id))) {
        return;
      }
      items.push(item);
      seenIds.add(String(item.characteristic_id));
    });

    writeItems(input, items.length ? items : [{}]);
    renderItemsEditor(row);
  }

  function updateSpecificationBlocksFromCategories() {
    getBlockInlineRows().forEach(function (row) {
      if (getBlockType(row) !== "specification") {
        return;
      }

      var input = getStructuredItemsInput(row);
      if (!input) {
        return;
      }

      var items = parseItems(input);
      if (!isSpecificationItemsEmpty(items)) {
        renderItemsEditor(row);
        return;
      }

      ensureSpecificationItemsSeeded(row);
      renderItemsEditor(row);
    });
  }

  function updateBlockRow(row) {
    if (!row || row.classList.contains("empty-form")) {
      return;
    }

    var visibleFields = new Set(BLOCK_TYPE_FIELDS[getBlockType(row)] || ["text"]);

    BLOCK_FIELD_NAMES.forEach(function (fieldName) {
      var field = findFieldContainer(row, fieldName);
      if (!field) {
        return;
      }
      setFieldVisibility(field, !visibleFields.has(fieldName));
    });

    updateFieldCopy(row);
    renderItemsEditor(row);
  }

  function syncBlockRows() {
    getBlockInlineRows().forEach(updateBlockRow);
  }

  function bindCategoryChangeHandlers() {
    var categoriesTo = document.getElementById("id_categories_to");
    var categories = document.getElementById("id_categories");

    [categoriesTo, categories].forEach(function (element) {
      if (!element) {
        return;
      }
      element.addEventListener("change", updateSpecificationBlocksFromCategories);
    });

    document.querySelectorAll(
      "#id_categories_selector .selector-chooser a, #id_categories_selector .selector-clearall"
    ).forEach(function (button) {
      button.addEventListener("click", function () {
        window.setTimeout(updateSpecificationBlocksFromCategories, 0);
      });
    });
  }

  document.addEventListener("change", function (event) {
    if (event.target && event.target.id === "id_material_type") {
      toggleLearningMode();
      return;
    }

    if (
      event.target &&
      event.target.matches('select[id^="id_blocks-"][id$="-block_type"]')
    ) {
      updateBlockRow(event.target.closest(".inline-related"));
      return;
    }

    if (event.target && event.target.matches("[data-block-item-field]")) {
      collectItemsFromEditor(event.target.closest(".inline-related"));
      return;
    }

    if (
      event.target &&
      event.target.matches("[data-comparison-model-name], [data-comparison-parameter], [data-comparison-cell]")
    ) {
      collectComparisonTableFromEditor(event.target.closest(".inline-related"));
    }
  });

  document.addEventListener("input", function (event) {
    if (event.target && event.target.matches("[data-block-item-field]")) {
      collectItemsFromEditor(event.target.closest(".inline-related"));
      return;
    }

    if (
      event.target &&
      event.target.matches("[data-comparison-model-name], [data-comparison-parameter], [data-comparison-cell]")
    ) {
      collectComparisonTableFromEditor(event.target.closest(".inline-related"));
    }
  });

  document.addEventListener("click", function (event) {
    if (event.target && event.target.matches("[data-add-comparison-model]")) {
      event.preventDefault();
      addComparisonModel(event.target.closest(".inline-related"));
      return;
    }

    if (event.target && event.target.matches("[data-remove-comparison-model]")) {
      event.preventDefault();
      removeComparisonModel(
        event.target.closest(".inline-related"),
        Number(event.target.dataset.removeComparisonModel)
      );
      return;
    }

    if (event.target && event.target.matches("[data-add-comparison-row]")) {
      event.preventDefault();
      addComparisonRow(event.target.closest(".inline-related"));
      return;
    }

    if (event.target && event.target.matches("[data-remove-comparison-row]")) {
      event.preventDefault();
      removeComparisonRow(
        event.target.closest(".inline-related"),
        Number(event.target.dataset.removeComparisonRow)
      );
      return;
    }

    if (event.target && event.target.matches("[data-add-block-item]")) {
      event.preventDefault();
      addStructuredItem(event.target.closest(".inline-related"));
      return;
    }

    if (event.target && event.target.matches("[data-remove-block-item]")) {
      event.preventDefault();
      removeStructuredItem(
        event.target.closest(".inline-related"),
        Number(event.target.dataset.removeBlockItem)
      );
      return;
    }

    if (event.target && event.target.matches("[data-import-category-characteristics]")) {
      event.preventDefault();
      importCategoryCharacteristics(event.target.closest(".inline-related"));
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    toggleLearningMode();
    syncBlockRows();
    bindCategoryChangeHandlers();

    var groups = [
      document.getElementById("blocks-group"),
    ].filter(Boolean);

    var observer = new MutationObserver(function (mutations) {
      var shouldSync = false;

      Array.prototype.forEach.call(mutations || [], function (mutation) {
        if (shouldSync) {
          return;
        }

        if (
          mutation.target &&
          mutation.target.closest &&
          mutation.target.closest("[data-block-items-editor]")
        ) {
          return;
        }

        Array.prototype.forEach.call(mutation.addedNodes || [], function (node) {
          if (shouldSync || !node || !node.querySelector) {
            return;
          }

          if (
            (node.classList && node.classList.contains("inline-related")) ||
            node.querySelector(".inline-related")
          ) {
            shouldSync = true;
          }
        });
      });

      if (shouldSync) {
        syncBlockRows();
      }
    });

    groups.forEach(function (group) {
      observer.observe(group, {
        childList: true,
        subtree: true,
      });
    });
  });
})();
