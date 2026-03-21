(function () {
  function getField(fieldId) {
    return document.getElementById(fieldId);
  }

  function getRow(fieldId) {
    var field = getField(fieldId);
    if (!field) {
      return null;
    }
    return field.closest(".form-row") || field.closest(".fieldBox") || field.parentElement;
  }

  function setHidden(node, hidden) {
    if (!node) {
      return;
    }
    node.classList.toggle("is-hidden", hidden);
  }

  function getValue(fieldId) {
    var field = getField(fieldId);
    return field ? String(field.value || "").trim() : "";
  }

  function getRichTextValue(fieldId) {
    var field = getField(fieldId);
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

  function setRichTextValue(fieldId, value) {
    var field = getField(fieldId);
    if (!field) {
      return;
    }

    var normalized = String(value || "").trim();
    field.value = normalized;

    var widget = field.closest("[data-rich-text-widget]");
    if (!widget) {
      return;
    }

    var surface = widget.querySelector("[data-editor-surface]");
    if (surface) {
      surface.textContent = normalized;
    }
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

  function buildPeriodText() {
    var startDate = formatDateInput(getValue("id_start_date"));
    var endDate = formatDateInput(getValue("id_end_date"));

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

  function buildAutoSummary() {
    var kind = getValue("id_promotion_kind");
    var title = getValue("id_title");
    var promoPrice = formatMoneyValue(getValue("id_promo_price"));
    var giftValue = getValue("id_benefit_value");
    var period = buildPeriodText();

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

  function bindSummaryMode() {
    var summaryField = getField("id_summary");
    if (!summaryField || summaryField.dataset.promotionSummaryBound === "true") {
      return;
    }

    summaryField.dataset.promotionSummaryBound = "true";
    summaryField.dataset.autoSummaryMode = getRichTextValue("id_summary") ? "manual" : "auto";

    function markManualMode() {
      if (summaryField.dataset.autoWriting === "true") {
        return;
      }
      summaryField.dataset.autoSummaryMode = getRichTextValue("id_summary") ? "manual" : "auto";
    }

    summaryField.addEventListener("input", markManualMode);

    var widget = summaryField.closest("[data-rich-text-widget]");
    var surface = widget ? widget.querySelector("[data-editor-surface]") : null;
    if (surface) {
      surface.addEventListener("input", markManualMode);
    }
  }

  function syncSummary() {
    var summaryField = getField("id_summary");
    if (!summaryField) {
      return "";
    }

    bindSummaryMode();

    var currentValue = getRichTextValue("id_summary");
    var lastAutoValue = summaryField.dataset.lastAutoSummary || "";
    var generated = buildAutoSummary();
    var autoMode = summaryField.dataset.autoSummaryMode !== "manual";

    if (generated && (!currentValue || currentValue === lastAutoValue || autoMode)) {
      summaryField.dataset.autoWriting = "true";
      setRichTextValue("id_summary", generated);
      summaryField.dataset.lastAutoSummary = generated;
      summaryField.dataset.autoSummaryMode = "auto";
      summaryField.dataset.autoWriting = "false";
      return generated;
    }

    return currentValue || generated;
  }

  function updatePreview() {
    var preview = document.querySelector(".admin-card-preview");
    if (!preview || !getField("id_promotion_kind")) {
      return;
    }

    var title = getValue("id_title") || "Без названия";
    var description =
      syncSummary() ||
      getRichTextValue("id_details") ||
      "Краткое описание появится здесь после заполнения формы.";
    var badge = getValue("id_badge");
    var brand = getValue("id_brand");
    var promoPrice = formatMoneyValue(getValue("id_promo_price"));
    var giftValue = getValue("id_benefit_value");
    var promotionKind = getValue("id_promotion_kind");

    preview.querySelector(".admin-card-preview__title").textContent = title;
    preview.querySelector(".admin-card-preview__description").textContent = description;

    var chipsContainer = preview.querySelector(".admin-card-preview__chips");
    if (chipsContainer) {
      var chips = [badge, brand].filter(Boolean);
      chipsContainer.innerHTML = chips
        .map(function (chip) {
          return '<span class="admin-card-preview__chip">' + chip + "</span>";
        })
        .join("");
      chipsContainer.classList.toggle("is-hidden", chips.length === 0);
    }

    var footerContainer = preview.querySelector(".admin-card-preview__footer");
    if (footerContainer) {
      var footer = [];
      if (promoPrice) {
        footer.push("Промоцена: " + promoPrice);
      }
      if (promotionKind === "gift" && giftValue) {
        footer.push("Подарок: " + giftValue);
      }
      footerContainer.innerHTML = footer
        .map(function (item) {
          return '<span class="admin-card-preview__meta">' + item + "</span>";
        })
        .join("");
      footerContainer.classList.toggle("is-hidden", footer.length === 0);
    }
  }

  function toggleFields() {
    var kind = getValue("id_promotion_kind");
    setHidden(getRow("id_benefit_value"), kind !== "gift");
    setHidden(getRow("id_promo_code"), kind !== "promo_price");
  }

  function bindField(fieldId, eventName, callback) {
    var field = getField(fieldId);
    if (!field) {
      return;
    }
    field.addEventListener(eventName, callback);
  }

  function initPromotionAdmin() {
    if (!getField("id_promotion_kind") || document.body.dataset.promotionAdminReady === "true") {
      return;
    }

    document.body.dataset.promotionAdminReady = "true";

    [
      "id_title",
      "id_promotion_kind",
      "id_badge",
      "id_brand",
      "id_promo_price",
      "id_benefit_value",
      "id_start_date",
      "id_end_date",
    ].forEach(function (fieldId) {
      bindField(fieldId, "input", updatePreview);
      bindField(fieldId, "change", function () {
        toggleFields();
        updatePreview();
      });
    });

    bindField("id_details", "input", updatePreview);
    bindField("id_summary", "input", updatePreview);

    var summaryField = getField("id_summary");
    if (summaryField) {
      var widget = summaryField.closest("[data-rich-text-widget]");
      var surface = widget ? widget.querySelector("[data-editor-surface]") : null;
      if (surface) {
        surface.addEventListener("input", updatePreview);
      }
    }

    toggleFields();
    updatePreview();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPromotionAdmin);
  } else {
    initPromotionAdmin();
  }
})();
