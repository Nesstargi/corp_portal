(function () {
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

    if (slides.length <= 1) {
      slider.dataset.initialized = "true";
      return;
    }

    if (prev) {
      prev.addEventListener("click", function () {
        updateSlider(slider, Number(slider.dataset.activeIndex || 0) - 1);
      });
    }

    if (next) {
      next.addEventListener("click", function () {
        updateSlider(slider, Number(slider.dataset.activeIndex || 0) + 1);
      });
    }

    dots.forEach(function (dot) {
      dot.addEventListener("click", function () {
        updateSlider(slider, Number(dot.dataset.slideDot));
      });
    });

    updateSlider(slider, 0);
    slider.dataset.initialized = "true";
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-image-slider]").forEach(initializeSlider);
  });
})();
