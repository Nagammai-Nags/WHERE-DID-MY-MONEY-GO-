(function () {
  const base = "/api/v1";
  function showError(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message || "Something went wrong. Please try again.";
    toast.classList.add("show");
    clearTimeout(showError.timer);
    showError.timer = setTimeout(() => toast.classList.remove("show"), 5000);
  }

  async function request(method, path, body) {
    try {
      const response = await fetch(base + path, {
        method,
        cache: "no-store",
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
    showError
  };
  window.formatINR = formatINR;
  window.todayLabel = todayLabel;
})();
