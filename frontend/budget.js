(function () {
  const state = {
    root: null,
    month: null,
    data: null,
    loading: false,
    error: null,
  };

  function apiClient() {
    if (window.api) return window.api;
    return {
      async get(path) {
        const response = await fetch(`/api/v1${path}`);
        return readResponse(response);
      },
      async put(path, body) {
        const response = await fetch(`/api/v1${path}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        return readResponse(response);
      },
    };
  }

  async function readResponse(response) {
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error?.message || "Request failed");
    }
    return payload;
  }

  function formatINR(minor) {
    if (typeof window.formatINR === "function") return window.formatINR(minor);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format((minor || 0) / 100);
  }

  function formatPct(pctBp) {
    if (pctBp === null || pctBp === undefined) return "-";
    return `${(pctBp / 100).toFixed(1)}%`;
  }

  function monthLabel(month) {
    if (!month) return "";
    const [year, monthIndex] = month.split("-").map(Number);
    return new Date(year, monthIndex - 1, 1).toLocaleDateString("en-IN", {
      month: "long",
      year: "numeric",
    });
  }

  function statusLabel(status) {
    return {
      NO_BUDGET: "No budget",
      OK: "OK",
      WARNING: "Warning",
      EXCEEDED: "Exceeded",
    }[status] || status;
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

    const panel = make("section", "budget-panel");
    const header = make("div", "budget-panel__header");
    header.appendChild(make("h3", "budget-panel__title", "Monthly budget"));
    header.appendChild(make("span", "budget-panel__month", monthLabel(state.data?.month || state.month)));
    panel.appendChild(header);

    if (state.error) {
      panel.appendChild(make("div", "budget-panel__error", state.error));
    }

    if (state.loading) {
      panel.appendChild(make("div", "budget-panel__loading", "Loading budget..."));
      state.root.appendChild(panel);
      return;
    }

    const data = state.data;
    const form = make("form", "budget-panel__form");
    const label = make("label", "budget-panel__label");
    label.textContent = "Limit";
    const input = make("input", "budget-panel__input");
    input.type = "number";
    input.min = "1";
    input.step = "0.01";
    input.name = "limit";
    input.placeholder = "6500.00";
    input.value = data?.limit_minor ? (data.limit_minor / 100).toFixed(2) : "";
    label.appendChild(input);

    const button = make("button", "budget-panel__save", "Save");
    button.type = "submit";
    form.append(label, button);
    form.addEventListener("submit", onSave);
    panel.appendChild(form);

    if (data) {
      const stats = make("div", "budget-panel__stats");
      stats.appendChild(stat("Spent", formatINR(data.spent_minor)));
      stats.appendChild(stat("Remaining", data.remaining_minor === null ? "-" : formatINR(data.remaining_minor)));
      stats.appendChild(stat("Used", formatPct(data.pct_bp)));
      stats.appendChild(stat("Status", statusLabel(data.status)));
      panel.appendChild(stats);

      if (data.status === "EXCEEDED") {
        panel.appendChild(make("div", "budget-panel__banner", `${formatINR(Math.abs(data.remaining_minor))} over budget.`));
      }
    }

    state.root.appendChild(panel);
  }

  function stat(label, value) {
    const item = make("div", "budget-panel__stat");
    item.appendChild(make("span", "budget-panel__stat-label", label));
    item.appendChild(make("strong", "budget-panel__stat-value", value));
    return item;
  }

  async function onSave(event) {
    event.preventDefault();
    const input = event.currentTarget.elements.limit;
    const rupees = Number.parseFloat(input.value);
    if (!Number.isFinite(rupees) || rupees <= 0) {
      state.error = "Enter a budget of at least ₹1.00.";
      render();
      return;
    }

    const payload = { limit_minor: Math.round(rupees * 100) };
    if (state.data?.month || state.month) payload.month = state.data?.month || state.month;

    state.loading = true;
    state.error = null;
    render();
    try {
      state.data = await apiClient().put("/budget", payload);
      state.month = state.data.month;
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  async function refresh() {
    if (!state.root) return;
    state.loading = true;
    state.error = null;
    render();
    try {
      const query = state.month ? `?month=${encodeURIComponent(state.month)}` : "";
      state.data = await apiClient().get(`/budget${query}`);
      state.month = state.data.month;
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  function mount(el, opts = {}) {
    state.root = el;
    state.month = opts.month || null;
    refresh();
  }

  window.WDMMG_BudgetPanel = { mount, refresh };
})();
