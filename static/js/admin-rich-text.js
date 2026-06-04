(function () {
  var FONT_SIZE_MAP = {
    "1": "0.78rem",
    "2": "0.9rem",
    "3": "1rem",
    "4": "1.15rem",
    "5": "1.25rem",
    "6": "1.35rem",
    "7": "1.35rem"
  };

  var blockFieldMap = {
    text: ["sort_order", "block_type", "title", "text"],
    image: ["sort_order", "block_type", "title", "gallery_uploads", "gallery_preview", "caption"],
    video: ["sort_order", "block_type", "title", "video_url", "caption"],
    quote: ["sort_order", "block_type", "title", "text", "caption"],
    feature: ["sort_order", "block_type", "title", "items_data"],
    sales_script: ["sort_order", "block_type", "title", "items_data"],
    instruction_step: ["sort_order", "block_type", "title", "text", "image", "caption"],
    specification: ["sort_order", "block_type", "title", "items_data"],
    table: ["sort_order", "block_type", "title", "items_data"],
    comparison_table: ["sort_order", "block_type", "title", "items_data"],
    file: ["sort_order", "block_type", "title", "document", "caption"]
  };

  function isTemplateInline(element) {
    return Boolean(element && element.closest && element.closest(".empty-form"));
  }

  function trimLeadingWhitespace(node) {
    if (!node) {
      return false;
    }

    if (node.nodeType === Node.TEXT_NODE) {
      node.textContent = node.textContent.replace(/^[\s\u00a0]+/, "");
      return node.textContent.trim().length > 0;
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return false;
    }

    var children = Array.from(node.childNodes);

    for (var index = 0; index < children.length; index += 1) {
      var child = children[index];
      var hasVisibleContent = trimLeadingWhitespace(child);

      if (hasVisibleContent) {
        return true;
      }

      if (
        child.nodeType === Node.TEXT_NODE &&
        child.textContent.trim().length === 0
      ) {
        child.remove();
      }

      if (
        child.nodeType === Node.ELEMENT_NODE &&
        child.textContent.trim().length === 0 &&
        !child.querySelector("img, video, iframe")
      ) {
        child.remove();
      }
    }

    return node.textContent.trim().length > 0;
  }

  function normalizeLists(root) {
    if (!root) {
      return;
    }

    root.querySelectorAll("ul, ol").forEach(function (list) {
      list.classList.add("rt-list");
    });

    root.querySelectorAll("li").forEach(function (item) {
      item.classList.add("rt-list-item");
      trimLeadingWhitespace(item);
    });
  }

  function moveChildren(source, target) {
    while (source.firstChild) {
      target.appendChild(source.firstChild);
    }
  }

  function normalizeFontTags(root) {
    if (!root) {
      return;
    }

    root.querySelectorAll("font").forEach(function (font) {
      var span = document.createElement("span");
      var color = font.getAttribute("color");
      var face = font.getAttribute("face");
      var size = font.getAttribute("size");
      var style = font.getAttribute("style");

      if (style) {
        span.setAttribute("style", style);
      }
      if (color) {
        span.style.color = color;
      }
      if (face) {
        span.style.fontFamily = face;
      }
      if (size && FONT_SIZE_MAP[String(size)]) {
        span.style.fontSize = FONT_SIZE_MAP[String(size)];
      }

      moveChildren(font, span);
      font.replaceWith(span);
    });
  }

  function normalizeLinks(root) {
    if (!root) {
      return;
    }

    root.querySelectorAll("a[href]").forEach(function (link) {
      var href = String(link.getAttribute("href") || "");
      if (/^https?:\/\//i.test(href)) {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener noreferrer");
      }
    });
  }

  function normalizeEditor(root) {
    normalizeLists(root);
    normalizeFontTags(root);
    normalizeLinks(root);
  }

  function syncToTextarea(widget) {
    var editor = widget.querySelector("[data-editor-surface]");
    var textarea = widget.querySelector(".rt-editor-source");

    if (!editor || !textarea) {
      return;
    }

    normalizeEditor(editor);
    textarea.value = editor.innerHTML.trim();
  }

  function syncAllWidgets(root) {
    var sourceRoot = root || document;

    sourceRoot.querySelectorAll("[data-rich-text-widget]").forEach(function (widget) {
      if (!isTemplateInline(widget)) {
        syncToTextarea(widget);
      }
    });
  }

  function getFieldNode(container, fieldName) {
    return container.querySelector(".field-" + fieldName);
  }

  function toggleBlockFields(inline) {
    var blockTypeField = getFieldNode(inline, "block_type");
    var select = blockTypeField ? blockTypeField.querySelector("select") : null;
    var visibleFields = blockFieldMap.text;

    if (!select) {
      return;
    }

    if (blockFieldMap[select.value]) {
      visibleFields = blockFieldMap[select.value];
    }

    Object.keys(blockFieldMap).reduce(function (all, key) {
      blockFieldMap[key].forEach(function (fieldName) {
        if (all.indexOf(fieldName) === -1) {
          all.push(fieldName);
        }
      });
      return all;
    }, []).forEach(function (fieldName) {
      var fieldNode = getFieldNode(inline, fieldName);
      if (!fieldNode || fieldName === "block_type" || fieldName === "sort_order") {
        return;
      }

      if (visibleFields.indexOf(fieldName) !== -1) {
        fieldNode.classList.remove("rt-editor-field-hidden");
      } else {
        fieldNode.classList.add("rt-editor-field-hidden");
      }
    });
  }

  function initializeInlineBehavior(inline) {
    if (!inline || isTemplateInline(inline) || inline.dataset.blockFieldsInitialized === "true") {
      return;
    }

    if (document.getElementById("learning-admin-config")) {
      return;
    }

    var blockTypeField = getFieldNode(inline, "block_type");
    var select = blockTypeField ? blockTypeField.querySelector("select") : null;

    if (!select) {
      return;
    }

    select.addEventListener("change", function () {
      toggleBlockFields(inline);
    });

    toggleBlockFields(inline);
    inline.dataset.blockFieldsInitialized = "true";
  }

  function initializeWidget(widget) {
    if (!widget || isTemplateInline(widget) || widget.dataset.initialized === "true") {
      return;
    }

    var editor = widget.querySelector("[data-editor-surface]");
    var textarea = widget.querySelector(".rt-editor-source");
    var buttons = widget.querySelectorAll("[data-command]");
    var colorInputs = widget.querySelectorAll("[data-color-command]");
    var formatSelect = widget.querySelector("[data-format-block]");
    var fontSizeSelect = widget.querySelector("[data-font-size]");
    var linkButtons = widget.querySelectorAll("[data-link-command]");

    if (!editor || !textarea) {
      return;
    }

    editor.innerHTML = textarea.value || "";
    normalizeEditor(editor);

    function nodeBelongsToEditor(node) {
      if (!node) {
        return false;
      }
      var element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
      return Boolean(element && (element === editor || editor.contains(element)));
    }

    function saveSelection() {
      var selection = window.getSelection ? window.getSelection() : null;
      if (!selection || !selection.rangeCount) {
        return;
      }

      var range = selection.getRangeAt(0);
      if (!nodeBelongsToEditor(range.commonAncestorContainer)) {
        return;
      }

      widget._savedRange = range.cloneRange();
    }

    function restoreSelection() {
      var selection = window.getSelection ? window.getSelection() : null;
      if (!selection || !widget._savedRange) {
        editor.focus();
        return;
      }

      selection.removeAllRanges();
      selection.addRange(widget._savedRange);
      editor.focus();
    }

    function runCommand(command, value) {
      restoreSelection();
      document.execCommand(command, false, value || null);
      normalizeEditor(editor);
      saveSelection();
      syncToTextarea(widget);
    }

    function applyFormatBlock(value) {
      if (!value) {
        return;
      }
      runCommand("formatBlock", value);
    }

    function applyFontSize(value) {
      if (!value) {
        return;
      }

      restoreSelection();
      document.execCommand("fontSize", false, "7");
      editor.querySelectorAll('font[size="7"]').forEach(function (font) {
        var span = document.createElement("span");
        span.style.fontSize = value;
        moveChildren(font, span);
        font.replaceWith(span);
      });
      normalizeEditor(editor);
      saveSelection();
      syncToTextarea(widget);
    }

    function normalizeUrl(value) {
      var url = String(value || "").trim();
      if (!url) {
        return "";
      }
      if (/^(https?:|mailto:|tel:|#|\/)/i.test(url)) {
        return url;
      }
      return "https://" + url;
    }

    function applyLinkCommand(mode) {
      if (mode === "remove") {
        runCommand("unlink");
        return;
      }

      var url = normalizeUrl(window.prompt("Введите ссылку", "https://"));
      if (!url) {
        return;
      }

      runCommand("createLink", url);
    }

    editor.addEventListener("input", function () {
      saveSelection();
      syncToTextarea(widget);
    });

    ["keyup", "mouseup", "focus", "blur"].forEach(function (eventName) {
      editor.addEventListener(eventName, saveSelection);
    });

    buttons.forEach(function (button) {
      button.addEventListener("mousedown", function (event) {
        event.preventDefault();
        saveSelection();
      });

      button.addEventListener("click", function () {
        runCommand(button.dataset.command);
      });
    });

    colorInputs.forEach(function (input) {
      input.addEventListener("mousedown", function (event) {
        saveSelection();
      });

      input.addEventListener("input", function () {
        runCommand(input.dataset.colorCommand, input.value);
      });
    });

    if (formatSelect) {
      formatSelect.addEventListener("mousedown", saveSelection);
      formatSelect.addEventListener("change", function () {
        applyFormatBlock(formatSelect.value);
      });
    }

    if (fontSizeSelect) {
      fontSizeSelect.addEventListener("mousedown", saveSelection);
      fontSizeSelect.addEventListener("change", function () {
        applyFontSize(fontSizeSelect.value);
        fontSizeSelect.value = "";
      });
    }

    linkButtons.forEach(function (button) {
      button.addEventListener("mousedown", function (event) {
        event.preventDefault();
        saveSelection();
      });

      button.addEventListener("click", function () {
        applyLinkCommand(button.dataset.linkCommand);
      });
    });

    if (textarea.form) {
      if (textarea.form.dataset.richTextSubmitBound !== "true") {
        textarea.form.addEventListener("submit", function () {
          syncAllWidgets(textarea.form);
        });
        textarea.form.dataset.richTextSubmitBound = "true";
      }
    }

    widget.dataset.initialized = "true";
  }

  function forEachMatching(root, selector, callback) {
    if (!root) {
      return;
    }

    if (root.matches && root.matches(selector)) {
      callback(root);
    }

    root.querySelectorAll(selector).forEach(callback);
  }

  function initializeAll(root) {
    var sourceRoot = root || document;
    forEachMatching(sourceRoot, "[data-rich-text-widget]", initializeWidget);
    forEachMatching(sourceRoot, ".inline-related", initializeInlineBehavior);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initializeAll(document);
  });

  document.addEventListener("formset:added", function (event) {
    var addedRoot = event.target;

    if (addedRoot && addedRoot.querySelectorAll) {
      addedRoot.querySelectorAll("[data-rich-text-widget]").forEach(function (widget) {
        delete widget.dataset.initialized;
      });

      addedRoot.querySelectorAll(".inline-related").forEach(function (inline) {
        delete inline.dataset.blockFieldsInitialized;
      });
    }

    initializeAll(addedRoot);
  });
})();
