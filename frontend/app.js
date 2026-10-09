(function () {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  const amount = (minor) => window.formatINR(minor);
  let summaryCache = null;
  let transactionRows = [];
  let reviewItems = [];
  let categoryItems = [];
  let toastTimer;

  function announce(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3800);
  }

  function periodLabel(period) {
    if (!period || !period.from) return "Your spending at a glance";
    const date = new Date(`${period.from}T12:00:00`);
    return `Activity from ${new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric" }).format(date)}`;
  }

  function setBusy(button, busy, label) {
    if (!button) return;
    if (busy) {
      button.dataset.originalText = button.textContent;
      button.textContent = label || "Working…";
      button.disabled = true;
    } else {
      button.textContent = button.dataset.originalText || button.textContent;
      button.disabled = false;
    }
  }

  function goTo(tabName) {
    const tab = $(`.tab[data-tab="${tabName}"]`);
    if (tab) tab.click();
  }

  function renderSummary(payload) {
    summaryCache = payload;
    const host = $("#dashboard-content");
    $("#period-label").textContent = periodLabel(payload.period);
    const small = payload.small_payments || {};
    const empty = payload.net_spend_minor === 0;
    $("#unknown-banner").hidden = !(payload.unknown_merchant_count > 0);
    if (payload.unknown_merchant_count > 0) {
      $("#unknown-banner").innerHTML = `<span class="unknown-dot"></span><strong>${payload.unknown_merchant_count} unknown merchant${payload.unknown_merchant_count === 1 ? "" : "s"}</strong><span>need a name</span><a href="#review" data-go="review">Review →</a>`;
      $("#unknown-banner a").addEventListener("click", (event) => { event.preventDefault(); goTo("review"); });
    }
    $("#review-count").textContent = payload.unknown_merchant_count > 0 ? String(payload.unknown_merchant_count) : "";
    if (empty) {
      host.innerHTML = `<div class="empty-state"><span class="empty-illustration">↘</span><p class="eyebrow">A FRESH START</p><h2>Your story starts with a transaction</h2><p>Import a statement or load the sample data to see your spending take shape.</p><button class="button primary" id="empty-import">Load sample data</button></div>`;
      $("#empty-import").addEventListener("click", () => sampleImport($("#empty-import")));
      return;
    }
    const categories = Array.isArray(payload.by_category) ? payload.by_category : [];
    const merchants = Array.isArray(payload.top_merchants) ? payload.top_merchants : [];
    host.innerHTML = `
      <div class="kpi-grid">
        <article class="kpi-card primary-kpi"><span class="kpi-label">TOTAL SPENDING</span><strong>${amount(payload.net_spend_minor)}</strong><span class="kpi-note">Computed from your activity</span></article>
        <article class="kpi-card"><span class="kpi-label">RECORDED INCOME</span><strong>${amount(payload.income_minor)}</strong><span class="kpi-note">Credits recorded in this period</span></article>
        <article class="kpi-card"><span class="kpi-label">SMALL PAYMENTS</span><strong>${small.count ?? 0}<span class="kpi-unit"> payments</span></strong><span class="kpi-note">${amount(small.total_minor)} in total</span></article>
        <article class="kpi-card"><span class="kpi-label">UNCATEGORIZED</span><strong>${amount(payload.uncategorized_minor)}</strong><span class="kpi-note">Payees to take another look at</span></article>
      </div>
      <div class="dashboard-grid">
        <article class="card category-card"><div class="card-heading"><div><p class="eyebrow">SPENDING BREAKDOWN</p><h2>By category</h2></div></div>
          ${categories.length ? `<div class="category-list">${categories.map((item) => `<div class="category-row"><div class="category-label"><span>${escapeHTML(item.category)}</span><strong>${amount(item.total_minor)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${Math.max(0, Math.min(100, item.pct_bp / 100))}%"></div></div><small>${(item.pct_bp / 100).toFixed(1)}% of spending</small></div>`).join("")}</div>` : `<div class="empty-note">No category activity for this period.</div>`}
        </article>
        <article class="card merchant-card"><div class="card-heading"><div><p class="eyebrow">RECOGNIZED PAYEES</p><h2>Top merchants</h2></div></div>
          ${merchants.length ? `<ol class="merchant-list">${merchants.map((item, index) => `<li><span class="merchant-rank">${String(index + 1).padStart(2, "0")}</span><span class="merchant-name">${escapeHTML(item.display_merchant)}<small>${item.count} transaction${item.count === 1 ? "" : "s"}</small></span><strong>${amount(item.total_minor)}</strong></li>`).join("")}</ol>` : `<div class="empty-note">Merchant activity will appear here.</div>`}
        </article>
      </div>`;
  }

  async function loadDashboard() {
    const host = $("#dashboard-content");
    if (!summaryCache) host.innerHTML = '<div class="loading">Loading your summary…</div>';
    try {
      const payload = await window.api.get("/analytics/summary");
      renderSummary(payload);
      await window.WDMMGCharts.refresh();
      const health = await window.api.get("/healthz").catch(() => null);
      if (health && health.db === "memory") {
        let banner = $("#memory-banner");
        if (!banner) {
          banner = document.createElement("div");
          banner.id = "memory-banner";
          banner.className = "memory-banner";
          banner.textContent = "Temporary database — data resets on restart";
          $(".dashboard-heading").after(banner);
        }
      }
    } catch (_) {
      if (!summaryCache) host.innerHTML = '<div class="error-state">Your summary could not be loaded. Check the connection and try again.</div>';
    }
  }

  function sourceBadge(source) {
    const labels = { USER: ["Confirmed", "badge-confirmed"], DICTIONARY: ["Auto", "badge-auto"], UNKNOWN: ["Unknown", "badge-unknown"] };
    const pair = labels[source] || [source || "Unknown", "badge-neutral"];
    return `<span class="badge ${pair[1]}">${escapeHTML(pair[0])}</span>`;
  }

  function typeBadge(type) {
    const classMap = { EXPENSE: "type-expense", REFUND: "type-refund", INCOME: "type-income", TRANSFER_OUT: "type-transfer", TRANSFER_IN: "type-transfer", IGNORED: "type-ignored" };
    const labels = { TRANSFER_OUT: "Transfer out", TRANSFER_IN: "Transfer in" };
    return `<span class="type-badge ${classMap[type] || "type-ignored"}">${escapeHTML(labels[type] || type || "Activity")}</span>`;
  }

  function renderTransactions(rows) {
    const host = $("#transactions-list");
    if (!rows.length) {
      host.innerHTML = '<div class="empty-state compact"><span class="empty-illustration">⌕</span><h2>No transactions to show</h2><p>Import some activity to see it here.</p><a href="#import" class="button subtle" data-go="import">Go to Import</a></div>';
      return;
    }
    host.innerHTML = `<div class="table-scroll"><table class="transaction-table"><thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th>Type</th><th>Amount</th><th>Source</th></tr></thead><tbody>${rows.map((row) => `<tr class="${row.txn_type === "INCOME" ? "row-income" : row.txn_type && row.txn_type.startsWith("TRANSFER") ? "row-transfer" : ""}"><td class="date-cell">${escapeHTML(row.date)}</td><td><strong class="txn-merchant">${escapeHTML(row.display_merchant)}</strong><span class="raw-counterparty" title="Original counterparty">${escapeHTML(row.counterparty_raw)}</span></td><td>${escapeHTML(row.category)}</td><td>${typeBadge(row.txn_type)}</td><td class="money-cell">${amount(row.amount_minor)}</td><td>${sourceBadge(row.merchant_source)}</td></tr>`).join("")}</tbody></table></div>`;
  }

  function filterTransactions() {
    const query = $("#txn-search").value.trim().toLocaleLowerCase();
    const type = $("#txn-type").value;
    const visible = transactionRows.filter((row) => (!type || row.txn_type === type) && (!query || `${row.display_merchant} ${row.counterparty_raw} ${row.category}`.toLocaleLowerCase().includes(query)));
    renderTransactions(visible);
  }

  async function loadTransactions() {
    const host = $("#transactions-list");
    host.innerHTML = '<div class="loading">Loading transactions…</div>';
    try {
      const payload = await window.api.get("/transactions");
      transactionRows = Array.isArray(payload.items) ? payload.items : [];
      filterTransactions();
    } catch (_) {
      host.innerHTML = '<div class="error-state">Transactions could not be loaded. Try refreshing.</div>';
    }
  }

  function renderReview() {
    const host = $("#review-list");
    $("#review-count").textContent = reviewItems.length ? String(reviewItems.length) : "";
    if (!reviewItems.length) {
      host.innerHTML = '<div class="empty-state compact"><span class="empty-illustration">✓</span><h2>All caught up</h2><p>New unfamiliar merchants will appear here.</p></div>';
      return;
    }
    host.innerHTML = reviewItems.map((item, index) => `<article class="card review-card" data-review-index="${index}"><div class="review-summary"><span class="review-avatar">${escapeHTML((item.identifier_value || "?").slice(0, 1).toUpperCase())}</span><div><p class="eyebrow">UNRECOGNIZED PAYEE</p><h2>${escapeHTML(item.identifier_value)}</h2><div class="raw-examples">${(item.raw_examples || []).map((value) => `<code>${escapeHTML(value)}</code>`).join("")}</div></div></div><div class="review-stats"><span><strong>${item.txn_count}</strong> transactions</span><span><strong>${amount(item.total_minor)}</strong> total</span></div><form class="resolve-form" data-group-key="${escapeHTML(item.group_key)}"><label><span>Display name</span><input name="display_name" maxlength="50" required placeholder="e.g. Tea stall"></label><label><span>Category</span><select name="category" required>${categoryItems.map((value) => `<option value="${escapeHTML(value)}" ${value === "Uncategorized" ? "selected" : ""}>${escapeHTML(value)}</option>`).join("")}</select></label><button class="button primary" type="submit">Save merchant name</button></form></article>`).join("");
    $$(".resolve-form", host).forEach((form) => form.addEventListener("submit", resolveMerchant));
  }

  async function loadReview() {
    const host = $("#review-list");
    host.innerHTML = '<div class="loading">Loading merchants…</div>';
    try {
      const [queue, categories] = await Promise.all([window.api.get("/merchants/review-queue"), window.api.get("/categories")]);
      reviewItems = Array.isArray(queue.items) ? queue.items : [];
      categoryItems = Array.isArray(categories.items) ? categories.items : [];
      renderReview();
    } catch (_) {
      host.innerHTML = '<div class="error-state">The review queue could not be loaded. Try refreshing.</div>';
    }
  }

  async function resolveMerchant(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $("button[type=submit]", form);
    const body = { group_key: form.dataset.groupKey, display_name: form.elements.display_name.value.trim(), category: form.elements.category.value };
    if (!body.display_name) return;
    setBusy(button, true, "Saving…");
    try {
      const result = await window.api.post("/merchants/resolve", body);
      announce(`${result.transactions_updated} transactions updated`);
      await Promise.all([loadReview(), loadDashboard(), loadTransactions()]);
      if (window.WDMMG_BudgetPanel && typeof window.WDMMG_BudgetPanel.refresh === "function") await window.WDMMG_BudgetPanel.refresh();
    } catch (_) {
      setBusy(button, false);
    }
  }

  function renderImportResult(result) {
    const rejectedRows = Array.isArray(result.rejected_rows) ? result.rejected_rows : [];
    $("#import-result").innerHTML = `<article class="card import-result"><div class="result-heading"><span class="success-mark">✓</span><div><p class="eyebrow">IMPORT COMPLETE</p><h2>${escapeHTML(result.source_type || "Import")} results</h2></div></div><div class="result-grid"><div><strong>${result.imported}</strong><span>Imported</span></div><div><strong>${result.duplicates}</strong><span>Duplicates</span></div><div><strong>${result.rejected}</strong><span>Rejected</span></div><div><strong>${result.ignored}</strong><span>Ignored</span></div><div><strong>${result.unknown_merchants}</strong><span>Unknown merchants</span></div></div>${rejectedRows.length ? `<div class="rejected-list"><h3>Rows to review</h3><ul>${rejectedRows.map((row) => `<li>Row ${escapeHTML(row.row)}: ${escapeHTML(row.reason)}</li>`).join("")}</ul></div>` : ""}</article>`;
  }

  async function doImport(button, promise) {
    setBusy(button, true);
    try {
      const result = await promise;
      renderImportResult(result);
      announce("Import finished");
      await Promise.all([loadDashboard(), loadTransactions(), loadReview()]);
    } catch (_) {
      $("#import-result").innerHTML = '<div class="error-state">Import did not finish. Review the message and try again.</div>';
    } finally { setBusy(button, false); }
  }

  function sampleImport(button) {
    return doImport(button, window.api.post("/imports/sample"));
  }

  function bindTabs() {
    $$(".tab").forEach((tab) => tab.addEventListener("click", () => {
      const name = tab.dataset.tab;
      $$(".tab").forEach((item) => { item.classList.toggle("active", item === tab); item.setAttribute("aria-selected", String(item === tab)); });
      $$(".page").forEach((page) => { page.hidden = page.dataset.page !== name; page.classList.toggle("active", page.dataset.page === name); });
      history.replaceState(null, "", `#${name}`);
      if (name === "dashboard") loadDashboard();
      if (name === "transactions") loadTransactions();
      if (name === "review") loadReview();
      if (name === "assistant" && window.WDMMG_AssistantPanel?.mount) window.WDMMG_AssistantPanel.mount($("#assistant-panel"));
    }));
    $$('[data-go]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); goTo(link.dataset.go); }));
    const hash = window.location.hash.slice(1);
    if (hash && $(`.tab[data-tab="${hash}"]`)) goTo(hash);
    else goTo("dashboard");
  }

  function bindActions() {
    $("#paste-import").addEventListener("click", (event) => {
      const button = event.currentTarget;
      const text = $("#paste-text").value;
      doImport(button, window.api.post("/imports", { source_type: "PASTE", text }));
    });
    $("#sample-import").addEventListener("click", (event) => sampleImport(event.currentTarget));
    $("#csv-file").addEventListener("change", (event) => {
      const file = event.currentTarget.files && event.currentTarget.files[0];
      if (!file) return;
      $("#file-name").textContent = file.name;
      const reader = new FileReader();
      reader.onerror = () => window.api.showError("Could not read this file. Try choosing it again.");
      reader.onload = () => doImport($("#csv-file"), window.api.post("/imports", { source_type: "CSV", text: String(reader.result || "") }));
      reader.readAsText(file);
    });
    $("#reset-demo").addEventListener("click", async (event) => {
      if (!window.confirm("Reset all demo transactions, merchant names, and budget?")) return;
      const button = event.currentTarget;
      setBusy(button, true, "Resetting…");
      try {
        await window.api.post("/dev/reset");
        $("#import-result").replaceChildren();
        summaryCache = null;
        await Promise.all([loadDashboard(), loadTransactions(), loadReview()]);
        announce("Demo data reset");
      } catch (_) { /* The API client displays the error. */ }
      finally { setBusy(button, false); }
    });
    $("#txn-search").addEventListener("input", filterTransactions);
    $("#txn-type").addEventListener("change", filterTransactions);
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("#today-label").textContent = window.todayLabel();
    bindTabs();
    bindActions();
    if (!$('.tab[data-tab="dashboard"]').classList.contains("active")) loadDashboard();
    if (window.WDMMG_BudgetPanel?.mount) window.WDMMG_BudgetPanel.mount($("#budget-panel"));
    if (!window.WDMMG_BudgetPanel) $("#budget-panel").innerHTML = '<div class="panel-unavailable">Budget panel will appear here.</div>';
    if (!window.WDMMG_AssistantPanel) $("#assistant-panel").innerHTML = '<div class="panel-unavailable">Assistant panel will appear here.</div>';
  });
})();
