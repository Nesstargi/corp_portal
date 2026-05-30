(function () {
  var toggle = document.querySelector("[data-nav-toggle]");
  var drawer = document.querySelector("[data-nav-drawer]");
  var closeButton = document.querySelector("[data-nav-close]");
  var backdrop = document.querySelector("[data-nav-backdrop]");
  var desktopMedia = window.matchMedia("(min-width: 861px)");

  if (!toggle || !drawer || !closeButton || !backdrop) {
    return;
  }

  function setMenuOpen(isOpen, returnFocus) {
    drawer.classList.toggle("is-open", isOpen);
    backdrop.classList.toggle("is-visible", isOpen);
    document.body.classList.toggle("nav-drawer-open", isOpen);
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    toggle.setAttribute("aria-label", isOpen ? "Закрыть меню" : "Открыть меню");

    if (desktopMedia.matches) {
      drawer.removeAttribute("aria-hidden");
    } else {
      drawer.setAttribute("aria-hidden", isOpen ? "false" : "true");
    }

    if (isOpen) {
      closeButton.focus();
    } else if (returnFocus) {
      toggle.focus();
    }
  }

  function syncNavigationMode() {
    setMenuOpen(false, false);
  }

  toggle.addEventListener("click", function () {
    setMenuOpen(!drawer.classList.contains("is-open"), false);
  });

  closeButton.addEventListener("click", function () {
    setMenuOpen(false, true);
  });

  backdrop.addEventListener("click", function () {
    setMenuOpen(false, true);
  });

  drawer.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      setMenuOpen(false, false);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && drawer.classList.contains("is-open")) {
      setMenuOpen(false, true);
    }
  });

  if (typeof desktopMedia.addEventListener === "function") {
    desktopMedia.addEventListener("change", syncNavigationMode);
  } else {
    desktopMedia.addListener(syncNavigationMode);
  }

  syncNavigationMode();
})();
