(async function () {
  const res = await fetch("data/history.json", { cache: "no-cache" });
  const data = await res.json();
  const minChart = data.min_measured_to_chart ?? 40;
  const SHORT = { "aa-hle": "HLE", "aa-scicode": "SciCode", "arc-agi-2": "ARC-AGI-2", "aa-terminal-bench": "T-Bench", "webdev-arena": "WebDev", "design-arena-website": "Design Arena" };
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const day = iso => new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).getTime();
  const fmtDate = iso => iso ? new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "";
  const fmtMonth = t => new Date(t).toLocaleDateString(undefined, { year: "2-digit", month: "short" });
  const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  const updated = `Last updated ${fmtDate(data.generated_at)}.`;
  document.getElementById("stamp").textContent = updated;
  document.getElementById("foot-stamp").textContent = updated;
  document.getElementById("min-chart").textContent = minChart;

  const charted = f => f.generations.filter(g => g.coverage >= minChart);
  // One shared time axis, so lines are comparable across families.
  const allTimes = data.families.flatMap(f => charted(f).map(g => day(g.released)));
  const t0 = Math.min(...allTimes), t1 = Math.max(day(data.generated_at.slice(0, 10)), ...allTimes);

  document.getElementById("jump").innerHTML = data.families
    .map(f => `<li><a href="#${slug(f.name)}">${esc(f.name)}</a></li>`).join("");

  // Only true successors count: both generations adjacent in the family and both well measured.
  const jumps = data.families.flatMap(f => f.generations.slice(1).map((g, i) => [f.generations[i], g]))
    .filter(([a, b]) => a.coverage >= minChart && b.coverage >= minChart)
    .map(([a, b]) => ({ from: a.name, to: b.name, gain: b.index - a.index }))
    .sort((a, b) => b.gain - a.gain).slice(0, 6);
  const flops = data.families.flatMap(f => f.generations.slice(1).map((g, i) => [f.generations[i], g]))
    .filter(([a, b]) => a.coverage >= minChart && b.coverage >= minChart && b.index < a.index)
    .map(([a, b]) => ({ from: a.name, to: b.name, gain: b.index - a.index }))
    .sort((a, b) => a.gain - b.gain).slice(0, 5);
  document.getElementById("flops").innerHTML = flops.length
    ? flops.map(j => `<li>${esc(j.to)} <span>${j.gain.toFixed(1)}</span><br><small>worse than ${esc(j.from)}</small></li>`).join("")
    : "<li>None. Every lab improved. Enjoy it while it lasts.</li>";
  document.getElementById("jumps").innerHTML = jumps
    .map(j => `<li>${esc(j.to)} <span>+${j.gain.toFixed(1)}</span><br><small>from ${esc(j.from)}</small></li>`).join("");

  document.getElementById("families").innerHTML = data.families.map(familyHtml).join("");
  document.querySelectorAll(".fam a.toggle").forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    const box = a.closest(".fam");
    const open = box.classList.toggle("open");
    a.textContent = open ? "[-]" : "[+]";
    a.setAttribute("aria-expanded", String(open));
  }));

  function familyHtml(f) {
    const gs = charted(f);
    const first = gs[0], last = gs[gs.length - 1];
    const summary = gs.length >= 2
      ? `${esc(first.name)} ${first.index.toFixed(1)} &rarr; ${esc(last.name)} <b>${last.index.toFixed(1)}</b> (+${(last.index - first.index).toFixed(1)})`
      : "Not enough measured generations to chart yet.";
    const cols = data.tracked.map(b => `<th title="${esc(b.name)}">${esc(SHORT[b.id] || b.name)}</th>`).join("");
    const rows = f.generations.map(g => {
      const thin = g.coverage < minChart;
      const vals = data.tracked.map(b => {
        const v = g.scores[b.id];
        return `<td>${v == null ? '<span class="est">-</span>' : v > 100 ? v.toFixed(0) : v.toFixed(1)}</td>`;
      }).join("");
      return `<tr class="${thin ? "dim" : ""}"><td class="l gen" title="${esc(g.title)}">${iconSvg(g, 16)} ${esc(g.name)}</td><td class="l">${esc(fmtDate(g.released))}</td>
        <td>${thin ? `<span class="est" title="Mostly estimated">${g.index.toFixed(1)}*</span>` : `<b>${g.index.toFixed(1)}</b>`}</td><td>${g.coverage}%</td>${vals}</tr>`;
    }).join("");
    return `<div class="fam dim-block" id="${slug(f.name)}">
      <h3>${esc(f.name)} <span>${esc(f.maker)}</span></h3>
      <div class="fam-body">
        ${gs.length >= 2 ? chart(gs) : ""}
        <p class="fam-summary">${summary}</p>
        <p><a href="#" class="toggle" aria-expanded="false">[+]</a> Every generation and its raw benchmark results</p>
        <div class="table-wrap fam-table"><table class="ranking">
          <thead><tr><th class="l">Generation</th><th class="l">Released</th><th>Score</th><th>Measured</th>${cols}</tr></thead>
          <tbody>${rows}</tbody>
        </table></div>
      </div>
    </div>`;
  }

  function chart(gs) {
    const W = 640, H = 170, L = 34, R = 92, T = 10, B = 24;
    const x = t => L + (W - L - R) * (t - t0) / Math.max(1, t1 - t0);
    const y = v => T + (H - T - B) * (1 - v / 100);
    const grid = [0, 25, 50, 75, 100].map(v =>
      `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${L - 6}" y="${y(v) + 3}" class="axis" text-anchor="end">${v}</text>`).join("");
    const ticks = [];
    const start = new Date(t0); start.setDate(1);
    for (let d = new Date(start); d.getTime() <= t1; d.setMonth(d.getMonth() + 6)) {
      if (d.getTime() >= t0) ticks.push(`<text x="${x(d.getTime())}" y="${H - 6}" class="axis" text-anchor="middle">${fmtMonth(d.getTime())}</text>`);
    }
    const pts = gs.map(g => [x(day(g.released)), y(g.index)]);
    const path = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
    const dots = gs.map((g, i) => `<circle cx="${pts[i][0].toFixed(1)}" cy="${pts[i][1].toFixed(1)}" r="3" class="dot"><title>${esc(g.name)}: ${g.index.toFixed(1)} (${esc(fmtDate(g.released))}, ${g.coverage}% measured)</title></circle>`).join("");
    const last = gs[gs.length - 1], lp = pts[pts.length - 1];
    return `<svg class="hist-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Score by release date">
      ${grid}${ticks.join("")}
      <path d="${path}" class="line"/>${dots}
      <text x="${lp[0] + 8}" y="${lp[1] + 4}" class="last">${esc(last.name.replace(/^(Claude|GPT-?|Gemini|DeepSeek|Kimi|Muse) /, ""))} ${last.index.toFixed(1)}</text>
    </svg>`;
  }
})();
