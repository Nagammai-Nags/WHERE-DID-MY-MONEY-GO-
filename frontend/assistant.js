(function () {
  const suggestedQuestions = [
    "Where did most of my money go this month?",
    "How much did I spend on small transactions?",
    "Which merchants did I spend the most at?",
    "How much did I spend on Food?",
    "What is my total spending?",
    "How is my budget?",
  ];

  const state = {
    root: null,
    messages: [],
    loading: false,
    error: null,
  };

  function apiClient() {
    if (window.api) return window.api;
    return {
      async post(path, body) {
        const response = await fetch(`/api/v1${path}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload?.error?.message || "Request failed");
        }
        return payload;
      },
    };
  }

  function formatINR(minor) {
    if (typeof window.formatINR === "function") return window.formatINR(minor);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format((minor || 0) / 100);
  }

  function empty(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function make(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function render() {
    if (!state.root) return;
    empty(state.root);

    const panel = make("section", "assistant-panel");
    panel.appendChild(make("h3", "assistant-panel__title", "Assistant"));

    const chips = make("div", "assistant-panel__chips");
    suggestedQuestions.forEach((question) => {
      const chip = make("button", "assistant-panel__chip", question);
      chip.type = "button";
      chip.addEventListener("click", () => ask(question));
      chips.appendChild(chip);
    });
    panel.appendChild(chips);

    const form = make("form", "assistant-panel__form");
    const input = make("input", "assistant-panel__input");
    input.name = "question";
    input.type = "text";
    input.maxLength = 500;
    input.placeholder = "Ask about your spending";
    const button = make("button", "assistant-panel__send", state.loading ? "Sending..." : "Send");
    button.type = "submit";
    button.disabled = state.loading;
    form.append(input, button);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      ask(input.value);
    });
    panel.appendChild(form);

    if (state.error) {
      panel.appendChild(make("div", "assistant-panel__error", state.error));
    }

    const list = make("div", "assistant-panel__conversation");
    state.messages.forEach((entry) => {
      list.appendChild(renderMessage(entry));
    });
    panel.appendChild(list);
    state.root.appendChild(panel);
  }

  function renderMessage(entry) {
    const item = make("article", "assistant-panel__message");
    item.appendChild(make("p", "assistant-panel__question", entry.question));

    if (!entry.response) {
      item.appendChild(make("p", "assistant-panel__answer", "Thinking..."));
      return item;
    }

    const response = entry.response;
    item.appendChild(make("p", "assistant-panel__answer", response.answer));
    item.appendChild(make("span", "assistant-panel__engine", `engine: ${response.engine || "rules"}`));

    if (response.facts?.length) {
      const table = make("table", "assistant-panel__facts");
      const thead = make("thead");
      const headRow = make("tr");
      ["Fact", "Amount", "Count"].forEach((heading) => headRow.appendChild(make("th", "", heading)));
      thead.appendChild(headRow);
      table.appendChild(thead);

      const tbody = make("tbody");
      response.facts.forEach((fact) => {
        const row = make("tr");
        row.appendChild(make("td", "", fact.label));
        row.appendChild(make("td", "", formatINR(fact.value_minor)));
        row.appendChild(make("td", "", fact.count === undefined ? "-" : String(fact.count)));
        tbody.appendChild(row);
      });
      table.appendChild(tbody);
      item.appendChild(table);
    }

    if (response.caveats?.length) {
      const caveats = make("ul", "assistant-panel__caveats");
      response.caveats.forEach((caveat) => caveats.appendChild(make("li", "", caveat)));
      item.appendChild(caveats);
    }

    return item;
  }

  async function ask(rawQuestion) {
    const question = rawQuestion.trim();
    if (!question) return;

    const entry = { question, response: null };
    state.messages.unshift(entry);
    state.loading = true;
    state.error = null;
    render();

    try {
      entry.response = await apiClient().post("/assistant/query", { question });
    } catch (error) {
      state.error = error.message;
      state.messages = state.messages.filter((item) => item !== entry);
    } finally {
      state.loading = false;
      render();
    }
  }

  function mount(el) {
    state.root = el;
    render();
  }

  window.WDMMG_AssistantPanel = { mount };
})();
