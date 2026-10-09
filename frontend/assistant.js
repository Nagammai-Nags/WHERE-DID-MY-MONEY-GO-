(function () {
  const suggestedQuestions = [
    { label: "Top category", question: "Where did most of my money go this month?" },
    { label: "Small spends", question: "How much did I spend on small transactions?" },
    { label: "Top merchants", question: "Which merchants did I spend the most at?" },
    { label: "Food total", question: "How much did I spend on Food?" },
    { label: "Total spend", question: "What is my total spending?" },
    { label: "Budget", question: "How is my budget?" },
  ];

  const state = {
    root: null,
    messages: [],
    loading: false,
    error: null,
  };

  const styleId = "wdmmg-assistant-styles";

  function injectStyles() {
    if (document.getElementById(styleId)) return;
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      .assistant-panel{display:grid;gap:18px}
      .assistant-panel__hero{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,rgba(56,189,248,.13),rgba(34,211,197,.06) 58%,rgba(251,191,36,.08));padding:22px;box-shadow:var(--shadow)}
      .assistant-panel__hero:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(255,255,255,.04),transparent 34%,rgba(255,255,255,.025));pointer-events:none}
      .assistant-panel__hero-content{position:relative;display:flex;align-items:flex-start;justify-content:space-between;gap:18px}
      .assistant-panel__eyebrow{margin:0 0 8px;color:var(--muted);font-size:11px;font-weight:800;letter-spacing:1.3px;text-transform:uppercase}
      .assistant-panel__title{margin:0;font:750 25px/1.15 Inter,"Aptos","Segoe UI",system-ui,sans-serif;color:var(--ink);letter-spacing:-.6px}
      .assistant-panel__subtitle{max-width:620px;margin:9px 0 0;color:var(--muted);font-size:14px;line-height:1.55}
      .assistant-panel__rule-badge{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;border:1px solid rgba(56,189,248,.32);background:rgba(56,189,248,.10);color:var(--ink);border-radius:999px;padding:8px 11px;font-size:12px;font-weight:750}
      .assistant-panel__rule-badge:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 3px rgba(34,211,197,.13)}
      .assistant-panel__composer{display:grid;gap:12px;border:1px solid var(--line);border-radius:18px;background:var(--card);padding:16px;box-shadow:var(--shadow)}
      .assistant-panel__chips{display:flex;gap:8px;overflow-x:auto;padding-bottom:2px;scrollbar-width:none}
      .assistant-panel__chips::-webkit-scrollbar{display:none}
      .assistant-panel__chip{flex:0 0 auto;border:1px solid var(--line);background:rgba(255,255,255,.04);color:var(--ink);border-radius:999px;padding:9px 12px;font-size:12px;font-weight:750;transition:transform .15s,border-color .15s,background .15s}
      .assistant-panel__chip:hover{transform:translateY(-1px);border-color:var(--green);background:rgba(34,211,197,.10)}
      .assistant-panel__chip:disabled{opacity:.58;cursor:wait;transform:none}
      .assistant-panel__form{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center}
      .assistant-panel__input{width:100%;min-height:48px;padding:13px 15px;border-radius:13px;font-size:14px;background:rgba(255,255,255,.03)}
      .assistant-panel__send{min-height:48px;border:0;border-radius:13px;padding:0 19px;background:var(--green);color:#06111a;font-weight:850;box-shadow:0 4px 0 rgba(0,0,0,.18)}
      .assistant-panel__send:hover{filter:brightness(1.04)}
      .assistant-panel__send:disabled{opacity:.65;cursor:wait;box-shadow:none}
      .assistant-panel__error{border:1px solid var(--red);background:var(--red-soft);color:var(--ink);border-radius:13px;padding:12px 14px;font-size:13px}
      .assistant-panel__conversation{display:grid;gap:14px}
      .assistant-panel__empty{border:1px dashed var(--line);border-radius:18px;padding:26px;text-align:center;color:var(--muted);background:rgba(255,255,255,.025)}
      .assistant-panel__empty strong{display:block;color:var(--ink);font-size:16px;margin-bottom:6px}
      .assistant-panel__message{display:grid;gap:10px}
      .assistant-panel__question{justify-self:end;max-width:min(720px,92%);margin:0;padding:11px 14px;border-radius:15px 15px 4px 15px;background:var(--green);color:#06111a;font-size:14px;font-weight:750;line-height:1.45}
      .assistant-panel__response{border:1px solid var(--line);border-radius:18px;background:var(--card);box-shadow:var(--shadow);padding:17px;display:grid;gap:14px}
      .assistant-panel__answer-row{display:flex;align-items:flex-start;gap:12px}
      .assistant-panel__avatar{width:34px;height:34px;border-radius:12px;display:grid;place-items:center;flex:0 0 34px;background:rgba(56,189,248,.13);border:1px solid rgba(56,189,248,.28);color:var(--ink);font-weight:850}
      .assistant-panel__answer{margin:0;color:var(--ink);font-size:15px;line-height:1.65}
      .assistant-panel__meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:10px}
      .assistant-panel__engine,.assistant-panel__status,.assistant-panel__intent{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:6px 9px;color:var(--muted);font-size:11px;font-weight:750;text-transform:lowercase}
      .assistant-panel__status-ok{color:var(--green);border-color:rgba(34,211,197,.35);background:rgba(34,211,197,.08)}
      .assistant-panel__facts-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:14px}
      .assistant-panel__facts{width:100%;border-collapse:collapse;background:transparent}
      .assistant-panel__facts th{padding:11px 13px;text-align:left;color:var(--muted);font-size:11px;letter-spacing:.65px;text-transform:uppercase;background:rgba(255,255,255,.035);white-space:nowrap}
      .assistant-panel__facts td{padding:12px 13px;border-top:1px solid var(--line);font-size:13px;color:var(--ink);white-space:nowrap}
      .assistant-panel__facts td:nth-child(2){font-weight:800;font-variant-numeric:tabular-nums}
      .assistant-panel__facts td:last-child,.assistant-panel__facts th:last-child{text-align:right}
      .assistant-panel__caveats{display:grid;gap:7px;list-style:none;margin:0;padding:0}
      .assistant-panel__caveats li{position:relative;padding:10px 12px 10px 31px;border:1px solid var(--line);border-radius:12px;color:var(--muted);font-size:13px;line-height:1.45;background:rgba(255,255,255,.025)}
      .assistant-panel__caveats li:before{content:"i";position:absolute;left:12px;top:10px;width:13px;height:13px;border-radius:50%;display:grid;place-items:center;background:rgba(56,189,248,.18);color:var(--ink);font-size:10px;font-weight:850}
      .assistant-panel__thinking{display:inline-flex;align-items:center;gap:7px;color:var(--muted)}
      .assistant-panel__thinking:before{content:"";width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:13px 0 0 var(--blue),26px 0 0 var(--orange);animation:assistant-thinking .8s ease-in-out infinite alternate}
      @keyframes assistant-thinking{to{transform:translateY(-3px)}}
      @media(max-width:640px){.assistant-panel__hero,.assistant-panel__composer,.assistant-panel__response{border-radius:15px}.assistant-panel__hero{padding:18px}.assistant-panel__hero-content{display:grid}.assistant-panel__title{font-size:22px}.assistant-panel__form{grid-template-columns:1fr}.assistant-panel__send{width:100%}.assistant-panel__question{max-width:100%}.assistant-panel__answer-row{align-items:flex-start}.assistant-panel__facts th,.assistant-panel__facts td{padding:10px 11px}}
    `;
    document.head.appendChild(style);
  }

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
    injectStyles();
    empty(state.root);

    const panel = make("section", "assistant-panel");

    const hero = make("div", "assistant-panel__hero");
    const heroContent = make("div", "assistant-panel__hero-content");
    const heroText = make("div");
    heroText.appendChild(make("p", "assistant-panel__eyebrow", "Grounded assistant"));
    heroText.appendChild(make("h2", "assistant-panel__title", "Ask what changed in your spending"));
    heroText.appendChild(
      make("p", "assistant-panel__subtitle", "Answers are written from computed totals, with the source facts shown beside each response.")
    );
    heroContent.appendChild(heroText);
    heroContent.appendChild(make("span", "assistant-panel__rule-badge", "rules engine"));
    hero.appendChild(heroContent);
    panel.appendChild(hero);

    const composer = make("div", "assistant-panel__composer");

    const chips = make("div", "assistant-panel__chips");
    suggestedQuestions.forEach(({ label, question }) => {
      const chip = make("button", "assistant-panel__chip", label);
      chip.type = "button";
      chip.title = question;
      chip.disabled = state.loading;
      chip.addEventListener("click", () => ask(question));
      chips.appendChild(chip);
    });
    composer.appendChild(chips);

    const form = make("form", "assistant-panel__form");
    const input = make("input", "assistant-panel__input");
    input.name = "question";
    input.type = "text";
    input.maxLength = 500;
    input.placeholder = "Ask about categories, merchants, budget, or totals";
    input.autocomplete = "off";
    const button = make("button", "assistant-panel__send", state.loading ? "Sending..." : "Send");
    button.type = "submit";
    button.disabled = state.loading;
    form.append(input, button);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      ask(input.value);
    });
    composer.appendChild(form);
    panel.appendChild(composer);

    if (state.error) {
      panel.appendChild(make("div", "assistant-panel__error", state.error));
    }

    const list = make("div", "assistant-panel__conversation");
    if (state.messages.length) {
      state.messages.forEach((entry) => {
        list.appendChild(renderMessage(entry));
      });
    } else {
      const emptyState = make("div", "assistant-panel__empty");
      emptyState.appendChild(make("strong", "", "Start with a suggested question"));
      emptyState.appendChild(make("span", "", "The response will include the exact facts used to produce the answer."));
      list.appendChild(emptyState);
    }
    panel.appendChild(list);
    state.root.appendChild(panel);
  }

  function renderMessage(entry) {
    const item = make("article", "assistant-panel__message");
    item.appendChild(make("p", "assistant-panel__question", entry.question));

    const responseCard = make("div", "assistant-panel__response");
    const answerRow = make("div", "assistant-panel__answer-row");
    answerRow.appendChild(make("div", "assistant-panel__avatar", "₹"));
    const answerBody = make("div");

    if (!entry.response) {
      answerBody.appendChild(make("p", "assistant-panel__answer assistant-panel__thinking", "Checking the computed facts"));
      answerRow.appendChild(answerBody);
      responseCard.appendChild(answerRow);
      item.appendChild(responseCard);
      return item;
    }

    const response = entry.response;
    answerBody.appendChild(make("p", "assistant-panel__answer", response.answer));
    const meta = make("div", "assistant-panel__meta");
    meta.appendChild(make("span", "assistant-panel__engine", `engine: ${response.engine || "rules"}`));
    meta.appendChild(make("span", "assistant-panel__intent", response.intent || "unknown"));
    meta.appendChild(make("span", `assistant-panel__status assistant-panel__status-${String(response.validation_status || "ok").toLowerCase()}`, response.validation_status || "OK"));
    answerBody.appendChild(meta);
    answerRow.appendChild(answerBody);
    responseCard.appendChild(answerRow);

    if (response.facts?.length) {
      const tableWrap = make("div", "assistant-panel__facts-wrap");
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
      tableWrap.appendChild(table);
      responseCard.appendChild(tableWrap);
    }

    if (response.caveats?.length) {
      const caveats = make("ul", "assistant-panel__caveats");
      response.caveats.forEach((caveat) => caveats.appendChild(make("li", "", caveat)));
      responseCard.appendChild(caveats);
    }

    item.appendChild(responseCard);
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
