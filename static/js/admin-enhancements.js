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

  function getRichTextValue(fieldId) {
    var field = document.getElementById(fieldId);
    if (!field) {
      return "";
    }

    var widget = field.closest("[data-rich-text-widget]");
    if (!widget) {
      return String(field.value || "").trim();
    }

    var surface = widget.querySelector("[data-editor-surface]");
    if (!surface) {
      return String(field.value || "").trim();
    }

    return String(surface.innerText || surface.textContent || field.value || "").trim();
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

  function formatMoneyValue(value) {
    var raw = String(value || "").trim();
    if (!raw) {
      return "";
    }

    if (raw.indexOf("%") !== -1) {
      return raw;
    }

    if (/^[\d\s.,]+$/.test(raw)) {
      var digits = raw.replace(/[^\d]/g, "");
      if (digits) {
        return Number(digits).toLocaleString("ru-RU") + " BYN";
      }
    }

    return raw;
  }

  function buildPromotionPeriodText() {
    var startDate = formatDateInput(getTextValue("id_start_date"));
    var endDate = formatDateInput(getTextValue("id_end_date"));

    if (startDate && endDate) {
      return "с " + startDate + " по " + endDate;
    }
    if (startDate) {
      return "с " + startDate;
    }
    if (endDate) {
      return "до " + endDate;
    }
    return "";
  }

  function buildPromotionAutoSummary() {
    var kind = getTextValue("id_promotion_kind");
    var title = getTextValue("id_title");
    var promoPrice = formatMoneyValue(getTextValue("id_promo_price"));
    var giftValue = getTextValue("id_benefit_value");
    var period = buildPromotionPeriodText();

    if (!title) {
      return "";
    }

    if (kind === "gift") {
      var giftSummary = "Подарок к " + title;
      if (giftValue) {
        giftSummary += " — " + giftValue;
      }
      if (period) {
        giftSummary += " " + period;
      }
      return giftSummary + ".";
    }

    if (kind === "preorder") {
      var preorderSummary = "Предзаказ на " + title;
      if (promoPrice) {
        preorderSummary += " " + promoPrice;
      }
      if (period) {
        preorderSummary += " " + period;
      }
      return preorderSummary + ".";
    }

    var discountSummary = "Скидка на " + title;
    if (promoPrice) {
      discountSummary += " " + promoPrice;
    }
    if (period) {
      discountSummary += " " + period;
    }
    return discountSummary + ".";
  }

  function bindPromotionSummaryAutoFill() {
    var summaryField = document.getElementById("id_summary");
    if (!summaryField || summaryField.dataset.promotionSummaryBound === "true") {
      return;
    }

    summaryField.dataset.promotionSummaryBound = "true";
    summaryField.dataset.autoSummaryMode = getRichTextValue("id_summary") ? "manual" : "auto";
    var widget = summaryField.closest("[data-rich-text-widget]");
    var surface = widget ? widget.querySelector("[data-editor-surface]") : null;

    function markManualMode() {
      if (summaryField.dataset.autoWriting === "true") {
        return;
      }

      summaryField.dataset.autoSummaryMode = getRichTextValue("id_summary") ? "manual" : "auto";
    }

    summaryField.addEventListener("input", markManualMode);
    if (surface) {
      surface.addEventListener("input", markManualMode);
    }
  }

  function syncPromotionSummaryField() {
    var summaryField = document.getElementById("id_summary");
    if (!summaryField) {
      return "";
    }

    bindPromotionSummaryAutoFill();

    var generated = buildPromotionAutoSummary();
    var currentValue = getRichTextValue("id_summary");
    var lastAutoValue = summaryField.dataset.lastAutoSummary || "";
    var autoMode = summaryField.dataset.autoSummaryMode !== "manual";

    if (generated && (!currentValue || currentValue === lastAutoValue || autoMode)) {
      var widget = summaryField.closest("[data-rich-text-widget]");
      var surface = widget ? widget.querySelector("[data-editor-surface]") : null;

      summaryField.dataset.autoWriting = "true";
      summaryField.value = generated;
      if (surface) {
        surface.textContent = generated;
      }
      summaryField.dataset.lastAutoSummary = generated;
      summaryField.dataset.autoSummaryMode = "auto";
      summaryField.dataset.autoWriting = "false";
      return generated;
    }

    return currentValue || generated;
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

    if (document.getElementById("id_promotion_kind")) {
      title = getTextValue("id_title");
      description = syncPromotionSummaryField() || truncateText(getRichTextValue("id_details"), 180);
      chips.push(getTextValue("id_badge"));
      chips.push(getTextValue("id_brand"));

      var promoPrice = formatMoneyValue(getTextValue("id_promo_price"));
      var giftValue = getTextValue("id_benefit_value");
      var promotionKind = getTextValue("id_promotion_kind");
      if (promoPrice) {
        footer.push("Промоцена: " + promoPrice);
      }
      if (promotionKind === "gift" && giftValue) {
        footer.push("Подарок: " + giftValue);
      }
    } else if (bodyClass.indexOf("model-news") !== -1 || document.getElementById("id_category")) {
      title = getTextValue("id_title");
      description = getRichTextValue("id_summary") || getRichTextValue("id_content");
      chips.push(getSelectedOptionLabel("id_category"));
    } else if (bodyClass.indexOf("model-learningmaterial") !== -1 || document.getElementById("id_material_type")) {
      title = getTextValue("id_title");
      description =
        getRichTextValue("id_summary") ||
        getRichTextValue("id_product_short_summary") ||
        getRichTextValue("id_product_full_description") ||
        getRichTextValue("id_content");
      chips.push(getSelectedOptionLabel("id_material_type"));
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
    var subscribersRow = findFieldRow("id_telegram_target_subscribers");
    var groupChatsRow = findFieldRow("id_telegram_target_group_chats");
    var chatCollectionsRow = findFieldRow("id_telegram_target_chat_collections");
    var includeGroupChatsRow = findFieldRow("id_telegram_include_group_chats");
    var enabled = sendNow.checked;
    var isCustom = audience.value === "custom";
    var isGroupChatsOnly = audience.value === "group_chats";

    setHidden(audienceRow, !enabled);
    setHidden(groupsRow, !enabled || !isCustom);
    setHidden(subscribersRow, !enabled || !isCustom);
    setHidden(groupChatsRow, !enabled || (!isCustom && !isGroupChatsOnly));
    setHidden(chatCollectionsRow, !enabled || (!isCustom && !isGroupChatsOnly));
    setHidden(includeGroupChatsRow, true);
  }

  function toggleBroadcastTargetGroups() {
    var targetMode = document.getElementById("id_target_mode");
    if (!targetMode) {
      return;
    }

    var groupsRow = findFieldRow("id_target_groups");
    var subscribersRow = findFieldRow("id_target_subscribers");
    var groupChatsRow = findFieldRow("id_target_group_chats");
    var chatCollectionsRow = findFieldRow("id_target_chat_collections");
    var includeGroupChatsRow = findFieldRow("id_include_group_chats");
    var isCustom = targetMode.value === "custom";
    var isGroupChatsOnly = targetMode.value === "group_chats";

    setHidden(groupsRow, !isCustom);
    setHidden(subscribersRow, !isCustom);
    setHidden(groupChatsRow, !isCustom && !isGroupChatsOnly);
    setHidden(chatCollectionsRow, !isCustom && !isGroupChatsOnly);
    setHidden(includeGroupChatsRow, true);
  }

  function togglePromotionBenefitField() {
    var promotionKind = document.getElementById("id_promotion_kind");
    if (!promotionKind) {
      return;
    }

    var promoPriceRow = findFieldRow("id_promo_price");
    var benefitRow = findFieldRow("id_benefit_value");
    var promoCodeRow = findFieldRow("id_promo_code");
    var kind = promotionKind.value;

    setHidden(benefitRow, kind !== "gift");
    setHidden(promoCodeRow, kind !== "promo_price");

    if (promoPriceRow) {
      promoPriceRow.classList.remove("is-hidden");
    }
  }

  function initializeAdminEnhancements() {
    if (document.body && document.body.dataset.adminEnhancementsReady === "true") {
      return;
    }

    if (document.body) {
      document.body.dataset.adminEnhancementsReady = "true";
    }

    ensureDraftStatusBox();
    restoreDraftSnapshot();
    setupImageUploadPreviews();
    toggleTelegramAudienceFields();
    toggleBroadcastTargetGroups();
    togglePromotionBenefitField();
    updateCardPreview();
    decorateTypeBadges();

    document.addEventListener(
      "change",
      function () {
        toggleTelegramAudienceFields();
        toggleBroadcastTargetGroups();
        togglePromotionBenefitField();
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
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAdminEnhancements);
  } else {
    initializeAdminEnhancements();
  }
})();
