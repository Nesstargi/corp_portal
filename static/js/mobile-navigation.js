(function () {
  var toggle = document.querySelector("[data-nav-toggle]");
  var drawer = document.querySelector("[data-nav-drawer]");
  var closeButton = document.querySelector("[data-nav-close]");
  var backdrop = document.querySelector("[data-nav-backdrop]");
  var desktopMedia = window.matchMedia("(min-width: 861px)");
  var returnFocusTarget = null;

  if (!toggle || !drawer || !closeButton || !backdrop) {
    return;
  }

  function getFocusableElements() {
    return Array.prototype.filter.call(
      drawer.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      ),
      function (element) {
        return !element.hasAttribute("hidden") && element.getAttribute("aria-hidden") !== "true";
      }
    );
  }

  function isMenuOpen() {
    return drawer.classList.contains("is-open");
  }

  function setMenuOpen(isOpen, returnFocus) {
    if (isOpen && !isMenuOpen()) {
      returnFocusTarget =
        document.activeElement && document.activeElement !== document.body
          ? document.activeElement
          : toggle;
    }

    drawer.classList.toggle("is-open", isOpen);
    backdrop.classList.toggle("is-visible", isOpen);
    document.body.classList.toggle("nav-drawer-open", isOpen);
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    toggle.setAttribute("aria-label", isOpen ? "Закрыть меню" : "Открыть меню");

    if (desktopMedia.matches) {
      drawer.removeAttribute("aria-hidden");
      drawer.removeAttribute("inert");
    } else {
      drawer.setAttribute("aria-hidden", isOpen ? "false" : "true");
      if (isOpen) {
        drawer.removeAttribute("inert");
      } else {
        drawer.setAttribute("inert", "");
      }
    }

    if (isOpen) {
      window.requestAnimationFrame(function () {
        if (isMenuOpen()) {
          closeButton.focus({ preventScroll: true });
        }
      });
    } else if (returnFocus) {
      var focusTarget = returnFocusTarget || toggle;
      if (focusTarget && typeof focusTarget.focus === "function" && focusTarget.isConnected) {
        focusTarget.focus();
      } else {
        toggle.focus();
      }
    }

    if (!isOpen) {
      returnFocusTarget = null;
    }
  }

  function syncNavigationMode() {
    var wasOpen = isMenuOpen();
    var focusWasInsideDrawer = drawer.contains(document.activeElement);

    setMenuOpen(false, false);

    if (desktopMedia.matches && wasOpen && focusWasInsideDrawer) {
      var activeLink = drawer.querySelector("a.is-active") || drawer.querySelector("a[href]");
      if (activeLink) {
        activeLink.focus();
      }
    }
  }

  toggle.addEventListener("click", function () {
    setMenuOpen(!isMenuOpen(), false);
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
    if (event.key === "Escape" && isMenuOpen()) {
      setMenuOpen(false, true);
      return;
    }

    if (event.key !== "Tab" || desktopMedia.matches || !isMenuOpen()) {
      return;
    }

    var focusableElements = getFocusableElements();
    if (!focusableElements.length) {
      event.preventDefault();
      closeButton.focus();
      return;
    }

    var firstElement = focusableElements[0];
    var lastElement = focusableElements[focusableElements.length - 1];
    var activeElement = document.activeElement;

    if (!drawer.contains(activeElement)) {
      event.preventDefault();
      (event.shiftKey ? lastElement : firstElement).focus();
      return;
    }

    if (event.shiftKey && activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  });

  if (typeof desktopMedia.addEventListener === "function") {
    desktopMedia.addEventListener("change", syncNavigationMode);
  } else {
    desktopMedia.addListener(syncNavigationMode);
  }

  syncNavigationMode();
})();
