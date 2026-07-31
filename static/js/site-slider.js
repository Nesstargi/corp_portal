(function () {
  var SWIPE_THRESHOLD = 48;

  function updateSlider(slider, nextIndex) {
    var track = slider.querySelector("[data-slider-track]");
    var slides = slider.querySelectorAll("[data-slide]");
    var dots = slider.querySelectorAll("[data-slide-dot]");

    if (!track || !slides.length) {
      return;
    }

    var maxIndex = slides.length - 1;
    var index = nextIndex;

    if (index < 0) {
      index = maxIndex;
    }

    if (index > maxIndex) {
      index = 0;
    }

    slider.dataset.activeIndex = String(index);
    track.style.transform = "translateX(-" + (index * 100) + "%)";

    slides.forEach(function (slide, slideIndex) {
      slide.setAttribute("aria-hidden", slideIndex === index ? "false" : "true");
    });

    dots.forEach(function (dot, dotIndex) {
      dot.classList.toggle("is-active", dotIndex === index);
      dot.setAttribute("aria-pressed", dotIndex === index ? "true" : "false");
    });
  }

  function initializeSlider(slider) {
    if (!slider || slider.dataset.initialized === "true") {
      return;
    }

    var slides = slider.querySelectorAll("[data-slide]");
    var prev = slider.querySelector("[data-slider-prev]");
    var next = slider.querySelector("[data-slider-next]");
    var dots = slider.querySelectorAll("[data-slide-dot]");
    var viewport = slider.querySelector(".image-slider__viewport");
    var touchStartX = null;
    var touchStartY = null;

    if (slides.length <= 1) {
      slider.dataset.initialized = "true";
      return;
    }

    if (!slider.hasAttribute("tabindex")) {
      slider.setAttribute("tabindex", "0");
    }

    if (!slider.hasAttribute("role")) {
      slider.setAttribute("role", "group");
    }

    if (!slider.hasAttribute("aria-label")) {
      slider.setAttribute("aria-label", "Галерея изображений");
    }

    function moveBy(offset) {
      updateSlider(slider, Number(slider.dataset.activeIndex || 0) + offset);
    }

    if (prev) {
      prev.addEventListener("click", function () {
        moveBy(-1);
      });
    }

    if (next) {
      next.addEventListener("click", function () {
        moveBy(1);
      });
    }

    dots.forEach(function (dot) {
      dot.addEventListener("click", function () {
        updateSlider(slider, Number(dot.dataset.slideDot));
      });
    });

    slider.addEventListener("keydown", function (event) {
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
        return;
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        moveBy(-1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        moveBy(1);
      }
    });

    if (viewport) {
      viewport.style.touchAction = "pan-y";

      viewport.addEventListener(
        "touchstart",
        function (event) {
          if (event.touches.length !== 1) {
            touchStartX = null;
            touchStartY = null;
            return;
          }

          touchStartX = event.touches[0].clientX;
          touchStartY = event.touches[0].clientY;
        },
        { passive: true }
      );

      viewport.addEventListener(
        "touchend",
        function (event) {
          if (touchStartX === null || touchStartY === null || !event.changedTouches.length) {
            return;
          }

          var deltaX = event.changedTouches[0].clientX - touchStartX;
          var deltaY = event.changedTouches[0].clientY - touchStartY;
          touchStartX = null;
          touchStartY = null;

          if (
            Math.abs(deltaX) < SWIPE_THRESHOLD ||
            Math.abs(deltaX) <= Math.abs(deltaY)
          ) {
            return;
          }

          moveBy(deltaX < 0 ? 1 : -1);
        },
        { passive: true }
      );

      viewport.addEventListener(
        "touchcancel",
        function () {
          touchStartX = null;
          touchStartY = null;
        },
        { passive: true }
      );
    }

    updateSlider(slider, 0);
    slider.dataset.initialized = "true";
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-image-slider]").forEach(initializeSlider);
  });
})();
