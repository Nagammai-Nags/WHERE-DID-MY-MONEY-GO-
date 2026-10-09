(function () {
  const base = "/api/v1";
  const mock = new URLSearchParams(window.location.search).get("mock") === "1";
  const fixtures = {
    "/analytics/summary": "/frontend/fixtures/summary.json",
    "/analytics/sankey": "/frontend/fixtures/sankey.json",
    "/transactions": "/frontend/fixtures/transactions.json",
    "/merchants/review-queue": "/frontend/fixtures/review_queue.json",
    "/imports": "/frontend/fixtures/import_result.json",
    "/imports/sample": "/frontend/fixtures/import_result.json"
  };
  const categoryItems = ["Food", "Transport", "Groceries", "Entertainment", "Shopping", "Bills", "Education", "Uncategorized"];

  function showError(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message || "Something went wrong. Please try again.";
    toast.classList.add("show");
    clearTimeout(showError.timer);
    showError.timer = setTimeout(() => toast.classList.remove("show"), 5000);
  }

  async function readFixture(path) {
    const file = fixtures[path];
    if (!file) {
      if (path === "/categories") return { items: categoryItems };
      if (path === "/healthz") return { status: "ok" };
      if (path === "/dev/reset") return { status: "ok" };
      return {};
    }
    const response = await fetch(file);
    if (!response.ok) throw new Error("Could not load demo fixture: " + path);
    return response.json();
  }

  async function request(method, path, body) {
    const cleanPath = path.split("?")[0];
    try {
      if (mock) {
        if (method === "GET") return await readFixture(cleanPath);
        if (cleanPath === "/imports" || cleanPath === "/imports/sample") return await readFixture("/imports/sample");
        if (cleanPath === "/merchants/resolve") {
          const queue = await readFixture("/merchants/review-queue");
          const item = queue.items.find((entry) => entry.group_key === body.group_key);
          return {
            group_key: body.group_key,
            display_merchant: body.display_name,
            category: body.category,
            transactions_updated: item ? item.txn_count : 0
          };
        }
        if (cleanPath === "/dev/reset") return { status: "ok" };
        return {};
      }

      const response = await fetch(base + path, {
        method,
        headers: body === undefined ? undefined : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body)
      });
      let payload;
      try { payload = await response.json(); } catch (_) { payload = {}; }
      if (!response.ok) {
        const message = payload && payload.error && payload.error.message
          ? payload.error.message
          : "Request failed (" + response.status + ")";
        showError(message);
        const error = new Error(message);
        error.payload = payload;
        throw error;
      }
      return payload;
    } catch (error) {
      if (!(error && error.payload)) showError(error.message);
      throw error;
    }
  }

  function formatINR(minor) {
    const safeMinor = Number.isFinite(Number(minor)) ? Number(minor) : 0;
    return new Intl.NumberFormat("en-IN", {
      style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2
    }).format(safeMinor / 100);
  }

  function todayLabel() {
    return new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long" }).format(new Date());
  }

  window.api = {
    get(path) { return request("GET", path); },
    post(path, body) { return request("POST", path, body); },
    put(path, body) { return request("PUT", path, body); },
    formatINR,
    todayLabel,
    isMock: mock,
    showError
  };
  window.formatINR = formatINR;
  window.todayLabel = todayLabel;
})();
