(function () {
  const NS = "http://www.w3.org/2000/svg";
  const BRANCH_PALETTE = [
    "#3B82F6", "#34D399", "#A3E635", "#FBBF24", "#FB923C",
    "#FB7185", "#F472B6", "#A78BFA", "#C084FC", "#22D3EE"
  ];
  const SOURCE_COLOR = "#22D3EE";
  const NEUTRAL_COLOR = "#94A3B8";

  function endpointId(endpoint) {
    return typeof endpoint === "object" ? endpoint.id : endpoint;
  }

  function branchColors(payload) {
    const nodes = payload.nodes || [];
    const links = payload.links || [];
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const roots = new Set(nodes.filter((node) => node.kind && node.kind.startsWith("ROOT_")).map((node) => node.id));
    const orderedCategories = [];
    links.forEach((link) => {
      const source = endpointId(link.source);
      const target = endpointId(link.target);
      if (roots.has(source) && byId.get(target)?.kind === "CATEGORY" && !orderedCategories.includes(target)) orderedCategories.push(target);
    });
    nodes.forEach((node) => {
      if (node.kind === "CATEGORY" && !orderedCategories.includes(node.id)) orderedCategories.push(node.id);
    });

    const colors = new Map();
    orderedCategories.forEach((id, index) => colors.set(id, BRANCH_PALETTE[index % BRANCH_PALETTE.length]));
    let nextColor = orderedCategories.length;
    nodes.filter((node) => node.kind === "UNSPENT").forEach((node) => {
      colors.set(node.id, BRANCH_PALETTE[nextColor % BRANCH_PALETTE.length]);
      nextColor += 1;
    });

    // Pass category branch colors through the graph's existing links to merchant and small-payment leaves.
    for (let pass = 0; pass < links.length; pass += 1) {
      links.forEach((link) => {
        const source = endpointId(link.source);
        const target = endpointId(link.target);
        if (!colors.has(target) && colors.has(source)) colors.set(target, colors.get(source));
      });
    }
    return colors;
  }
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

  function el(name, attrs) {
    const node = document.createElementNS(NS, name);
    Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function nodeColor(node, colors) {
    if (node.kind === "ROOT_INCOME" || node.kind === "ROOT_SPEND") return SOURCE_COLOR;
    return colors.get(node.id) || NEUTRAL_COLOR;
  }

  function linkColor(link, colors) {
    const sourceId = endpointId(link.source);
    const targetId = endpointId(link.target);
    return colors.get(sourceId) || colors.get(targetId) || SOURCE_COLOR;
  }

  function renderLinkTable(host, payload) {
    const wrap = document.createElement("div");
    wrap.className = "flow-table-wrap";
    const table = document.createElement("table");
    table.className = "flow-table";
    table.innerHTML = "<thead><tr><th>From</th><th>To</th><th>Amount</th></tr></thead>";
    const body = document.createElement("tbody");
    const names = new Map((payload.nodes || []).map((node) => [node.id, node.name]));
    (payload.links || []).forEach((link) => {
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;
      const row = document.createElement("tr");
      [names.get(sourceId) || sourceId, names.get(targetId) || targetId, window.formatINR(link.value_minor)].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    table.appendChild(body);
    wrap.appendChild(table);
    host.appendChild(wrap);
  }

  function renderFallback(svg, payload, width, height) {
    const margin = { top: 28, right: 150, bottom: 20, left: 150 };
    const plotWidth = Math.max(260, width - margin.left - margin.right);
    const plotHeight = height - margin.top - margin.bottom;
    const nodes = (payload.nodes || []).map((node) => ({ ...node }));
    const links = (payload.links || []).map((link) => ({ ...link }));
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const colors = branchColors(payload);
    const incoming = new Map();
    const outgoing = new Map();
    links.forEach((link) => {
      const sid = typeof link.source === "object" ? link.source.id : link.source;
      const tid = typeof link.target === "object" ? link.target.id : link.target;
      const sourceLinks = outgoing.get(sid) || [];
      const targetLinks = incoming.get(tid) || [];
      sourceLinks.push(link);
      targetLinks.push(link);
      outgoing.set(sid, sourceLinks);
      incoming.set(tid, targetLinks);
    });
    const columns = [[], [], []];
    nodes.forEach((node) => {
      const column = node.kind && node.kind.startsWith("ROOT_") ? 0 : node.kind === "CATEGORY" ? 1 : 2;
      node.column = column;
      columns[column].push(node);
    });
    const gap = 15;
    const nodeWidth = 16;
    const scaleCandidates = links.map((link) => Number(link.value_minor)).filter((value) => value > 0);
    const maxLink = Math.max(1, ...scaleCandidates);
    const scale = Math.min(0.9, (plotHeight - gap * Math.max(...columns.map((column) => column.length), 1)) / maxLink);
    const nodeHeight = (node) => {
      const adjacent = [...(incoming.get(node.id) || []), ...(outgoing.get(node.id) || [])];
      let size = 0;
      adjacent.forEach((link) => { size = Math.max(size, Number(link.value_minor) || 0); });
      return Math.max(7, size * scale);
    };
    columns.forEach((column, index) => {
      const x = margin.left + index * (plotWidth / 2);
      const heights = column.map(nodeHeight);
      let total = gap * Math.max(0, column.length - 1);
      heights.forEach((item) => { total = total + item; });
      let y = margin.top + Math.max(0, (plotHeight - total) / 2);
      column.forEach((node, nodeIndex) => {
        node.x0 = x;
        node.x1 = x + nodeWidth;
        node.y0 = y;
        node.y1 = y + heights[nodeIndex];
        node._outOffset = 0;
        node._inOffset = 0;
        y = node.y1 + gap;
      });
    });
    links.forEach((link) => {
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;
      const source = byId.get(sourceId);
      const target = byId.get(targetId);
      if (!source || !target) return;
      const thickness = Math.max(1, Number(link.value_minor) * scale);
      const sy = source.y0 + source._outOffset + thickness / 2;
      const ty = target.y0 + target._inOffset + thickness / 2;
      source._outOffset = source._outOffset + thickness;
      target._inOffset = target._inOffset + thickness;
      const sx = source.x1;
      const tx = target.x0;
      const bend = (tx - sx) * 0.48;
      const path = el("path", { d: `M${sx},${sy} C${sx + bend},${sy} ${tx - bend},${ty} ${tx},${ty}`, fill: "none", stroke: linkColor(link, colors), "stroke-opacity": "0.58", "stroke-width": thickness, class: "flow-link", tabindex: "0", role: "img", "aria-label": `${source.name} to ${target.name}: ${window.formatINR(link.value_minor)}` });
      const title = el("title");
      title.textContent = `${source.name} → ${target.name}: ${window.formatINR(link.value_minor)}`;
      path.appendChild(title);
      svg.appendChild(path);
    });
    nodes.forEach((node) => {
      const nodeValue = Math.max(...[...(incoming.get(node.id) || []), ...(outgoing.get(node.id) || [])].map((link) => Number(link.value_minor) || 0), 0);
      const rect = el("rect", { x: node.x0, y: node.y0, width: nodeWidth, height: Math.max(7, node.y1 - node.y0), rx: 5, fill: nodeColor(node, colors), class: "flow-node-shape" });
      const group = el("g", { class: "flow-node", tabindex: "0", role: "img", "aria-label": `${node.name}: ${window.formatINR(nodeValue)}` });
      group.appendChild(rect);
      const label = el("text", { x: node.column === 2 ? node.x1 + 8 : node.x0 - 8, y: (node.y0 + node.y1) / 2 + 4, "text-anchor": node.column === 2 ? "start" : "end", class: "flow-label" });
      label.textContent = node.name;
      const title = el("title");
      title.textContent = `${node.name}: ${window.formatINR(nodeValue)}${node.kind === "SMALL" ? ` · ${window.WDMMGCharts.smallCount} payments` : ""}`;
      group.appendChild(title);
      svg.appendChild(group);
      svg.appendChild(label);
    });
  }

  function renderD3(svg, payload, width, height) {
    const graph = {
      nodes: payload.nodes.map((node) => ({ ...node })),
      links: payload.links.map((link) => ({ source: link.source, target: link.target, value: link.value_minor, value_minor: link.value_minor }))
    };
    const colors = branchColors(payload);
    const layout = window.d3.sankey().nodeId((node) => node.id).nodeWidth(16).nodePadding(13).extent([[28, 24], [width - 150, height - 20]]);
    layout(graph);
    const path = window.d3.sankeyLinkHorizontal();
    graph.links.forEach((link) => {
      const line = el("path", { d: path(link), fill: "none", stroke: linkColor(link, colors), "stroke-opacity": "0.58", "stroke-width": Math.max(1, link.width), class: "flow-link", tabindex: "0", role: "img", "aria-label": `${link.source.name} to ${link.target.name}: ${window.formatINR(link.value_minor)}` });
      const title = el("title");
      title.textContent = `${link.source.name} → ${link.target.name}: ${window.formatINR(link.value_minor)}`;
      line.appendChild(title);
      svg.appendChild(line);
    });
    graph.nodes.forEach((node) => {
      const nodeLinks = [...node.sourceLinks, ...node.targetLinks];
      const amount = Math.max(...nodeLinks.map((link) => Number(link.value_minor) || 0), 0);
      const rect = el("rect", { x: node.x0, y: node.y0, width: node.x1 - node.x0, height: Math.max(5, node.y1 - node.y0), rx: 5, fill: nodeColor(node, colors), class: "flow-node-shape" });
      const group = el("g", { class: "flow-node", tabindex: "0", role: "img", "aria-label": `${node.name}: ${window.formatINR(amount)}` });
      group.appendChild(rect);
      const label = el("text", { x: node.x0 < width / 2 ? node.x1 + 7 : node.x0 - 7, y: (node.y0 + node.y1) / 2 + 4, "text-anchor": node.x0 < width / 2 ? "start" : "end", class: "flow-label" });
      label.textContent = node.name;
      const title = el("title");
      title.textContent = `${node.name}: ${window.formatINR(amount)}${node.kind === "SMALL" ? ` · ${window.WDMMGCharts.smallCount} payments` : ""}`;
      group.appendChild(title);
      svg.appendChild(group);
      svg.appendChild(label);
    });
  }

  function renderSankey(host, payload) {
    host.replaceChildren();
    if (!payload || !Array.isArray(payload.nodes) || !Array.isArray(payload.links)) {
      host.innerHTML = '<div class="empty-note">Flow data is not available yet.</div>';
      return;
    }
    const banner = document.getElementById("sankey-warning");
    banner.replaceChildren();
    if (payload.meta && payload.meta.overspent_minor > 0) {
      const note = document.createElement("div");
      note.className = "overspent-note";
      note.textContent = `Spending exceeded recorded income by ${window.formatINR(payload.meta.overspent_minor)}`;
      banner.appendChild(note);
    }
    const fallback = !(window.d3 && typeof window.d3.sankey === "function" && typeof window.d3.sankeyLinkHorizontal === "function");
    const hasUnknown = payload.nodes.some((node) => node.kind === "CATEGORY" && node.name === "Uncategorized" || node.kind === "MERCHANT" && (/^Unknown:/i.test(node.name || "") || String(node.id).includes(":Uncategorized:")));
    if (hasUnknown) {
      const review = document.createElement("div");
      review.className = "flow-review-callout";
      review.innerHTML = '<span aria-hidden="true">●</span><span>Unknown and uncategorized activity is easy to spot here.</span><a href="#review">Review merchants →</a>';
      review.querySelector("a").addEventListener("click", (event) => {
        event.preventDefault();
        const tab = document.querySelector('.tab[data-tab="review"]');
        if (tab) tab.click();
      });
      host.appendChild(review);
    }
    const label = document.createElement("div");
    label.className = "flow-mode";
    label.textContent = fallback ? "Fallback flow view" : "Money flow · hover a path for its amount";
    host.appendChild(label);
    const wrap = document.createElement("div");
    wrap.className = "flow-scroll";
    const width = Math.max(820, wrap.clientWidth || host.clientWidth || 820);
    const height = Math.max(390, Math.min(620, payload.nodes.length * 28));
    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height, role: "img", "aria-label": "Money flow diagram" });
    try {
      if (fallback) renderFallback(svg, payload, width, height);
      else renderD3(svg, payload, width, height);
      wrap.appendChild(svg);
      host.appendChild(wrap);
    } catch (error) {
      host.replaceChildren();
      const fallbackLabel = document.createElement("div");
      fallbackLabel.className = "flow-mode";
      fallbackLabel.textContent = "Fallback flow view";
      host.appendChild(fallbackLabel);
      const tableOnly = document.createElement("p");
      tableOnly.className = "muted small";
      tableOnly.textContent = "The flow diagram could not be laid out. The table below shows the API links and values.";
      host.appendChild(tableOnly);
    }
    const toggle = document.createElement("button");
    toggle.className = "button subtle table-toggle";
    toggle.type = "button";
    toggle.textContent = "Table view";
    const tableSlot = document.createElement("div");
    tableSlot.hidden = true;
    toggle.addEventListener("click", () => {
      tableSlot.hidden = !tableSlot.hidden;
      toggle.textContent = tableSlot.hidden ? "Table view" : "Hide table";
      if (!tableSlot.dataset.loaded) {
        renderLinkTable(tableSlot, payload);
        tableSlot.dataset.loaded = "true";
      }
    });
    host.append(toggle, tableSlot);
  }

  window.WDMMGCharts = {
    smallCount: 0,
    renderSankey,
    async refresh() {
      const host = document.getElementById("sankey-chart");
      if (!host) return;
      try {
        const [payload, summary] = await Promise.all([window.api.get("/analytics/sankey"), window.api.get("/analytics/summary")]);
        this.smallCount = summary.small_payments ? summary.small_payments.count : 0;
        renderSankey(host, payload);
      } catch (_) {
        host.innerHTML = '<div class="error-state">Money flow could not be loaded. Try refreshing.</div>';
      }
    }
  };
})();
