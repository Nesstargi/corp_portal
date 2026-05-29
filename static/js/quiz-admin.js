(function () {
  function parseOptions(input) {
    if (!input || !input.value) {
      return [];
    }

    try {
      var parsed = JSON.parse(input.value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function writeOptions(input, items) {
    if (!input) {
      return;
    }
    input.value = JSON.stringify(items);
  }

  function getQuestionRows() {
    return document.querySelectorAll(".dynamic-questions");
  }

  function getOptionsInput(row) {
    return row.querySelector('[id$="-options_data"]');
  }

  function ensureOptionsSeeded(input) {
    var options = parseOptions(input);

    if (options.length >= 2) {
      return;
    }

    if (!options.length) {
      options = [{ text: "", is_correct: false }, { text: "", is_correct: false }];
    }

    if (options.length === 1) {
      options.push({ text: "", is_correct: false });
    }

    writeOptions(input, options);
  }

  function renderOptionRow(option, index, groupName) {
    return (
      '<div class="quiz-options__row" data-quiz-option="' +
      index +
      '">' +
      '<div class="quiz-options__field">' +
      '<label class="quiz-options__label">Вариант ответа</label>' +
      '<input type="text" value="' +
      escapeHtml(option.text || "") +
      '" data-quiz-option-text="' +
      index +
      '">' +
      "</div>" +
      '<label class="quiz-options__correct">' +
      '<input type="radio" name="' +
      groupName +
      '" value="' +
      index +
      '"' +
      (option.is_correct ? " checked" : "") +
      ' data-quiz-option-correct="' +
      index +
      '">' +
      "<span>Правильный вариант</span>" +
      "</label>" +
      '<button type="button" class="quiz-options__remove" data-remove-quiz-option="' +
      index +
      '">Удалить</button>' +
      "</div>"
    );
  }

  function renderEditor(row) {
    if (!row || row.classList.contains("empty-form")) {
      return;
    }

    var input = getOptionsInput(row);
    if (!input) {
      return;
    }

    ensureOptionsSeeded(input);

    var editor = row.querySelector("[data-quiz-options-editor]");
    if (!editor) {
      return;
    }

    var options = parseOptions(input);
    var groupName = (input.id || "quiz-options").replace(/[^a-z0-9_-]+/gi, "-") + "-correct";
    var renderKey = JSON.stringify(options);

    if (editor.dataset.renderKey === renderKey) {
      return;
    }

    editor.innerHTML =
      '<div class="quiz-options">' +
      '<div class="quiz-options__intro">' +
      '<div class="quiz-options__title">Варианты ответа</div>' +
      '<p class="help">Добавь варианты ответа и отметь один правильный. После ответа сотрудник увидит пояснение ниже под вопросом.</p>' +
      "</div>" +
      '<div class="quiz-options__list">' +
      options
        .map(function (option, index) {
          return renderOptionRow(option, index, groupName);
        })
        .join("") +
      "</div>" +
      '<button type="button" class="quiz-options__add" data-add-quiz-option="true">Добавить ещё вариант</button>' +
      "</div>";
    editor.dataset.renderKey = renderKey;
  }

  function collectOptions(row) {
    var input = getOptionsInput(row);
    if (!input) {
      return;
    }

    var options = [];
    row.querySelectorAll("[data-quiz-option]").forEach(function (item) {
      var textInput = item.querySelector("[data-quiz-option-text]");
      var correctInput = item.querySelector("[data-quiz-option-correct]");
      var text = textInput ? String(textInput.value || "").trim() : "";

      if (!text) {
        return;
      }

      options.push({
        text: text,
        is_correct: Boolean(correctInput && correctInput.checked),
      });
    });

    if (!options.length) {
      options = [{ text: "", is_correct: false }, { text: "", is_correct: false }];
    }

    if (options.length === 1) {
      options.push({ text: "", is_correct: false });
    }

    writeOptions(input, options);
  }

  function addOption(row) {
    var input = getOptionsInput(row);
    var options = parseOptions(input);
    options.push({ text: "", is_correct: false });
    writeOptions(input, options);
    renderEditor(row);
  }

  function removeOption(row, index) {
    var input = getOptionsInput(row);
    var options = parseOptions(input).filter(function (_item, optionIndex) {
      return optionIndex !== index;
    });

    if (options.length < 2) {
      options.push({ text: "", is_correct: false });
    }

    writeOptions(input, options);
    renderEditor(row);
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function syncEditors() {
    getQuestionRows().forEach(renderEditor);
  }

  document.addEventListener("input", function (event) {
    if (event.target && event.target.matches("[data-quiz-option-text]")) {
      collectOptions(event.target.closest(".dynamic-questions"));
    }
  });

  document.addEventListener("change", function (event) {
    if (event.target && event.target.matches("[data-quiz-option-correct]")) {
      collectOptions(event.target.closest(".dynamic-questions"));
    }
  });

  document.addEventListener("click", function (event) {
    if (event.target && event.target.matches("[data-add-quiz-option]")) {
      event.preventDefault();
      addOption(event.target.closest(".dynamic-questions"));
      return;
    }

    if (event.target && event.target.matches("[data-remove-quiz-option]")) {
      event.preventDefault();
      removeOption(
        event.target.closest(".dynamic-questions"),
        Number(event.target.dataset.removeQuizOption)
      );
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    syncEditors();

    var group = document.getElementById("questions-group");
    if (!group) {
      return;
    }

    var observer = new MutationObserver(function (mutations) {
      var shouldSync = false;

      Array.prototype.forEach.call(mutations || [], function (mutation) {
        Array.prototype.forEach.call(mutation.addedNodes || [], function (node) {
          if (shouldSync || !node || !node.querySelector) {
            return;
          }

          if (
            (node.classList && node.classList.contains("dynamic-questions")) ||
            node.querySelector(".dynamic-questions")
          ) {
            shouldSync = true;
          }
        });
      });

      if (shouldSync) {
        syncEditors();
      }
    });

    observer.observe(group, {
      childList: true,
      subtree: true,
    });
  });
})();
