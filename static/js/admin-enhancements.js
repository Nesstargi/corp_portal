(function () {
  function isChangeFormPage() {
    return (document.body.className || "").indexOf("change-form") !== -1;
  }

  function getDraftStorageKey() {
    return "corpportal-admin-draft:" + window.location.pathname;
  }

  function isIgnoredField(field) {
    if (!field || !field.name) {
      return true;
    }

    if (field.type === "hidden" || field.type === "file" || field.type === "password") {
      return true;
    }

    return /-(TOTAL|INITIAL|MIN_NUM|MAX_NUM)_FORMS$/.test(field.name);
  }

  function collectDraftData() {
    if (!isChangeFormPage()) {
      return {};
    }

    var form = document.querySelector("form");
    if (!form) {
      return {};
    }

    var data = {};
    form.querySelectorAll("input, textarea, select").forEach(function (field) {
      if (isIgnoredField(field)) {
        return;
      }

      if (field.type === "checkbox") {
        data[field.name] = field.checked;
        return;
      }

      if (field.type === "radio") {
        if (field.checked) {
          data[field.name] = field.value;
        }
        return;
      }

      data[field.name] = field.value;
    });

    return data;
  }

  function saveDraftSnapshot() {
    if (!isChangeFormPage()) {
      return;
    }

    var payload = {
      saved_at: new Date().toISOString(),
      values: collectDraftData(),
    };

    try {
      localStorage.setItem(getDraftStorageKey(), JSON.stringify(payload));
      updateDraftStatus(payload.saved_at);
    } catch (error) {}
  }

  function restoreDraftSnapshot() {
    if (!isChangeFormPage()) {
      return;
    }

    var raw = localStorage.getItem(getDraftStorageKey());
    if (!raw) {
      return;
    }

    try {
      var payload = JSON.parse(raw);
      var values = payload.values || {};

      Object.keys(values).forEach(function (fieldName) {
        var fields = document.querySelectorAll('[name="' + CSS.escape(fieldName) + '"]');
        if (!fields.length) {
          return;
        }

        fields.forEach(function (field) {
          if (field.type === "checkbox") {
            field.checked = Boolean(values[fieldName]);
          } else if (field.type === "radio") {
            field.checked = field.value === values[fieldName];
          } else {
            field.value = values[fieldName];
          }
          field.dispatchEvent(new Event("change", { bubbles: true }));
          field.dispatchEvent(new Event("input", { bubbles: true }));
        });
      });

      updateDraftStatus(payload.saved_at, true);
    } catch (error) {}
  }

  function clearDraftSnapshot() {
    if (!isChangeFormPage()) {
      return;
    }

    try {
      localStorage.removeItem(getDraftStorageKey());
      updateDraftStatus("", false, true);
    } catch (error) {}
  }

  function ensureDraftStatusBox() {
    if (!isChangeFormPage()) {
      return;
    }

    var form = document.querySelector("form");
    if (!form || document.querySelector(".admin-draft-status")) {
      return;
    }

    var box = document.createElement("div");
    box.className = "admin-draft-status";
    box.innerHTML =
      '<span class="admin-draft-status__label">Черновик в браузере</span>' +
      '<span class="admin-draft-status__hint">Пока не сохранён</span>' +
      '<button type="button" class="admin-draft-status__button">Очистить</button>';

    var top = document.getElementById("content-main") || form.parentElement;
    top.insertBefore(box, form);

    box.querySelector(".admin-draft-status__button").addEventListener("click", clearDraftSnapshot);
  }

  function updateDraftStatus(savedAt, restored, cleared) {
    var box = document.querySelector(".admin-draft-status");
    if (!box) {
      return;
    }

    var hint = box.querySelector(".admin-draft-status__hint");
    if (!savedAt) {
      hint.textContent = cleared ? "Локальный черновик очищен" : "Пока не сохранён";
      return;
    }

    var date = new Date(savedAt);
    var formatted = isNaN(date.getTime())
      ? "только что"
      : date.toLocaleString("ru-RU");
    hint.textContent = restored
      ? "Черновик восстановлен. Последнее сохранение: " + formatted
      : "Последнее автосохранение: " + formatted;
  }

  function isImageFile(file) {
    return Boolean(file && file.type && file.type.indexOf("image/") === 0);
  }

  function createImagePreviewContainer(input) {
    var wrapper = document.createElement("div");
    wrapper.className = "admin-image-preview is-empty admin-image-preview--dynamic";
    wrapper.dataset.previewField = input.name || input.id || "";
    wrapper.innerHTML =
      '<div class="admin-image-preview__canvas">' +
      '<img src="" alt="" class="is-hidden" />' +
      '<div class="admin-image-preview__placeholder">Изображение пока не добавлено.</div>' +
      "</div>" +
      '<div class="admin-image-preview__meta">Превью выбранного изображения</div>' +
      '<div class="admin-image-preview__meta admin-image-preview__dimensions is-hidden"></div>' +
      '<div class="admin-image-preview__warning is-hidden"></div>';

    var host = input.closest(".form-row, .fieldBox, .aligned > div, .form-group") || input.parentElement;
    if (host) {
      host.appendChild(wrapper);
    }

    return wrapper;
  }

  function findImagePreviewContainer(input) {
    var candidates = Array.from(document.querySelectorAll(".admin-image-preview"));
    var fieldName = input.name || "";
    var inputId = input.id || "";
    var suffix = fieldName.split("-").pop();

    return (
      candidates.find(function (preview) {
        return preview.dataset.previewField === fieldName || preview.dataset.previewField === inputId;
      }) ||
      candidates.find(function (preview) {
        return preview.dataset.previewField === suffix;
      }) ||
      null
    );
  }

  function updateImagePreviewState(preview, imageUrl, dimensions, warningText) {
    if (!preview) {
      return;
    }

    var image = preview.querySelector("img");
    var placeholder = preview.querySelector(".admin-image-preview__placeholder");
    var dimensionsBox = preview.querySelector(".admin-image-preview__dimensions");
    var warningBox = preview.querySelector(".admin-image-preview__warning");

    if (image) {
      image.src = imageUrl || "";
      image.classList.toggle("is-hidden", !imageUrl);
    }
    if (placeholder) {
      placeholder.classList.toggle("is-hidden", Boolean(imageUrl));
    }
    preview.classList.toggle("is-empty", !imageUrl);

    if (dimensionsBox) {
      dimensionsBox.textContent = dimensions || "";
      dimensionsBox.classList.toggle("is-hidden", !dimensions);
    }

    if (warningBox) {
      warningBox.textContent = warningText || "";
      warningBox.classList.toggle("is-hidden", !warningText);
    }
  }

  function readRecommendedSize(preview) {
    if (!preview) {
      return { width: 0, height: 0 };
    }

    return {
      width: parseInt(preview.dataset.recommendedWidth || "0", 10) || 0,
      height: parseInt(preview.dataset.recommendedHeight || "0", 10) || 0,
    };
  }

  function bindImageInputPreview(input) {
    if (!input || input.dataset.previewBound === "true") {
      return;
    }

    input.dataset.previewBound = "true";

    var preview = findImagePreviewContainer(input);
    if (!preview) {
      preview = createImagePreviewContainer(input);
    }

    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!isImageFile(file)) {
        updateImagePreviewState(preview, "", "", "");
        return;
      }

      var objectUrl = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        var recommended = readRecommendedSize(preview);
        var dimensions = "Размер файла: " + img.width + " x " + img.height + " px";
        var warning = "";

        if (
          recommended.width &&
          recommended.height &&
          (img.width < recommended.width || img.height < recommended.height)
        ) {
          warning =
            "Изображение меньше рекомендуемого размера " +
            recommended.width +
            " x " +
            recommended.height +
            " px.";
        }

        updateImagePreviewState(preview, objectUrl, dimensions, warning);
      };
      img.onerror = function () {
        updateImagePreviewState(preview, objectUrl, "", "");
      };
      img.src = objectUrl;
    });
  }

  function setupImageUploadPreviews() {
    document.querySelectorAll('input[type="file"]').forEach(function (input) {
      var key = ((input.name || "") + " " + (input.id || "")).toLowerCase();
      if (key.indexOf("image") === -1 && key.indexOf("cover") === -1) {
        return;
      }
      bindImageInputPreview(input);
    });
  }

  function setHidden(element, hidden) {
    if (!element) {
      return;
    }
    element.classList.toggle("is-hidden", hidden);
  }

  function findFieldRow(fieldId) {
    var field = document.getElementById(fieldId);
    if (!field) {
      return null;
    }
    return field.closest(".form-row, .fieldBox, .aligned > div, .flex-container") || field.parentElement;
  }

  function getTextValue(fieldId) {
    var field = document.getElementById(fieldId);
    if (!field) {
      return "";
    }
    return String(field.value || "").trim();
  }

  function getSelectedOptionLabel(fieldId) {
    var field = document.getElementById(fieldId);
    if (!field || !field.options || field.selectedIndex < 0) {
      return "";
    }
    return String(field.options[field.selectedIndex].text || "").trim();
  }

  function truncateText(text, limit) {
    var value = String(text || "").trim();
    if (!value) {
      return "";
    }
    if (value.length <= limit) {
      return value;
    }
    return value.slice(0, limit).trim() + "...";
  }

  function formatDateInput(value) {
    if (!value || value.indexOf("-") === -1) {
      return "";
    }
    var parts = value.split("-");
    if (parts.length !== 3) {
      return "";
    }
    return [parts[2], parts[1], parts[0]].join(".");
  }

  function getBenefitLabel() {
    var kind = getTextValue("id_promotion_kind");
    var benefit = getTextValue("id_benefit_value").toLowerCase();
    if (kind === "gift" || benefit.indexOf("подар") !== -1) {
      return "Подарок";
    }
    return "Скидка";
  }

  function buildPromotionSummary() {
    var benefitValue = getTextValue("id_benefit_value");
    if (!benefitValue) {
      return truncateText(getTextValue("id_summary") || getTextValue("id_details"), 180);
    }

    var startDate = formatDateInput(getTextValue("id_start_date"));
    var endDate = formatDateInput(getTextValue("id_end_date"));
    var prefix = getBenefitLabel() === "Подарок" ? "Подарок при покупке у нас" : "Выгода при покупке у нас";

    if (startDate && endDate) {
      return prefix + " с " + startDate + " по " + endDate + " — " + benefitValue + ".";
    }
    if (startDate) {
      return prefix + " с " + startDate + " — " + benefitValue + ".";
    }
    if (endDate) {
      return prefix + " до " + endDate + " — " + benefitValue + ".";
    }
    return prefix + " — " + benefitValue + ".";
  }

  function updateCardPreview() {
    var preview = document.querySelector(".admin-card-preview");
    if (!preview) {
      return;
    }

    var bodyClass = document.body.className || "";
    var title = "";
    var description = "";
    var chips = [];
    var footer = [];

    if (bodyClass.indexOf("model-news") !== -1) {
      title = getTextValue("id_title");
      description = getTextValue("id_summary") || getTextValue("id_content");
      chips.push(getSelectedOptionLabel("id_category"));
    } else if (bodyClass.indexOf("model-learningmaterial") !== -1) {
      title = getTextValue("id_title");
      description =
        getTextValue("id_summary") ||
        getTextValue("id_product_short_summary") ||
        getTextValue("id_product_full_description") ||
        getTextValue("id_content");
      chips.push(getSelectedOptionLabel("id_material_type"));
    } else if (bodyClass.indexOf("model-promotion") !== -1) {
      title = getTextValue("id_title");
      description = buildPromotionSummary();
      chips.push(getTextValue("id_badge"));
      chips.push(getTextValue("id_brand"));

      var promoPrice = getTextValue("id_promo_price");
      var benefitValue = getTextValue("id_benefit_value");
      if (promoPrice) {
        footer.push("Промоцена: " + promoPrice);
      }
      if (benefitValue) {
        footer.push(getBenefitLabel() + ": " + benefitValue);
      }
    }

    preview.querySelector(".admin-card-preview__title").textContent =
      title || "Без названия";
    preview.querySelector(".admin-card-preview__description").textContent =
      truncateText(description, 180) || "Краткое описание появится здесь после заполнения формы.";

    var chipsContainer = preview.querySelector(".admin-card-preview__chips");
    if (chipsContainer) {
      chipsContainer.innerHTML = chips
        .filter(Boolean)
        .map(function (chip) {
          return '<span class="admin-card-preview__chip">' + chip + "</span>";
        })
        .join("");
      chipsContainer.classList.toggle("is-hidden", chipsContainer.innerHTML === "");
    }

    var footerContainer = preview.querySelector(".admin-card-preview__footer");
    if (footerContainer) {
      footerContainer.innerHTML = footer
        .filter(Boolean)
        .map(function (item) {
          return '<span class="admin-card-preview__meta">' + item + "</span>";
        })
        .join("");
      footerContainer.classList.toggle("is-hidden", footerContainer.innerHTML === "");
    }
  }

  function typeBadgeClass(value) {
    var normalized = String(value || "").toLowerCase();
    if (normalized.indexOf("акц") !== -1 || normalized.indexOf("скид") !== -1 || normalized.indexOf("подар") !== -1) {
      return "is-orange";
    }
    if (normalized.indexOf("товар") !== -1 || normalized.indexOf("модел") !== -1) {
      return "is-blue";
    }
    if (normalized.indexOf("процесс") !== -1 || normalized.indexOf("инструк") !== -1) {
      return "is-green";
    }
    return "is-violet";
  }

  function decorateTypeBadges() {
    document.querySelectorAll(".field-material_type, .field-category, .field-promotion_kind").forEach(function (cell) {
      if (cell.querySelector(".admin-type-badge")) {
        return;
      }

      var text = (cell.textContent || "").trim();
      if (!text || text === "-") {
        return;
      }

      cell.innerHTML =
        '<span class="admin-type-badge ' + typeBadgeClass(text) + '">' + text + "</span>";
    });
  }

  function toggleTelegramAudienceFields() {
    var sendNow = document.getElementById("id_send_telegram_notification");
    var audience = document.getElementById("id_telegram_audience");
    if (!sendNow || !audience) {
      return;
    }

    var audienceRow = findFieldRow("id_telegram_audience");
    var groupsRow = findFieldRow("id_telegram_target_groups");
    var enabled = sendNow.checked;

    setHidden(audienceRow, !enabled);
    setHidden(groupsRow, !enabled || audience.value !== "groups");
  }

  function toggleBroadcastTargetGroups() {
    var targetMode = document.getElementById("id_target_mode");
    if (!targetMode) {
      return;
    }

    var groupsRow = findFieldRow("id_target_groups");
    setHidden(groupsRow, targetMode.value !== "groups");
  }

  document.addEventListener("DOMContentLoaded", function () {
    ensureDraftStatusBox();
    restoreDraftSnapshot();
    setupImageUploadPreviews();
    toggleTelegramAudienceFields();
    toggleBroadcastTargetGroups();
    updateCardPreview();
    decorateTypeBadges();

    document.addEventListener(
      "change",
      function () {
        toggleTelegramAudienceFields();
        toggleBroadcastTargetGroups();
        updateCardPreview();
        setupImageUploadPreviews();
        saveDraftSnapshot();
      },
      true
    );

    document.addEventListener(
      "input",
      function () {
        updateCardPreview();
        saveDraftSnapshot();
      },
      true
    );
  });
})();
