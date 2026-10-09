(function () {
  const state = {
    root: null,
    data: null,
    loading: false,
    error: null,
    from: "2026-10-01",
    to: "2026-10-31",
    drilldown: null,
  };

  const styleId = "wdmmg-graph-analytics-styles";

  function injectStyles() {
    if (document.getElementById(styleId)) return;
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      .graph-analytics{display:grid;gap:18px}
      .graph-controls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr)) auto auto;gap:10px;align-items:end;border:1px solid var(--line);background:var(--card);border-radius:16px;padding:16px;box-shadow:var(--shadow)}
      .graph-controls label{display:grid;gap:7px;color:var(--muted);font-size:12px;font-weight:750}
      .graph-controls input{min-height:42px;padding:9px 11px}
      .graph-period{color:var(--muted);font-size:13px}
      .graph-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
      .graph-card{border:1px solid var(--line);background:var(--card);border-radius:16px;padding:17px;box-shadow:var(--shadow);min-width:0}
      .graph-card.full{grid-column:1/-1}
      .graph-card h2{margin:0 0 12px;font-size:18px}
      .graph-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
      .graph-kpi{border:1px solid var(--line);border-radius:14px;padding:14px;background:rgba(255,255,255,.03)}
      .graph-kpi span{display:block;color:var(--muted);font-size:11px;font-weight:800;letter-spacing:.7px;text-transform:uppercase}
      .graph-kpi strong{display:block;margin-top:8px;font-size:20px;overflow-wrap:anywhere}
      .graph-svg{width:100%;height:auto;display:block}
      .graph-axis{stroke:var(--line);stroke-width:1}
      .graph-label{fill:var(--muted);font-size:11px}
      .graph-line{fill:none;stroke:var(--green);stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
      .graph-dot{fill:var(--green);cursor:pointer}
      .graph-bar{fill:var(--blue);cursor:pointer}
      .graph-bar:hover,.graph-dot:hover{filter:brightness(1.2)}
      .merchant-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;align-items:center;border:0;background:transparent;color:var(--ink);width:100%;text-align:left;padding:9px 0;border-bottom:1px solid var(--line)}
      .merchant-row:last-child{border-bottom:0}
      .merchant-row strong,.merchant-row span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .merchant-track{grid-column:1/-1;height:8px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden}
      .merchant-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--green),var(--blue))}
      .graph-drilldown{border:1px solid var(--line);background:var(--card);border-radius:16px;padding:17px;box-shadow:var(--shadow)}
      .graph-drilldown-header{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:12px}
      .graph-drilldown table{width:100%;border-collapse:collapse}
      .graph-drilldown th,.graph-drilldown td{padding:10px;border-top:1px solid var(--line);font-size:12px;text-align:left;white-space:nowrap}
      .graph-drilldown th{color:var(--muted);text-transform:uppercase;font-size:10px;letter-spacing:.6px}
      .graph-empty{border:1px dashed var(--line);border-radius:16px;padding:26px;text-align:center;color:var(--muted)}
      @media(max-width:760px){.graph-controls{grid-template-columns:1fr}.graph-grid,.graph-summary{grid-template-columns:1fr}.graph-card.full{grid-column:auto}.graph-drilldown{overflow-x:auto}}
    `;
    document.head.appendChild(style);
  }

  function make(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function empty(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function money(minor) {
    return window.formatINR ? window.formatINR(minor) : `₹${((minor || 0) / 100).toFixed(2)}`;
  }

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }

  async function refresh() {
    if (!state.root) return;
    state.loading = true;
    state.error = null;
    state.drilldown = null;
    render();
    try {
      state.data = await window.api.get(`/analytics/graph?from=${encodeURIComponent(state.from)}&to=${encodeURIComponent(state.to)}`);
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  function render() {
    if (!state.root) return;
    injectStyles();
    empty(state.root);

    const panel = make("section", "graph-analytics");
    panel.appendChild(renderControls());

    if (state.error) panel.appendChild(make("div", "error-state", state.error));
    if (state.loading) {
      panel.appendChild(make("div", "loading", "Loading graph analytics..."));
      state.root.appendChild(panel);
      return;
    }
    if (!state.data) {
      panel.appendChild(make("div", "graph-empty", "Choose a period and apply the filter."));
      state.root.appendChild(panel);
      return;
    }

    panel.appendChild(make("div", "graph-period", `Selected period: ${state.data.period.from} to ${state.data.period.to} · grouped by ${state.data.period.grouping}`));
    if (state.data.summary.net_spend_minor === 0 && state.data.summary.income_minor === 0) {
      panel.appendChild(make("div", "graph-empty", "No matching transactions for this period."));
      state.root.appendChild(panel);
      return;
    }

    panel.appendChild(renderSummary());
    const grid = make("div", "graph-grid");
    grid.appendChild(renderTrend());
    grid.appendChild(renderIncomeVsSpend());
    grid.appendChild(renderCategoryChart());
    grid.appendChild(renderMerchantChart());
    grid.appendChild(renderActivityChart());
    panel.appendChild(grid);
    if (state.drilldown) panel.appendChild(renderDrilldown());
    state.root.appendChild(panel);
  }

  function renderControls() {
    const form = make("form", "graph-controls");
    form.innerHTML = `
      <label>Start date<input type="date" name="from" value="${esc(state.from)}"></label>
      <label>End date<input type="date" name="to" value="${esc(state.to)}"></label>
      <button class="button primary" type="submit">Apply filter</button>
      <button class="button subtle" type="button" data-reset>Reset</button>
    `;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const nextFrom = form.elements.from.value;
      const nextTo = form.elements.to.value;
      if (nextFrom > nextTo) {
        state.error = "Start date must be on or before end date.";
        render();
        return;
      }
      state.from = nextFrom;
      state.to = nextTo;
      refresh();
    });
    form.querySelector("[data-reset]").addEventListener("click", () => {
      state.from = "2026-10-01";
      state.to = "2026-10-31";
      refresh();
    });
    return form;
  }

  function renderSummary() {
    const summary = state.data.summary;
    const host = make("div", "graph-summary");
    const highest = summary.highest_merchant;
    [
      ["Net expenditure", money(summary.net_spend_minor)],
      ["Income", money(summary.income_minor)],
      ["Spending txns", String(summary.spending_transaction_count)],
      ["Daily average", money(summary.average_daily_net_spend_minor)],
      ["Top merchant", highest ? `${highest.display_merchant} · ${money(highest.total_minor)}` : "None"],
      ["Previous period", summary.previous_period ? `${money(summary.previous_period.delta_minor)} change` : "No comparison"],
    ].forEach(([label, value]) => {
      const card = make("article", "graph-kpi");
      card.appendChild(make("span", "", label));
      card.appendChild(make("strong", "", value));
      host.appendChild(card);
    });
    return host;
  }

  function renderTrend() {
    const card = make("article", "graph-card full");
    card.appendChild(make("h2", "", "Spending trend"));
    card.appendChild(lineChart(state.data.time_series, "net_spend_minor", (point) => setDrilldown("Date", point.date, transactionsForDate(point.date))));
    return card;
  }

  function renderActivityChart() {
    const card = make("article", "graph-card full");
    card.appendChild(make("h2", "", "Transaction activity"));
    card.appendChild(barChart(state.data.activity, "spending_transaction_count", "date", (point) => setDrilldown("Date", point.date, transactionsForDate(point.date))));
    return card;
  }

  function renderCategoryChart() {
    const card = make("article", "graph-card");
    card.appendChild(make("h2", "", "Category-wise expenditure"));
    card.appendChild(barChart(state.data.category_breakdown, "total_minor", "category", (point) => setDrilldown("Category", point.category, point.transactions)));
    return card;
  }

  function renderMerchantChart() {
    const card = make("article", "graph-card");
    card.appendChild(make("h2", "", "Merchant-wise expenditure"));
    const list = make("div");
    const max = Math.max(1, ...state.data.merchant_breakdown.map((item) => item.total_minor));
    state.data.merchant_breakdown.slice(0, 8).forEach((merchant) => {
      const row = make("button", "merchant-row");
      row.type = "button";
      row.innerHTML = `<strong>${esc(merchant.display_merchant)}</strong><span>${money(merchant.total_minor)}</span><div class="merchant-track"><div class="merchant-fill" style="width:${Math.max(2, merchant.total_minor * 100 / max)}%"></div></div>`;
      row.addEventListener("click", () => setDrilldown("Merchant", merchant.display_merchant, merchant.transactions));
      list.appendChild(row);
    });
    card.appendChild(list);
    return card;
  }

  function renderIncomeVsSpend() {
    const card = make("article", "graph-card");
    card.appendChild(make("h2", "", "Income vs expenditure"));
    const data = [
      { label: "Income", value: state.data.income_vs_expenditure.income_minor },
      { label: "Expenses", value: state.data.income_vs_expenditure.expense_minor },
      { label: "Refunds", value: state.data.income_vs_expenditure.refund_minor },
    ];
    card.appendChild(barChart(data, "value", "label"));
    return card;
  }

  function lineChart(items, valueKey, onPoint) {
    const width = 760;
    const height = 260;
    const pad = 34;
    const max = Math.max(1, ...items.map((item) => Math.max(0, item[valueKey])));
    const step = items.length > 1 ? (width - pad * 2) / (items.length - 1) : 0;
    const points = items.map((item, index) => {
      const x = pad + index * step;
      const y = height - pad - (Math.max(0, item[valueKey]) / max) * (height - pad * 2);
      return { item, x, y };
    });
    const svg = svgRoot(width, height);
    svg.insertAdjacentHTML("beforeend", `<line class="graph-axis" x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}"></line>`);
    const path = points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ");
    svg.insertAdjacentHTML("beforeend", `<path class="graph-line" d="${path}"></path>`);
    points.forEach((point) => {
      const dot = svgEl("circle", { class: "graph-dot", cx: point.x, cy: point.y, r: 4, tabindex: 0 });
      dot.appendChild(svgTitle(`${point.item.date}: ${money(point.item[valueKey])}`));
      dot.addEventListener("click", () => onPoint?.(point.item));
      svg.appendChild(dot);
    });
    return svg;
  }

  function barChart(items, valueKey, labelKey, onBar) {
    const width = 520;
    const height = Math.max(180, items.length * 34 + 40);
    const pad = 30;
    const labelWidth = 130;
    const max = Math.max(1, ...items.map((item) => Math.max(0, item[valueKey])));
    const svg = svgRoot(width, height);
    items.forEach((item, index) => {
      const y = pad + index * 34;
      const barWidth = Math.max(2, (Math.max(0, item[valueKey]) / max) * (width - labelWidth - pad * 2));
      const label = item[labelKey];
      svg.appendChild(svgText(12, y + 17, String(label), "graph-label"));
      const rect = svgEl("rect", { class: "graph-bar", x: labelWidth, y, width: barWidth, height: 20, rx: 6, tabindex: 0 });
      rect.appendChild(svgTitle(`${label}: ${money(item[valueKey])}`));
      rect.addEventListener("click", () => onBar?.(item));
      svg.appendChild(rect);
      svg.appendChild(svgText(labelWidth + barWidth + 8, y + 15, valueKey.includes("count") ? String(item[valueKey]) : money(item[valueKey]), "graph-label"));
    });
    return svg;
  }

  function svgRoot(width, height) {
    return svgEl("svg", { class: "graph-svg", viewBox: `0 0 ${width} ${height}`, role: "img" });
  }

  function svgEl(name, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, String(value)));
    return el;
  }

  function svgText(x, y, text, className) {
    const el = svgEl("text", { x, y, class: className });
    el.textContent = text;
    return el;
  }

  function svgTitle(text) {
    const title = svgEl("title", {});
    title.textContent = text;
    return title;
  }

  function transactionsForDate(dateKey) {
    return state.data.transactions.filter((row) => row.date === dateKey || row.date.startsWith(dateKey));
  }

  function setDrilldown(kind, label, transactions) {
    state.drilldown = { kind, label, transactions: transactions || [] };
    render();
  }

  function renderDrilldown() {
    const box = make("section", "graph-drilldown");
    const header = make("div", "graph-drilldown-header");
    header.appendChild(make("h2", "", `${state.drilldown.kind}: ${state.drilldown.label}`));
    const back = make("button", "button subtle", "Back to graphs");
    back.type = "button";
    back.addEventListener("click", () => { state.drilldown = null; render(); });
    header.appendChild(back);
    box.appendChild(header);
    if (!state.drilldown.transactions.length) {
      box.appendChild(make("div", "graph-empty", "No transactions for this selection."));
      return box;
    }
    const rows = state.drilldown.transactions.map((row) => `<tr><td>${esc(row.date)}</td><td>${esc(row.display_merchant)}</td><td>${esc(row.category)}</td><td>${esc(row.txn_type)}</td><td>${money(row.amount_minor)}</td></tr>`).join("");
    box.insertAdjacentHTML("beforeend", `<table><thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th>Type</th><th>Amount</th></tr></thead><tbody>${rows}</tbody></table>`);
    return box;
  }

  function mount(el) {
    state.root = el;
    if (!state.data && !state.loading) refresh();
    else render();
  }

  window.WDMMG_GraphAnalytics = { mount, refresh };
})();
