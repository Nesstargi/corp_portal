(function () {
  function setSectionVisibility(selector, hidden) {
    document.querySelectorAll(selector).forEach(function (section) {
      section.classList.toggle("is-hidden", hidden);
    });
  }

  function toggleLearningMode() {
    var materialType = document.getElementById("id_material_type");
    var isProductMode = materialType && materialType.value === "product";

    setSectionVisibility(".learning-admin-section.product-only", !isProductMode);
    setSectionVisibility(".learning-admin-section.general-only", isProductMode);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var materialType = document.getElementById("id_material_type");

    toggleLearningMode();

    if (materialType) {
      materialType.addEventListener("change", toggleLearningMode);
    }
  });
})();
