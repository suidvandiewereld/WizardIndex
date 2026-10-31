// The Data sources page: every benchmark behind each skill, how fresh it is, and how the
// cross-checked ones compare with a second published run.
(async function () {
  const data = await (await fetch("data/index.json", { cache: "no-cache" })).json();
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtDate = iso => iso ? new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "never";
  const share = d => `${Math.round(d.share ?? 0)}%`;

  function checkLine(id) {
    const c = (data.checks || []).find(x => x.benchmark === id);
    if (!c) return "";
    if (c.offset == null) return `<span class="check">Cross-check against ${esc(c.against_name)}: only ${c.shared} models in common so far.</span>`;
    const name = id => esc(data.models.find(m => m.model === id)?.name || id);
    const flagged = c.flagged.length
      ? ` <span class="warn">Disagree by more than ${c.tolerance} points beyond that: ${c.flagged.map(f => name(f.model)).join(", ")}.</span>`
      : ` No model strays more than ${c.tolerance} points from that.`;
    return `<span class="check">Cross-checked against ${esc(c.against_name)} on ${c.shared} shared models: typically within ` +
      `${c.spread.toFixed(1)} points of a steady ${c.offset > 0 ? "+" : ""}${c.offset.toFixed(1)}-point gap.${flagged}</span>`;
  }

  document.getElementById("dims").innerHTML = data.dimensions.map(d => `
    <div class="dim-block" id="${esc(d.id)}">
      <h2>${esc(d.name)} <span>${d.share != null ? `${share(d)} of score` : "not scored yet"}</span></h2>${d.estimate_error != null
        ? `<p class="dim-note">Where a model is untested here, its estimate is typically off by ${d.estimate_error.toFixed(0)} points (checked by hiding tested models' real results and estimating them).</p>` : ""}
      <ul>${d.benchmarks.map(b => {
        const live = b.n_results > 0;
        return `<li><span class="dot ${live ? "live" : ""}"></span> <a href="${esc(b.url)}">${esc(b.name)}</a>
          <span class="n">${live ? `(${b.n_results} models, fetched ${fmtDate(b.fetched_at)})` : "(no data yet)"}</span>${checkLine(b.id)}</li>`;
      }).join("")}</ul>
    </div>`).join("");
  document.getElementById("toc").innerHTML = data.dimensions.map(d => `<li><a href="#${esc(d.id)}">${esc(d.name)}</a></li>`).join("");
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (target) target.scrollIntoView();
})();
