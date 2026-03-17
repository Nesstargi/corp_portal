(function () {
  var blockFieldMap = {
    text: ["sort_order", "block_type", "title", "text"],
    image: ["sort_order", "block_type", "title", "image", "caption"],
    video: ["sort_order", "block_type", "title", "video_url", "caption"],
    quote: ["sort_order", "block_type", "title", "text", "caption"],
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

  function syncToTextarea(widget) {
    var editor = widget.querySelector("[data-editor-surface]");
    var textarea = widget.querySelector(".rt-editor-source");

    if (!editor || !textarea) {
      return;
    }

    normalizeLists(editor);
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

    if (!editor || !textarea) {
      return;
    }

    editor.innerHTML = textarea.value || "";
    normalizeLists(editor);

    editor.addEventListener("input", function () {
      syncToTextarea(widget);
    });

    buttons.forEach(function (button) {
      button.addEventListener("mousedown", function (event) {
        event.preventDefault();
      });

      button.addEventListener("click", function () {
        editor.focus();
        document.execCommand(button.dataset.command, false, null);
        normalizeLists(editor);
        syncToTextarea(widget);
      });
    });

    colorInputs.forEach(function (input) {
      input.addEventListener("mousedown", function (event) {
        event.preventDefault();
      });

      input.addEventListener("input", function () {
        editor.focus();
        document.execCommand(input.dataset.colorCommand, false, input.value);
        normalizeLists(editor);
        syncToTextarea(widget);
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
