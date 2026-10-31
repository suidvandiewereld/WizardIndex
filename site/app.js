(async function () {
  const res = await fetch("data/index.json", { cache: "no-cache" });
  const data = await res.json();
  const dims = data.dimensions;
  const benchName = Object.fromEntries(dims.flatMap(d => d.benchmarks.map(b => [b.id, b.name])));
  const benchDim = Object.fromEntries(dims.flatMap(d => d.benchmarks.map(b => [b.id, d.id])));
  const benchUrl = Object.fromEntries(dims.flatMap(d => d.benchmarks.map(b => [b.id, b.url])));
  const liveDims = dims.filter(d => d.benchmarks.some(b => b.n_results > 0));
  const showAll = document.getElementById("show-all");

  const benchKind = Object.fromEntries(dims.flatMap(d => d.benchmarks.map(b => [b.id, b.kind])));
  const SHORT = { swe: "Coding", taste: "Taste", agentic: "Agentic", reasoning: "Reasoning", adaptability: "Adapting", spatial: "Spatial", creativity: "Creative", reliability: "Reliable", price: "Thrift", architecture: "Architecture", cleanliness: "Clean code", instructions: "Instructions" };
  // Column headers, kept short so the ranking table fits without scrolling; the full name is the tooltip.
  const HEAD = { swe: "Code", taste: "Taste", agentic: "Agent", reasoning: "Reason", adaptability: "Adapt",
    reliability: "Truth", spatial: "Space", creativity: "Ideas", price: "Thrift" };
  const dollars = v => "$" + Math.round(v).toLocaleString("en-US");
  // The dollar figure behind a model's price score, for the cell tooltip.
  const costOf = m => Object.entries(m.benchmarks).find(([id]) => benchKind[id] === "cost");
  const PHRASE = { swe: "real coding", taste: "design taste", agentic: "agentic work", reasoning: "reasoning",
    adaptability: "anything unfamiliar", reliability: "not making stuff up", spatial: "spatial work", creativity: "creative problems" };
  const ORGS = { openai: "OpenAI", xai: "xAI", "z.ai": "Z.ai", zhipu: "Z.ai", deepseek: "DeepSeek", minimax: "MiniMax", moonshot: "Moonshot AI", kimi: "Moonshot AI", "moonshot ai": "Moonshot AI", alibaba: "Alibaba",
    google: "Google", "google deepmind": "Google DeepMind", "google-deepmind": "Google DeepMind", "meta ai": "Meta AI", meta: "Meta", "mistral ai": "Mistral AI" };
  const orgName = o => ORGS[o] || o.charAt(0).toUpperCase() + o.slice(1);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtDate = iso => iso ? new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "never";

  const updated = `Last updated ${fmtDate(data.generated_at)}`;
  document.getElementById("foot-stamp").textContent = `${updated}.`;
  document.getElementById("max-age").textContent = data.ranking?.max_age_days ?? 120;
  const liveWeight = liveDims.reduce((a, d) => a + d.weight, 0);
  const totalWeight = dims.reduce((a, d) => a + d.weight, 0);
  document.getElementById("coverage-note").textContent =
    `${liveDims.length} of ${dims.length} skills have published leaderboard data so far (${Math.round(100 * liveWeight / totalWeight)}% of the planned weight). ` +
    `The rest join once somebody actually publishes numbers for them.`;

  renderChart();
  renderFinder();
  renderHead();
  renderBody();
  renderSidebar();
  renderDims();
  showAll.addEventListener("change", renderBody);

  function skillValue(m, id) {
    if (m.dimensions[id] != null) return { v: m.dimensions[id], est: false };
    if (m.estimated?.[id] != null) return { v: m.estimated[id], est: true, from: m.estimated_from?.[id] };
    return null;
  }

  // Every ranked model's index as a bar on one 0-100 scale, in two columns so it stays short.
  // Clicking a bar opens that model's row in the table below, which doubles as the chart's table view.
  function renderChart() {
    const ranked = data.models.filter(m => m.ranked);
    if (!ranked.length) return;
    const half = Math.ceil(ranked.length / 2);
    const row = m => `<li><a href="#" class="ic-row" data-model="${esc(m.model)}"
        title="#${m.rank} ${esc(m.name)}, ${esc(m.title)}: ${m.index.toFixed(1)} (${m.coverage}% measured). Click for the details.">
      <span class="ic-rank">${m.rank}</span>
      <span class="ic-name">${iconSvg(m, 16)} ${esc(m.name)}</span>
      <span class="ic-track"><i style="width:${Math.max(0, Math.min(100, m.index)).toFixed(1)}%"></i></span>
      <span class="ic-score">${m.index.toFixed(1)}</span></a></li>`;
    const axis = `<div class="ic-axis" aria-hidden="true"><span></span><span class="ic-ticks">${
      [0, 25, 50, 75, 100].map(t => `<b style="left:${t}%">${t}</b>`).join("")}</span></div>`;
    const col = list => `<div class="ic-col"><ol>${list.map(row).join("")}</ol>${axis}</div>`;
    const box = document.getElementById("index-chart");
    box.innerHTML = `<h3>The index at a glance <span>${ranked.length} ranked models, out of 100</span></h3>
      <div class="ic-cols">${col(ranked.slice(0, half))}${col(ranked.slice(half))}</div>`;
    box.querySelectorAll("a.ic-row").forEach(a => a.addEventListener("click", e => {
      e.preventDefault();
      reveal(a.dataset.model);
    }));
  }

  // "Which model for my job?": a job weights the skills it leans on, a bar sets how good is good
  // enough, and every ranked model is sorted into the cheapest that clears the bar, ones worth paying
  // more for, overkill (a cheaper model does the job as well) and not enough. Jobs and bars live in
  // config/tasks.yaml; each model shows its real result on the benchmark closest to the job.
  function renderFinder() {
    const { jobs = [], bars = [] } = data.tasks || {};
    const form = document.getElementById("finder");
    if (!jobs.length || !bars.length) return;
    const ranked = data.models.filter(m => m.ranked);
    form.innerHTML = `<fieldset><legend>Which model for my job?</legend>
      <div class="finder-ask">
        <label>I need to <select id="f-job">${jobs.map(j => `<option value="${esc(j.id)}">${esc(j.name)}</option>`).join("")}</select></label>
        <label>and it is <select id="f-bar">${bars.map(b => `<option value="${esc(b.id)}">${esc(b.name.toLowerCase())}</option>`).join("")}</select></label>
      </div>
      <div id="f-out"></div></fieldset>`;
    const jobSel = form.querySelector("#f-job"), barSel = form.querySelector("#f-bar");
    try {
      const saved = JSON.parse(localStorage.getItem("wi-finder") || "{}");
      if (jobs.some(j => j.id === saved.job)) jobSel.value = saved.job;
      if (bars.some(b => b.id === saved.bar)) barSel.value = saved.bar;
    } catch (e) { /* no storage: defaults */ }
    const update = () => {
      try { localStorage.setItem("wi-finder", JSON.stringify({ job: jobSel.value, bar: barSel.value })); } catch (e) { /* fine */ }
      showFinder(jobs.find(j => j.id === jobSel.value), bars.find(b => b.id === barSel.value), ranked);
    };
    jobSel.addEventListener("change", update);
    barSel.addEventListener("change", update);
    update();
  }

  // A model's fit for a job: the job's skill weights over the model's skill scores, measured or estimated.
  function jobFit(m, job) {
    let sum = 0, weight = 0, guessed = 0;
    for (const [id, w] of Object.entries(job.skills)) {
      const s = skillValue(m, id);
      if (!s) continue;
      sum += w * s.v; weight += w;
      if (s.est) guessed += w;
    }
    return weight ? { v: sum / weight, guessed: guessed / weight } : null;
  }

  // The model's real result on the first of the job's benchmarks it was tested on, as a sentence.
  function proofOf(m, job) {
    for (const p of job.proof || []) {
      const r = m.benchmarks[p.bench];
      const v = r && proofValue(r, p.format);
      if (v != null) return { p, v, text: p.text.replace("{v}", proofFormat(v, p.format)) };
    }
    return null;
  }
  function proofValue(r, format) {
    if (format !== "winrate") return r.score;
    const hit = (r.notes || []).join(" ").match(/([\d.]+)% win rate/);
    return hit ? +hit[1] : null;
  }
  function proofFormat(v, format) {
    if (format === "pct" || format === "winrate") return `${v.toFixed(0)}%`;
    if (format === "signed") return `${v > 0 ? "+" : ""}${v.toFixed(0)}`;
    return Math.round(v).toLocaleString("en-US");
  }

  function showFinder(job, bar, ranked) {
    const thrift = m => skillValue(m, "price")?.v ?? 0;
    const rows = ranked.map(m => ({ m, fit: jobFit(m, job), cost: thrift(m), proof: proofOf(m, job) })).filter(r => r.fit);
    const enough = rows.filter(r => r.fit.v >= bar.min);
    const short = rows.filter(r => r.fit.v < bar.min).sort((a, b) => b.fit.v - a.fit.v);
    // Older version: a newer model in the same product line does this job as well, for about the same price.
    const successor = r => enough.find(o => o !== r && o.m.line && o.m.line === r.m.line
      && (o.m.released || "") > (r.m.released || "") && o.fit.v >= r.fit.v - 1 && o.cost >= r.cost - 5);
    const older = enough.filter(successor);
    const current = enough.filter(r => !older.includes(r));
    // Overkill: another model that clears the bar does this job about as well (within a point) and costs less.
    const overkill = current.filter(r => current.some(o => o !== r && o.fit.v >= r.fit.v - 1 && o.cost > r.cost + 1));
    const worth = current.filter(r => !overkill.includes(r)).sort((a, b) => b.cost - a.cost);
    overkill.sort((a, b) => b.fit.v - a.fit.v);

    // What a model just over the bar actually achieves on the job's benchmark.
    const near = enough.filter(r => r.fit.v < bar.min + 10 && r.proof);
    let typical = "";
    if (near.length >= 2) {
      const bench = near[0].proof.p, vals = near.filter(r => r.proof.p === bench).map(r => r.proof.v).sort((a, b) => a - b);
      if (vals.length >= 2) typical = ` Typical for a model just over it: ${bench.text.replace("{v}", proofFormat(vals[Math.floor(vals.length / 2)], bench.format))}.`;
    }

    const line = (r, verdict, cls, why = "") => {
      const c = costOf(r.m);
      const price = c ? `${dollars(c[1].score)}${c[1].plan ? ` on ${c[1].plan}` : ""}: ${benchName[c[0]]}` : "No price data; estimated";
      const fit = `${r.fit.v.toFixed(0)}${r.fit.guessed > 0.3 ? `<span class="est" title="Partly estimated: not every skill this job needs has been tested">*</span>` : ""}`;
      return `<tr class="${cls}"><td class="verdict-cell"${why ? ` title="${esc(why)}"` : ""}>${verdict}</td>
        <td class="l"><a href="#" class="f-model" data-model="${esc(r.m.model)}">${iconSvg(r.m, 16)} ${esc(r.m.name)}</a></td>
        <td>${fit}</td><td title="${esc(price)}">${r.cost.toFixed(0)}</td>
        <td class="l proof">${r.proof ? esc(r.proof.text) : `<span class="untested">not tested on a benchmark like this yet</span>`}</td></tr>`;
    };
    const body = [
      ...worth.map((r, i) => line(r, i ? "Step up" : "<b>Best pick</b>", i ? "step" : "pick")),
      ...overkill.slice(0, 5).map(r => line(r, "Overkill", "over")),
      ...older.slice(0, 5).map(r => line(r, "Older version", "over", `${successor(r).m.name} replaces it: as good at this job, for about the same price`)),
      ...short.slice(0, 3).map(r => line(r, "Not enough", "short")),
    ].join("");
    const hidden = [overkill.length > 5 && `${overkill.length - 5} more cost more than a model that does this job as well`,
      older.length > 5 && `${older.length - 5} more older versions are replaced by newer ones`].filter(Boolean);
    const more = hidden.length ? `<p class="small-note">${hidden.join("; ")}.</p>` : "";
    document.getElementById("f-out").innerHTML = `
      <p class="finder-bar"><b>${esc(bar.name)}</b> means a fit of ${bar.min} or more for this job. ${esc(bar.blurb)}
        ${enough.length} of ${rows.length} ranked models clear it.${esc(typical)}</p>
      ${enough.length ? "" : `<p class="finder-none">No ranked model clears this bar for this job yet. The closest are below.</p>`}
      <table class="finder-table">
        <tr><th></th><th class="l">Model</th><th title="Weighted mean of the skills this job needs, on the table's scale">Fit</th><th title="Higher is cheaper (the Thrift column)">Thrift</th><th class="l">What it actually did</th></tr>
        ${body}
      </table>${more}
      <p class="small-note">Best pick is the cheapest model that clears the bar. Step up means better at this job, at a higher price. Overkill means a cheaper model does this job about as well. Older version means a newer model from the same line replaces it.</p>`;
    document.querySelectorAll("#f-out a.f-model").forEach(a => a.addEventListener("click", e => {
      e.preventDefault();
      reveal(a.dataset.model);
    }));
  }

  // Scrolls the table to a model and opens its details.
  function reveal(id) {
    if (!showAll.checked && !data.models.find(m => m.model === id)?.ranked) { showAll.checked = true; renderBody(); }
    const row = document.querySelector(`#ranking tr.model[data-model="${id}"]`);
    if (!row) return;
    row.scrollIntoView({ block: "center" });
    const t = row.querySelector("a.toggle");
    if (t.textContent === "[+]") toggle(t);
  }

  function renderHead() {
    const cols = liveDims.map(d => `<th class="skill" title="${esc(d.name)}">${esc(HEAD[d.id] || SHORT[d.id] || d.name)}<small>${d.weight}%</small></th>`).join("");
    document.querySelector("#ranking thead").innerHTML =
      `<tr><th>#</th><th class="l">Model</th><th>Score</th>${cols}<th title="Share of the score that is measured, not estimated">Data</th></tr>`;
  }

  function renderBody() {
    const models = data.models.filter(m => m.ranked || showAll.checked);
    const tbody = document.querySelector("#ranking tbody");
    tbody.innerHTML = models.map(rowHtml).join("");
    tbody.querySelectorAll("a.toggle").forEach(a => a.addEventListener("click", e => { e.preventDefault(); toggle(a); }));
  }

  function rowHtml(m, i) {
    const cells = liveDims.map(d => {
      const s = skillValue(m, d.id);
      if (!s) return `<td class="skill est">n/a</td>`;
      if (s.est) return `<td class="skill est" title="${s.from ? `Estimated from ${esc(s.from)}, which was tested here` : "Estimated: not tested in this skill yet"}">${s.v.toFixed(0)}*</td>`;
      const cost = !d.skill && costOf(m);
      const c = cost && cost[1], at = c && c.effort ? ` at ${esc(c.effort)}` : "";
      const tip = !c ? "" : c.plan
        ? ` title="${dollars(c.score)} to run the evals${at} on ${esc(c.plan)} (${dollars(c.list_price)} at API prices)"`
        : ` title="${dollars(c.score)} to run the evals${at}, at API prices"`;
      return `<td class="skill ${s.v >= 85 ? "hi" : s.v >= 60 ? "mid" : "lo"}"${tip}>${s.v.toFixed(0)}</td>`;
    }).join("");
    const flag = m.outdated ? "outdated" : !m.ranked ? "unranked" : "";
    const cls = ["model", i % 2 ? "" : "odd", m.rank && m.rank <= 3 ? "top" : "", m.ranked ? "" : "dim"].join(" ");
    const sub = m.org ? orgName(m.org) : "";
    return `<tr class="${cls}" data-model="${esc(m.model)}">
      <td class="rank">${m.rank ?? "-"}</td>
      <td class="l who"><div class="who-in"><a href="#" class="toggle" aria-expanded="false" aria-label="Show details for ${esc(m.name)}">[+]</a>${iconSvg(m, 24)}<div>
        <span class="name" title="${esc(verdict(m))}">${esc(m.name)}</span>${flag ? `<span class="flag">${flag}</span>` : ""}
        <span class="title">${esc(m.title)}</span><span class="org">${esc(sub)}</span></div></div></td>
      <td class="score-cell"><span class="score">${m.index.toFixed(1)}</span></td>
      ${cells}
      <td>${m.coverage}%</td>
    </tr>`;
  }

  function toggle(a) {
    const tr = a.closest("tr");
    const next = tr.nextElementSibling;
    if (next && next.classList.contains("details")) {
      next.remove();
      a.textContent = "[+]";
      a.setAttribute("aria-expanded", "false");
      return;
    }
    const m = data.models.find(x => x.model === tr.dataset.model);
    // One block per skill: the skill and the model's score in it, then each benchmark behind it.
    const rows = liveDims.map(d => {
      const results = Object.entries(m.benchmarks).filter(([id]) => benchDim[id] === d.id);
      const s = skillValue(m, d.id);
      const head = `<td class="skill" rowspan="${Math.max(results.length, 1)}"${s?.from ? ` title="Estimated from ${esc(s.from)}"` : ""}>${esc(d.name)}` +
        `<span class="skill-score">${s ? (s.est ? `<i class="est">${s.v.toFixed(0)}* estimated</i>` : s.v.toFixed(0)) : "n/a"}</span></td>`;
      if (!results.length) return `<tr>${head}<td colspan="4" class="untested">Not tested on any benchmark here yet. ${s?.from
        ? `Estimated from ${esc(s.from)}, which was.` : "Estimated from its other results."}</td></tr>`;
      return results.map(([id, r], i) => {
        const val = benchKind[id] === "cost" ? dollars(r.score) : r.score > 100 ? r.score.toFixed(0) : `${r.score.toFixed(1)}%`;
        const ci = r.ci != null ? ` <span class="ci">&plusmn;${(+r.ci).toFixed(1)}</span>` : "";
        const effort = r.effort && !r.model_raw.toLowerCase().includes(r.effort.toLowerCase()) ? ` (${esc(r.effort)})` : "";
        const notes = (r.notes || []).map(n => `<span class="${/contamination/.test(n) ? "warn" : ""}">${linkify(n)}</span>`).join("<br>");
        const bench = benchUrl[id] ? `<a href="${esc(benchUrl[id])}">${esc(benchName[id] || id)}</a>` : esc(benchName[id] || id);
        return `<tr>${i ? "" : head}<td>${bench}</td><td class="res"><b>${val}</b>${ci}</td><td class="raw">${esc(r.model_raw)}${effort}</td><td class="notes">${notes}</td></tr>`;
      }).join("");
    }).join("");
    const detail = document.createElement("tr");
    detail.className = "details";
    const released = m.released ? `<p>Released ${fmtDate(m.released)}. ${m.coverage}% of this score is measured.</p>` : "";
    detail.innerHTML = `<td colspan="${liveDims.length + 4}"><div class="seal">${iconSvg(m, 64)}<span>${esc(m.title)}</span></div><p class="verdict"><b>Verdict:</b> ${esc(verdict(m))}</p>${aboutHtml(m.about)}${released}
      <table class="receipts"><tr><th>Skill</th><th>Benchmark</th><th>Result</th><th class="raw">Listed as</th><th class="notes">Notes</th></tr>${rows}</table></td>`;
    tr.after(detail);
    a.textContent = "[-]";
    a.setAttribute("aria-expanded", "true");
  }

  // Escapes a note and turns any URL in it into a short link ("cursor.com/cursorbench").
  function linkify(text) {
    return String(text).split(/(https?:\/\/\S+)/).map((part, i) => {
      if (i % 2 === 0) return esc(part);
      const url = part.replace(/[.,;)]+$/, "");
      let label = url;
      try { const u = new URL(url); label = u.hostname.replace(/^www\./, "") + u.pathname.replace(/\/$/, ""); } catch (e) { /* keep raw */ }
      return `<a href="${esc(url)}">${esc(label)}</a>${esc(part.slice(url.length))}`;
    }).join("");
  }

  // Hand-written verdicts where we have them; otherwise a quip built from the model's own measured scores.
  function verdict(m) {
    if (m.about?.verdict) return m.about.verdict;
    const measured = liveDims.filter(d => d.skill && m.dimensions[d.id] != null)
      .map(d => ({ name: PHRASE[d.id] || d.name.toLowerCase(), v: m.dimensions[d.id] }));
    if (measured.length < 2) return "Barely tested. Ask again later.";
    measured.sort((a, b) => b.v - a.v);
    const best = measured[0], worst = measured[measured.length - 1];
    if (worst.v >= 80) return "No glaring weakness anywhere. Suspicious, but fine.";
    if (best.v < 60) return `Mediocre across the board. Its best skill is ${best.name}, at ${best.v.toFixed(0)}.`;
    const how = worst.v < 25 ? "falls flat on its face at" : worst.v < 45 ? "hopeless at" : "shaky at";
    return `${best.v >= 85 ? "Strong" : "Decent"} at ${best.name} (${best.v.toFixed(0)}), ${how} ${worst.name} (${worst.v.toFixed(0)}).`;
  }

  function aboutHtml(about) {
    if (!about?.description) return "";
    const list = (label, items) => items?.length
      ? `<p><b>${label}:</b> ${items.map(esc).join(", ")}</p>` : "";
    const sources = (about.sources || []).map(s => `<a href="${esc(s.url)}">${esc(s.title)}</a>`).join(" &middot; ");
    const thin = about.evidence === "thin" ? ` <span class="flag">little discussion found</span>` : "";
    return `<div class="about">
      <h4>What people say${thin}</h4>
      <p>${esc(about.description)}</p>
      ${list("Praised for", about.praised)}
      ${list("Common complaints", about.criticized)}
      ${about.basis ? `<p class="about-src">Based on ${esc(about.basis)}.</p>` : ""}
      <p class="about-src">Sources: ${sources}${about.as_of ? ` (researched ${fmtDate(about.as_of)})` : ""}</p>
    </div>`;
  }

  function renderShame() {
    const ranked = data.models.filter(m => m.ranked);
    const picks = [
      ["reliability", "Biggest fibber"],
      ["adaptability", "Most lost outside its comfort zone"],
      ["agentic", "Shouldn't be trusted with a terminal"],
      ["taste", "Ugliest output"],
      ["swe", "Worst actual coder"],
    ].filter(([id]) => liveDims.some(d => d.id === id));
    document.getElementById("shame").innerHTML = picks.map(([id, label]) => {
      const pool = ranked.filter(m => m.dimensions[id] != null);
      if (!pool.length) return "";
      const worst = pool.reduce((a, b) => (b.dimensions[id] < a.dimensions[id] ? b : a));
      return `<li><b>${label}:</b> ${esc(worst.name)} <span>${worst.dimensions[id].toFixed(0)}</span></li>`;
    }).join("");
  }

  function renderSidebar() {
    renderShame();
    const maxW = Math.max(...liveDims.map(d => d.weight));
    const pending = dims.filter(d => !liveDims.includes(d)).map(d => SHORT[d.id] || d.name);
    document.getElementById("weights").innerHTML = liveDims.map(d =>
      `<tr><td>${esc(SHORT[d.id] || d.name)}</td><td class="wbar"><i style="width:${(100 * d.weight / maxW).toFixed(0)}%"></i></td><td>${d.weight}%</td></tr>`
    ).join("") + (pending.length ? `<tr class="none"><td colspan="3">Not scored yet: ${esc(pending.join(", "))}</td></tr>` : "");
    const now = new Date(data.generated_at);
    const fresh = data.models.filter(m => !m.ranked && m.released && Object.keys(m.dimensions).length
      && (now - new Date(m.released + "T00:00:00")) / 864e5 <= 30)
      .sort((a, b) => b.released.localeCompare(a.released));
    if (fresh.length) {
      document.getElementById("new-box").hidden = false;
      document.getElementById("newlist").innerHTML = fresh.map(m => {
        const has = liveDims.filter(d => m.dimensions[d.id] != null).map(d => SHORT[d.id] || d.name);
        return `<li><a href="#" data-model="${esc(m.model)}">${esc(m.name)}</a> <span class="when">${esc(fmtDate(m.released))}</span>
          <span class="has">Tested so far: ${esc(has.join(", "))}</span></li>`;
      }).join("");
      document.querySelectorAll("#newlist a").forEach(a => a.addEventListener("click", e => {
        e.preventDefault();
        reveal(a.dataset.model);
      }));
    }
    document.getElementById("top5").innerHTML = data.models.filter(m => m.ranked).slice(0, 5)
      .map(m => `<li>${iconSvg(m, 16)} ${esc(m.name)} <span>${m.index.toFixed(1)}</span></li>`).join("");
  }

  function renderDims() {
    document.getElementById("dims").innerHTML = dims.map(d => `
      <div class="dim-block">
        <h3>${esc(d.name)} <span>${d.weight}% of score</span></h3>
        <ul>${d.benchmarks.map(b => {
          const live = b.n_results > 0;
          return `<li><span class="dot ${live ? "live" : ""}"></span> <a href="${esc(b.url)}">${esc(b.name)}</a>
            <span class="n">${live ? `(${b.n_results} models, fetched ${fmtDate(b.fetched_at)})` : "(no data yet)"}</span></li>`;
        }).join("")}</ul>
      </div>`).join("");
  }
})();
