(function () {
  var mobileMedia = window.matchMedia("(max-width: 720px)");

  function getFilterPanels() {
    return document.querySelectorAll("[data-filter-panel]");
  }

  function hasActiveFilters(panel) {
    return panel.dataset.hasActiveFilters === "true";
  }

  function syncFilterPanels() {
    getFilterPanels().forEach(function (panel) {
      if (!mobileMedia.matches) {
        panel.open = true;
        panel.dataset.mobileInitialized = "false";
        panel.dataset.filterViewport = "desktop";
        return;
      }

      if (panel.dataset.filterViewport !== "mobile") {
        panel.open = hasActiveFilters(panel);
        panel.dataset.mobileInitialized = "true";
        panel.dataset.filterViewport = "mobile";
      }
    });
  }

  // The script is loaded at the end of the document, so applying the initial
  // state synchronously prevents an inactive mobile filter from painting open.
  syncFilterPanels();

  if (typeof mobileMedia.addEventListener === "function") {
    mobileMedia.addEventListener("change", syncFilterPanels);
  } else {
    mobileMedia.addListener(syncFilterPanels);
  }

  window.addEventListener("pageshow", function () {
    getFilterPanels().forEach(function (panel) {
      panel.dataset.filterViewport = "";
    });
    syncFilterPanels();
  });
})();
