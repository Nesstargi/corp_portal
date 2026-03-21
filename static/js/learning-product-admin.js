(function () {
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
    setSectionVisibility(".learning-admin-section.product-only", !productMode);
    setSectionVisibility(".learning-admin-section.general-only", productMode);
    setSectionVisibility(".learning-admin-anchor.product-only", !productMode);
    setSectionVisibility(".learning-admin-anchor.general-only", productMode);
  }

  function readCategoryCharacteristicMap() {
    var script = document.getElementById("category-characteristics-map");
    if (!script) {
      return {};
    }

    try {
      return JSON.parse(script.textContent || "{}");
    } catch (error) {
      return {};
    }
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

  function getRequiredCharacteristics(categoryMap, categoryIds) {
    var unique = new Map();

    categoryIds.forEach(function (categoryId) {
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

  function getSpecSection() {
    return document.getElementById("product-specifications-section");
  }

  function getInlinePrefix() {
    var section = getSpecSection();
    if (!section) {
      return "";
    }
    return section.dataset.inlinePrefix || "product_specifications";
  }

  function getTotalForms(prefix) {
    var input = document.getElementById("id_" + prefix + "-TOTAL_FORMS");
    return input ? parseInt(input.value || "0", 10) : 0;
  }

  function getFormField(prefix, index, fieldName) {
    return document.getElementById("id_" + prefix + "-" + index + "-" + fieldName);
  }

  function getFormInfo(prefix, index) {
    var characteristic = getFormField(prefix, index, "characteristic");
    if (!characteristic) {
      return null;
    }

    return {
      index: index,
      characteristic: characteristic,
      value: getFormField(prefix, index, "value"),
      sortOrder: getFormField(prefix, index, "sort_order"),
      deleteField: getFormField(prefix, index, "DELETE"),
    };
  }

  function isDeleted(formInfo) {
    return !!(formInfo && formInfo.deleteField && formInfo.deleteField.checked);
  }

  function isFormEmpty(formInfo) {
    if (!formInfo || isDeleted(formInfo)) {
      return false;
    }

    var characteristicValue = String(formInfo.characteristic.value || "").trim();
    var specValue = formInfo.value ? String(formInfo.value.value || "").trim() : "";
    return !characteristicValue && !specValue;
  }

  function getExistingCharacteristicIds(prefix) {
    var total = getTotalForms(prefix);
    var existing = new Set();

    for (var index = 0; index < total; index += 1) {
      var formInfo = getFormInfo(prefix, index);
      if (!formInfo || isDeleted(formInfo)) {
        continue;
      }

      var value = String(formInfo.characteristic.value || "").trim();
      if (value) {
        existing.add(value);
      }
    }

    return existing;
  }

  function findReusableForm(prefix) {
    var total = getTotalForms(prefix);

    for (var index = 0; index < total; index += 1) {
      var formInfo = getFormInfo(prefix, index);
      if (isFormEmpty(formInfo)) {
        return formInfo;
      }
    }

    return null;
  }

  function addInlineForm(prefix) {
    var group = document.getElementById(prefix + "-group");
    if (!group) {
      return null;
    }

    var addButton = group.querySelector(".add-row a");
    if (!addButton) {
      return null;
    }

    var beforeTotal = getTotalForms(prefix);
    addButton.click();
    var afterTotal = getTotalForms(prefix);

    if (afterTotal <= beforeTotal) {
      return null;
    }

    return getFormInfo(prefix, afterTotal - 1);
  }

  function fillSpecificationForm(formInfo, characteristicData, position) {
    if (!formInfo || !formInfo.characteristic) {
      return;
    }

    formInfo.characteristic.value = String(characteristicData.id);
    formInfo.characteristic.dispatchEvent(new Event("change", { bubbles: true }));

    if (formInfo.sortOrder && !String(formInfo.sortOrder.value || "").trim()) {
      formInfo.sortOrder.value = String(
        Number(characteristicData.sort_order || 0) || (position + 1) * 10
      );
    }
  }

  function syncProductSpecifications() {
    if (!isProductMode()) {
      return;
    }

    var prefix = getInlinePrefix();
    if (!prefix) {
      return;
    }

    var categoryMap = readCategoryCharacteristicMap();
    var selectedCategoryIds = getSelectedCategoryIds();
    var requiredCharacteristics = getRequiredCharacteristics(categoryMap, selectedCategoryIds);
    var existingIds = getExistingCharacteristicIds(prefix);

    requiredCharacteristics.forEach(function (characteristicData, index) {
      var characteristicId = String(characteristicData.id);
      if (existingIds.has(characteristicId)) {
        return;
      }

      var formInfo = findReusableForm(prefix) || addInlineForm(prefix);
      if (!formInfo) {
        return;
      }

      fillSpecificationForm(formInfo, characteristicData, index);
      existingIds.add(characteristicId);
    });
  }

  function bindCategoryChangeHandlers() {
    var categoriesTo = document.getElementById("id_categories_to");
    var categories = document.getElementById("id_categories");

    [categoriesTo, categories].forEach(function (element) {
      if (!element) {
        return;
      }
      element.addEventListener("change", syncProductSpecifications);
    });

    document.querySelectorAll(
      "#id_categories_selector .selector-chooser a, #id_categories_selector .selector-clearall"
    ).forEach(function (button) {
      button.addEventListener("click", function () {
        window.setTimeout(syncProductSpecifications, 0);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var materialType = document.getElementById("id_material_type");

    toggleLearningMode();
    bindCategoryChangeHandlers();
    syncProductSpecifications();

    if (materialType) {
      materialType.addEventListener("change", function () {
        toggleLearningMode();
        window.setTimeout(syncProductSpecifications, 0);
      });
    }
  });
})();
