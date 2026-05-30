(function () {
  var mobileMedia = window.matchMedia("(max-width: 720px)");

  function syncFilterPanels() {
    document.querySelectorAll("[data-filter-panel]").forEach(function (panel) {
      if (!mobileMedia.matches) {
        panel.open = true;
        panel.dataset.mobileInitialized = "false";
        return;
      }

      if (panel.dataset.mobileInitialized !== "true") {
        panel.open = panel.dataset.hasActiveFilters === "true";
        panel.dataset.mobileInitialized = "true";
      }
    });
  }

  if (typeof mobileMedia.addEventListener === "function") {
    mobileMedia.addEventListener("change", syncFilterPanels);
  } else {
    mobileMedia.addListener(syncFilterPanels);
  }

  syncFilterPanels();
})();
