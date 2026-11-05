/* Fills in the live parts of the site from data/rates.json and data/reviews.json.
   Both files sit next to the pages; GitHub updates rates.json every weekday. */
(function () {
  "use strict";

  var ROOT = document.body.getAttribute("data-root") || ".";
  function path(p) { return ROOT === "." ? p : ROOT + "/" + p; }

  // What each rate is called on the site and what it means for an owner.
  var RATES = {
    fed:    { name: "Fed funds target", series: "DFEDTARU", drives: "Set by the Federal Reserve. Short-term borrowing costs move with it." },
    prime:  { name: "Prime rate", series: "DPRIME", drives: "Bank and construction loans are often priced at prime plus a margin." },
    sofr:   { name: "SOFR", series: "SOFR", drives: "Construction and bridge loans are often priced at SOFR plus a spread." },
    t5:     { name: "5-Year Treasury", series: "DGS5", drives: "Five-year fixed multifamily loans are usually priced off this rate." },
    t10:    { name: "10-Year Treasury", series: "DGS10", drives: "Ten-year loans and cap rates take their cue from it." },
    mort30: { name: "30-Year Mortgage", series: "MORTGAGE30US", drives: "The average 30-year fixed rate. It matters to buyers who will live in a 2-to-4-family house." }
  };

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmtDate(iso) {
    if (!iso) return "";
    var p = String(iso).slice(0, 10).split("-");
    return MONTHS[+p[1] - 1] + " " + (+p[2]) + ", " + p[0];
  }
  function pct(v) { return v == null ? "—" : Number(v).toFixed(2) + "%"; }
  function range(lo, hi) { return Number(lo).toFixed(2) + "–" + Number(hi).toFixed(2) + "%"; }
  function valueOf(key, r) {
    if (!r) return "—";
    return key === "fed" ? range(r.lower, r.upper) : pct(r.value);
  }

  // "▲ 0.06" for display, "Up 0.06 points" for screen readers
  function move(c, span) {
    if (c == null) return "";
    var flat = Math.abs(c) < 0.005;
    var shown = flat ? "No change" : (c > 0 ? "▲ " : "▼ ") + Math.abs(c).toFixed(2);
    var said = flat ? "No change" : (c > 0 ? "Up " : "Down ") + Math.abs(c).toFixed(2) + " points";
    return '<span><span class="muted">' + span + '</span><span aria-hidden="true">' + shown +
      '</span><span class="sr">' + said + " over one " + (span === "1 wk" ? "week" : "year") + "</span></span>";
  }
  function words(c) {
    if (c == null) return null;
    if (Math.abs(c) < 0.005) return "unchanged";
    return (c > 0 ? "up " : "down ") + Math.abs(c).toFixed(2) + " points";
  }

  function tile(key, r, detailed) {
    var d = RATES[key];
    var html = '<div class="rate-name">' + d.name + "</div>" +
      '<div class="rate-value">' + valueOf(key, r) + "</div>" +
      '<div class="rate-asof">' + (r ? (r.date ? "As of " + fmtDate(r.date) : "Current target") : "Fills in on the first update") + "</div>";
    if (detailed) {
      var moves = r ? move(r.change_1w, "1 wk") + move(r.change_1y, "1 yr") : "";
      if (moves) html += '<div class="rate-moves">' + moves + "</div>";
      html += '<p class="rate-drives">' + d.drives + "</p>";
      var src = (r && r.source) || "https://fred.stlouisfed.org/series/" + d.series;
      html += '<a class="rate-source" href="' + esc(src) + '" target="_blank" rel="noopener">FRED · ' + d.series + "</a>";
    }
    var el = document.createElement("article");
    el.className = "rate" + (r ? "" : " rate-pending");
    el.innerHTML = html;
    return el;
  }

  function renderTiles(rates) {
    document.querySelectorAll("[data-rates]").forEach(function (box) {
      var keys = box.getAttribute("data-rates").split(",");
      var detailed = box.hasAttribute("data-detailed");
      box.innerHTML = "";
      keys.forEach(function (k) { box.appendChild(tile(k, rates[k], detailed)); });
    });
  }

  function renderStamp(data) {
    document.querySelectorAll("[data-stamp]").forEach(function (el) {
      el.textContent = data.preview
        ? "Preview. The live site refreshes these every weekday."
        : "Updated " + fmtDate(data.updated) + " from FRED";
    });
    document.querySelectorAll("[data-preview-note]").forEach(function (el) {
      el.hidden = !data.preview;
    });
  }

  function renderRecap(rates) {
    var list = document.querySelector("[data-recap]");
    if (!list) return;
    var out = [];
    if (rates.fed) {
      var fy = words(rates.fed.change_1y);
      out.push("The Fed's target range is " + range(rates.fed.lower, rates.fed.upper) +
        (fy && fy !== "unchanged" ? ", " + fy + " from a year ago." : "."));
    }
    [["t10", "The 10-year Treasury"], ["t5", "The 5-year Treasury"], ["sofr", "SOFR"], ["mort30", "The average 30-year mortgage"]].forEach(function (pair) {
      var r = rates[pair[0]];
      if (!r || r.value == null) return;
      var w = words(r.change_1w), y = words(r.change_1y);
      var s = pair[1] + " is " + pct(r.value);
      if (w && y) s += ", " + w + " on the week and " + y + " from a year ago.";
      else if (w) s += ", " + w + " on the week.";
      else s += ".";
      out.push(s);
    });
    if (rates.mort30 && rates.t10) {
      out.push("The 30-year mortgage sits " + (rates.mort30.value - rates.t10.value).toFixed(2) + " points above the 10-year Treasury.");
    }
    list.innerHTML = out.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("");
  }

  // ---------- Chart: 10-year Treasury and SOFR since 2021 ----------
  var SVGNS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs, parent) {
    var el = document.createElementNS(SVGNS, tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  }

  function chartSeries(history) {
    return [
      { key: "t10", name: "10-Year Treasury", short: "10-yr" },
      { key: "sofr", name: "SOFR", short: "SOFR" }
    ].map(function (s) {
      s.pts = (history[s.key] || []).map(function (p) {
        return { d: p[0], t: Date.parse(p[0] + "T00:00:00Z"), v: p[1] };
      });
      return s;
    }).filter(function (s) { return s.pts.length > 1; });
  }

  function nearest(pts, t) {
    var lo = 0, hi = pts.length - 1;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (pts[mid].t < t) lo = mid; else hi = mid;
    }
    return Math.abs(pts[lo].t - t) <= Math.abs(pts[hi].t - t) ? lo : hi;
  }

  function drawChart(box, series) {
    var W = Math.max(300, Math.round(box.clientWidth));
    var narrow = W < 600;
    var H = narrow ? 260 : 340;
    var m = { top: 14, right: narrow ? 58 : 132, bottom: 30, left: 40 };
    var t0 = Math.min.apply(null, series.map(function (s) { return s.pts[0].t; }));
    var t1 = Math.max.apply(null, series.map(function (s) { return s.pts[s.pts.length - 1].t; }));
    var vmax = Math.max.apply(null, series.map(function (s) { return Math.max.apply(null, s.pts.map(function (p) { return p.v; })); }));
    var top = Math.max(1, Math.ceil(vmax));
    var step = top > 6 ? 2 : 1;
    function x(t) { return m.left + (t - t0) / (t1 - t0 || 1) * (W - m.left - m.right); }
    function y(v) { return m.top + (1 - v / top) * (H - m.top - m.bottom); }

    box.innerHTML = "";
    var root = svg("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, role: "img", tabindex: "0" }, box);
    var latest = series.map(function (s) { var p = s.pts[s.pts.length - 1]; return s.name + " " + pct(p.v); }).join(", ");
    root.setAttribute("aria-label", "Line chart of the 10-year Treasury and SOFR, weekly since 2021. Latest: " + latest + ". Use the left and right arrow keys to read past values.");

    for (var v = 0; v <= top; v += step) {
      svg("line", { x1: m.left, x2: W - m.right, y1: y(v), y2: y(v), "class": v === 0 ? "axis" : "grid" }, root);
      svg("text", { x: m.left - 8, y: y(v) + 4, "text-anchor": "end" }, root).textContent = v + "%";
    }
    var y0 = new Date(t0).getUTCFullYear(), y1 = new Date(t1).getUTCFullYear();
    for (var yr = y0; yr <= y1; yr++) {
      var tt = Date.UTC(yr, 0, 1);
      if (tt < t0 - 7 * 864e5 || tt > t1) continue;
      var xx = x(Math.max(tt, t0));
      svg("line", { x1: xx, x2: xx, y1: H - m.bottom, y2: H - m.bottom + 5, "class": "axis" }, root);
      if (!narrow || yr % 2 === 1) {
        svg("text", { x: xx, y: H - m.bottom + 20, "text-anchor": "middle" }, root).textContent = yr;
      }
    }

    // Lines, then end labels nudged apart so they never overlap
    var ends = [];
    series.forEach(function (s) {
      var d = s.pts.map(function (p, i) { return (i ? "L" : "M") + x(p.t).toFixed(1) + " " + y(p.v).toFixed(1); }).join("");
      svg("path", { d: d, "class": "line line-" + s.key }, root);
      var last = s.pts[s.pts.length - 1];
      ends.push({ s: s, y: y(last.v), v: last.v });
    });
    ends.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < ends.length; i++) {
      if (ends[i].y - ends[i - 1].y < 18) ends[i].y = ends[i - 1].y + 18;
    }
    ends.forEach(function (e) {
      var label = narrow ? pct(e.v) : e.s.short + " " + pct(e.v);
      svg("text", { x: W - m.right + 10, y: e.y + 4, "class": "end-" + e.s.key }, root).textContent = label;
    });

    // Hover / tap / keyboard readout
    var cross = svg("line", { y1: m.top, y2: H - m.bottom, "class": "cross", visibility: "hidden" }, root);
    var dots = series.map(function (s) { return svg("circle", { r: 5, "class": "dot-" + s.key, visibility: "hidden" }, root); });
    var hit = svg("rect", { x: m.left, y: m.top, width: W - m.left - m.right, height: H - m.top - m.bottom, "class": "hit" }, root);
    var tip = document.createElement("div");
    tip.className = "tip";
    tip.hidden = true;
    tip.setAttribute("aria-live", "polite");
    box.appendChild(tip);

    var base = series[0];
    var current = base.pts.length - 1;

    function show(idx) {
      current = Math.max(0, Math.min(base.pts.length - 1, idx));
      var t = base.pts[current].t;
      var cx = x(t);
      cross.setAttribute("x1", cx); cross.setAttribute("x2", cx); cross.setAttribute("visibility", "visible");
      var rows = ['<b>Week of ' + fmtDate(base.pts[current].d) + "</b>"];
      series.forEach(function (s, k) {
        var p = s.pts[nearest(s.pts, t)];
        dots[k].setAttribute("cx", x(p.t)); dots[k].setAttribute("cy", y(p.v)); dots[k].setAttribute("visibility", "visible");
        rows.push(s.name + ": <b>" + pct(p.v) + "</b>");
      });
      tip.innerHTML = rows.join("<br>");
      tip.hidden = false;
      var w = tip.offsetWidth;
      var left = Math.max(0, Math.min(W - w, cx - w / 2));
      tip.style.left = left + "px";
    }
    function hide() {
      cross.setAttribute("visibility", "hidden");
      dots.forEach(function (d) { d.setAttribute("visibility", "hidden"); });
      tip.hidden = true;
    }
    function fromEvent(ev) {
      var r = root.getBoundingClientRect();
      var px = (ev.clientX - r.left) * (W / r.width);
      var t = t0 + (px - m.left) / (W - m.left - m.right) * (t1 - t0);
      show(nearest(base.pts, t));
    }
    hit.addEventListener("pointermove", fromEvent);
    hit.addEventListener("pointerdown", fromEvent);
    hit.addEventListener("pointerleave", hide);
    root.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowLeft") { show(current - 1); ev.preventDefault(); }
      else if (ev.key === "ArrowRight") { show(current + 1); ev.preventDefault(); }
      else if (ev.key === "Home") { show(0); ev.preventDefault(); }
      else if (ev.key === "End") { show(base.pts.length - 1); ev.preventDefault(); }
      else if (ev.key === "Escape") { hide(); }
    });
    root.addEventListener("blur", hide);
  }

  function renderTable(series) {
    var body = document.querySelector("[data-chart-table]");
    if (!body) return;
    var rows = [];
    var years = {};
    series[0].pts.forEach(function (p) { var yr = p.d.slice(0, 4); if (!years[yr]) years[yr] = p; });
    Object.keys(years).sort().forEach(function (yr) {
      var t = years[yr].t;
      rows.push("<tr><td>Start of " + yr + "</td>" + series.map(function (s) {
        return "<td>" + pct(s.pts[nearest(s.pts, t)].v) + "</td>";
      }).join("") + "</tr>");
    });
    var lastT = series[0].pts[series[0].pts.length - 1].t;
    rows.push("<tr><td>Latest (" + fmtDate(series[0].pts[series[0].pts.length - 1].d) + ")</td>" + series.map(function (s) {
      return "<td>" + pct(s.pts[nearest(s.pts, lastT)].v) + "</td>";
    }).join("") + "</tr>");
    body.innerHTML = rows.join("");
  }

  function renderChart(history) {
    var box = document.querySelector("[data-chart]");
    if (!box) return;
    var series = chartSeries(history || {});
    var details = document.querySelector("[data-chart-details]");
    if (!series.length) {
      box.innerHTML = '<p class="chart-empty">The chart since 2021 fills in on the first automatic update.</p>';
      if (details) details.hidden = true;
      return;
    }
    if (details) details.hidden = false;
    renderTable(series);
    var lastW = 0;
    function redraw() {
      var w = Math.round(box.clientWidth);
      if (w && w !== lastW) { lastW = w; drawChart(box, series); }
    }
    redraw();
    if ("ResizeObserver" in window) {
      var pending = false;
      new ResizeObserver(function () {
        if (pending) return;
        pending = true;
        requestAnimationFrame(function () { pending = false; redraw(); });
      }).observe(box);
    }
  }

  // ---------- Monthly reviews ----------
  function renderReviews(list) {
    var latest = document.querySelector("[data-review-latest]");
    if (latest && list.length) {
      var r = list[0];
      latest.innerHTML = '<a class="review-card" href="' + esc(path(r.url)) + '">' +
        '<span class="review-meta">' + esc(r.label) + "</span>" +
        '<span class="h-card">' + esc(r.title) + "</span>" +
        '<p class="review-sum">' + esc(r.summary) + "</p>" +
        '<span class="read">Read the review →</span></a>';
    }
    var all = document.querySelector("[data-review-list]");
    if (all) {
      all.innerHTML = list.map(function (r) {
        return '<a class="review-row" href="' + esc(path(r.url)) + '">' +
          '<span class="review-meta">' + esc(r.label) + "</span>" +
          '<span class="stack"><span class="h-card">' + esc(r.title) + "</span>" +
          '<span class="review-sum">' + esc(r.summary) + "</span></span></a>";
      }).join("");
    }
  }

  function load(name) {
    return fetch(path("data/" + name), { cache: "no-cache" }).then(function (res) {
      if (!res.ok) throw new Error(name + " " + res.status);
      return res.json();
    });
  }

  function failRates() {
    document.querySelectorAll("[data-rates]").forEach(function (box) {
      box.innerHTML = '<p class="rate" style="grid-column: 1 / -1; margin: 0">The rates didn\'t load. Refresh the page to try again.</p>';
    });
    document.querySelectorAll("[data-stamp]").forEach(function (el) { el.textContent = "Rates unavailable right now"; });
  }

  if (document.querySelector("[data-rates], [data-recap], [data-chart], [data-stamp]")) {
    load("rates.json").then(function (data) {
      var rates = data.rates || {};
      renderTiles(rates);
      renderStamp(data);
      renderRecap(rates);
      renderChart(data.history);
    }).catch(failRates);
  }
  if (document.querySelector("[data-review-latest], [data-review-list]")) {
    load("reviews.json").then(renderReviews).catch(function () {});
  }
})();
