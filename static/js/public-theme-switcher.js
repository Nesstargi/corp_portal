(function () {
  var storageKey = "corpportal-public-theme";
  var defaultTheme = "current";
  var corporateTheme = "corporate";

  function normalizeTheme(theme) {
    return theme === corporateTheme ? corporateTheme : defaultTheme;
  }

  function readSavedTheme() {
    try {
      return normalizeTheme(window.localStorage.getItem(storageKey));
    } catch (error) {
      return defaultTheme;
    }
  }

  function saveTheme(theme) {
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch (error) {
      // The selected theme still applies for this page when storage is unavailable.
    }
  }

  function updateToggle(toggle, theme) {
    var corporateIsActive = theme === corporateTheme;
    var actionLabel = corporateIsActive
      ? "Включить текущий стиль"
      : "Включить корпоративный стиль";

    toggle.setAttribute("aria-pressed", corporateIsActive ? "true" : "false");
    toggle.setAttribute("aria-label", actionLabel);
    toggle.setAttribute("title", actionLabel);
  }

  function applyTheme(theme) {
    var normalizedTheme = normalizeTheme(theme);
    document.documentElement.dataset.publicTheme = normalizedTheme;

    document.querySelectorAll("[data-theme-toggle]").forEach(function (toggle) {
      updateToggle(toggle, normalizedTheme);
    });

    return normalizedTheme;
  }

  function initializeToggle() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (toggle) {
      updateToggle(toggle, document.documentElement.dataset.publicTheme);
      toggle.addEventListener("click", function () {
        var nextTheme =
          document.documentElement.dataset.publicTheme === corporateTheme
            ? defaultTheme
            : corporateTheme;

        saveTheme(applyTheme(nextTheme));
      });
    });
  }

  applyTheme(readSavedTheme());

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeToggle, { once: true });
  } else {
    initializeToggle();
  }

  window.addEventListener("storage", function (event) {
    if (event.key === storageKey) {
      applyTheme(event.newValue);
    }
  });
})();
