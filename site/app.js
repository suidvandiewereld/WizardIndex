(async function () {
  // The data sources used to be a section of this page; old links to it go to their own page now.
  if (location.hash === "#sources") { location.replace("sources.html"); return; }
  const res = await fetch("data/index.json", { cache: "no-cache" });
  const data = await res.json();
  const dims = data.dimensions;
  const benchName = Object.fromEntries(dims.flatMap(d => d.benchmarks.map(b => [b.id, b.name])));
  const benchDim = Object.fromEntries(dims.flatMap(d => d.benchmarks.map(b => [b.id, d.id])));
  const benchUrl = Object.fromEntries(dims.flatMap(d => d.benchmarks.map(b => [b.id, b.url])));
  const liveDims = dims.filter(d => d.benchmarks.some(b => b.n_results > 0));
  const showAll = document.getElementById("show-all");
  const findBox = document.getElementById("find");
  const labSel = document.getElementById("lab");
  // Table order: null is the overall ranking; otherwise a column key, highest first unless sortUp.
  let sortKey = null, sortUp = false;
  const MAX_COMPARE = 4;
  const picked = new Set(loadPicks());

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
  // Leaderboards spell some labs several ways; each lab gets one name, so the table and the lab filter agree.
  const ORGS = { openai: "OpenAI", xai: "xAI", "z.ai": "Z.ai", "z.ai (zhipu ai)": "Z.ai", zhipu: "Z.ai", deepseek: "DeepSeek", minimax: "MiniMax", moonshot: "Moonshot AI", kimi: "Moonshot AI", "moonshot ai": "Moonshot AI", alibaba: "Alibaba",
    google: "Google DeepMind", "google deepmind": "Google DeepMind", "google-deepmind": "Google DeepMind", "meta ai": "Meta", meta: "Meta", mistral: "Mistral AI", "mistral ai": "Mistral AI", nvidia: "NVIDIA",
    stepfun: "StepFun", "thinking machines": "Thinking Machines", "institute of foundation models": "Institute of Foundation Models" };
  const orgName = o => ORGS[o] || o.charAt(0).toUpperCase() + o.slice(1);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtDate = iso => iso ? new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "never";

  const updated = `Last updated ${fmtDate(data.generated_at)}`;
  document.getElementById("foot-stamp").textContent = `${updated}.`;
  document.getElementById("max-age").textContent = data.ranking?.max_age_days ?? 120;
  const pending = dims.filter(d => !liveDims.includes(d)).map(d => SHORT[d.id] || d.name);
  // A skill's real share of the score: its weight over the skills that have data, as computed by the build.
  const share = d => `${Math.round(d.share ?? 0)}%`;
  // How far a partly estimated score could be off ("" when it is all measured), and the ranks that spans.
  const plusMinus = m => m.margin >= 0.5 ? ` ±${m.margin.toFixed(1)}` : "";
  const rankSpan = m => m.rank_range && m.rank_range[0] !== m.rank_range[1] ? `${m.rank_range[0]}–${m.rank_range[1]}` : "";
  document.getElementById("coverage-note").innerHTML = `<h2>Reading this table</h2><ul>
    <li>100 is this week's leader on each benchmark and 50 the middle of the ranked models, so scores are relative: a model's score can move when others join or leave the board, even if its own results haven't changed. The raw results behind each <b>[+]</b> are absolute.</li>
    <li>The weights are each skill's real share of the score. ${liveDims.length} of ${dims.length} skills have published leaderboard data so far${pending.length
      ? `; ${esc(pending.join(", "))} count${pending.length === 1 ? "s" : ""} once somebody actually publishes numbers for ${pending.length === 1 ? "it" : "them"}` : ""}.</li>
    <li>A <span class="est">*</span> is an estimate, and &plusmn; is how far it could be off.</li></ul>`;

  // Rank changes since the ranking before this one, when the build kept it (data/previous_ranks.json).
  const wasRank = data.previous?.ranks || {};
  const since = data.previous?.generated_at;
  const isNew = m => m.released && (new Date(data.generated_at) - new Date(m.released + "T00:00:00")) / 864e5 <= 14;
  document.getElementById("key").innerHTML = [
    `<span><i class="sw hi"></i>85+</span>`, `<span><i class="sw mid"></i>60&ndash;84</span>`, `<span><i class="sw lo"></i>under 60</span>`,
    `<span><i class="est">63*</i> estimated</span>`, `<span><b>&plusmn;</b> possible error</span>`,
    `<span><span class="new-badge">NEW</span> last two weeks</span>`,
    since ? `<span><b class="mv up">&#9650;</b><b class="mv down">&#9660;</b> since ${new Date(since).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>` : "",
    `<span><i class="tick-box"></i>tick to compare</span>`,
  ].join("");

  renderChart();
  renderFinder();
  renderHead();
  renderLabs();
  renderBody();
  renderCompare();
  renderSidebar();
  showAll.addEventListener("change", () => { renderLabs(); renderBody(); });
  findBox.addEventListener("input", renderBody);
  labSel.addEventListener("change", renderBody);
  document.getElementById("show-all-n").textContent = `(${data.models.filter(m => !m.ranked).length} more)`;
  document.querySelector("#ranking thead").addEventListener("click", e => {
    const b = e.target.closest("button.sort");
    if (!b) return;
    const key = b.dataset.key;
    if (key === "rank") sortKey = null;
    else if (key === sortKey) sortUp = !sortUp;
    else { sortKey = key; sortUp = key === "name"; }
    renderHead();
    renderBody();
  });
  // A shared link to one model (#model=<id>) opens its details.
  const linked = location.hash.match(/^#model=(.+)$/);
  if (linked) reveal(decodeURIComponent(linked[1]));

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
    const clip = v => Math.max(0, Math.min(100, v));
    // A whisker across the bar's end where part of the score is estimated: how far it could be off.
    const whisker = m => m.margin >= 0.5
      ? `<s style="left:${clip(m.index - m.margin).toFixed(1)}%;width:${(clip(m.index + m.margin) - clip(m.index - m.margin)).toFixed(1)}%"></s>` : "";
    const row = m => `<li><a href="#" class="ic-row" data-model="${esc(m.model)}"
        title="#${m.rank} ${esc(m.name)}, ${esc(m.title)}: ${m.index.toFixed(1)}${plusMinus(m)} (${m.coverage}% measured). Click for the details.">
      <span class="ic-rank">${m.rank}</span>
      <span class="ic-name">${iconSvg(m, 16)} ${esc(m.name)}</span>
      <span class="ic-track"><i style="width:${clip(m.index).toFixed(1)}%"></i>${whisker(m)}</span>
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
    if (!showAll.checked && !data.models.find(m => m.model === id)?.ranked) { showAll.checked = true; renderLabs(); renderBody(); }
    if (!document.querySelector(`#ranking tr.model[data-model="${CSS.escape(id)}"]`) && (findBox.value || labSel.value)) {
      findBox.value = "";
      labSel.value = "";
      renderBody();
    }
    const row = document.querySelector(`#ranking tr.model[data-model="${CSS.escape(id)}"]`);
    if (!row) return;
    row.scrollIntoView({ block: "center" });
    const t = row.querySelector("a.toggle");
    if (t.textContent === "[+]") toggle(t);
  }

  // Every heading sorts the table by its column; # goes back to the overall ranking.
  function renderHead() {
    const cols = [
      { key: "rank", label: "#", title: "The overall ranking" },
      { key: "name", label: "Model", cls: "l", title: "Sort by name" },
      { key: "index", label: "Score", title: "The index score" },
      ...liveDims.map(d => ({ key: d.id, label: HEAD[d.id] || SHORT[d.id] || d.name, small: share(d), cls: "skill", title: `${d.name}: ${share(d)} of the score` })),
      { key: "coverage", label: "Data", title: "Share of the score that is measured, not estimated" },
    ];
    const arrow = key => key === sortKey ? (sortUp ? " &#9650;" : " &#9660;") : "";
    document.querySelector("#ranking thead").innerHTML = `<tr>${cols.map(c => {
      const sorted = c.key === sortKey;
      return `<th class="${c.cls || ""}${sorted ? " sorted" : ""}"${sorted ? ` aria-sort="${sortUp ? "ascending" : "descending"}"` : ""} title="${esc(c.title)}">` +
        `<button type="button" class="sort" data-key="${c.key}">${esc(c.label)}${arrow(c.key)}${c.small ? `<small>${c.small}</small>` : ""}</button></th>`;
    }).join("")}</tr>`;
    const note = document.getElementById("sort-note");
    const col = cols.find(c => c.key === sortKey);
    note.hidden = !col;
    if (col) {
      const order = sortKey === "name" ? (sortUp ? "A to Z" : "Z to A") : sortUp ? "lowest first" : "highest first";
      note.innerHTML = `Sorted by <b>${esc(col.key === "name" ? "name" : liveDims.find(d => d.id === col.key)?.name || col.label)}</b>, ${order}. ` +
        `Click the heading again to reverse it, or <b>#</b> to go back to the overall ranking.`;
    }
  }

  // The lab menu lists the labs among the models the table can show right now.
  function renderLabs() {
    const pool = data.models.filter(m => (m.ranked || showAll.checked) && m.org);
    const labs = [...new Set(pool.map(m => orgName(m.org)))].sort((a, b) => a.localeCompare(b));
    const keep = labs.includes(labSel.value) ? labSel.value : "";
    labSel.innerHTML = `<option value="">All labs</option>` + labs.map(l => `<option>${esc(l)}</option>`).join("");
    labSel.value = keep;
  }

  function sortValue(m, key) {
    if (key === "name") return m.name.toLowerCase();
    if (key === "index" || key === "coverage") return m[key];
    return skillValue(m, key)?.v;
  }

  // Ranked models only, or every model in score order: outdated and unranked ones then sit, greyed
  // out and flagged, where their score puts them instead of trailing after the last ranked model.
  // Then the chosen column order, the search box and the lab menu.
  function renderBody() {
    const pool = showAll.checked
      ? [...data.models].sort((a, b) => b.index - a.index)
      : data.models.filter(m => m.ranked);
    if (sortKey) {
      pool.sort((a, b) => {
        const x = sortValue(a, sortKey), y = sortValue(b, sortKey);
        if (x == null || y == null) return (x == null) - (y == null);
        return (x < y ? -1 : x > y ? 1 : 0) * (sortUp ? 1 : -1);
      });
    }
    const q = findBox.value.trim().toLowerCase(), lab = labSel.value;
    const models = pool.filter(m => (!lab || (m.org && orgName(m.org) === lab))
      && (!q || [m.name, m.model, m.title, m.org && orgName(m.org)].some(s => s && s.toLowerCase().includes(q))));
    const tbody = document.querySelector("#ranking tbody");
    tbody.innerHTML = models.length ? models.map(rowHtml).join("")
      : `<tr><td class="none" colspan="${liveDims.length + 4}">No models match. Clear the search or pick another lab.</td></tr>`;
    document.getElementById("shown-n").textContent = q || lab ? `${models.length} of ${pool.length} shown` : "";
    tbody.querySelectorAll("a.toggle").forEach(a => a.addEventListener("click", e => { e.preventDefault(); toggle(a); }));
    tbody.querySelectorAll("input.pick").forEach(box => box.addEventListener("change", () => pick(box)));
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
    const span = rankSpan(m), pm = plusMinus(m);
    return `<tr class="${cls}" data-model="${esc(m.model)}">
      <td class="rank">${m.rank ?? "-"}${movement(m)}${span ? `<small title="Could rank anywhere from ${span} if estimates are off by their typical amount">${span}</small>` : ""}</td>
      <td class="l who"><div class="who-in"><input type="checkbox" class="pick" title="Tick to compare, up to ${MAX_COMPARE} models" aria-label="Compare ${esc(m.name)}"${picked.has(m.model) ? " checked" : ""}><a href="#" class="toggle" aria-expanded="false" aria-label="Show details for ${esc(m.name)}">[+]</a>${iconSvg(m, 24)}<div>
        <span class="name" title="${esc(verdict(m))}">${esc(m.name)}</span>${isNew(m) ? `<span class="new-badge" title="Released ${fmtDate(m.released)}">NEW</span>` : ""}${flag ? `<span class="flag">${flag}</span>` : ""}
        <span class="title">${esc(m.title)}</span><span class="org">${esc(sub)}</span></div></div></td>
      <td class="score-cell"><span class="score">${m.index.toFixed(1)}</span>${pm
        ? `<small class="pm" title="Part of this score is estimated; estimates like these are typically off by this much">${pm.trim()}</small>` : ""}</td>
      ${cells}
      <td>${m.coverage}%</td>
    </tr>`;
  }

  // Up or down since the last ranking, or "new" for a model that wasn't ranked then.
  function movement(m) {
    if (!m.rank || !since) return "";
    const was = wasRank[m.model];
    if (was == null) return `<span class="mv new" title="Not ranked on ${fmtDate(since)}">new</span>`;
    if (was === m.rank) return "";
    const up = was > m.rank;
    return `<span class="mv ${up ? "up" : "down"}" title="Was #${was} on ${fmtDate(since)}">${up ? "&#9650;" : "&#9660;"}${Math.abs(was - m.rank)}</span>`;
  }

  function loadPicks() {
    try { return JSON.parse(localStorage.getItem("wi-compare") || "[]"); } catch (e) { return []; }
  }

  function pick(box) {
    const id = box.closest("tr").dataset.model;
    if (box.checked && picked.size >= MAX_COMPARE) {
      box.checked = false;
      document.getElementById("compare").querySelector(".compare-full")?.removeAttribute("hidden");
      return;
    }
    if (box.checked) picked.add(id); else picked.delete(id);
    try { localStorage.setItem("wi-compare", JSON.stringify([...picked])); } catch (e) { /* no storage: picks last until reload */ }
    renderCompare();
  }

  // The ticked models side by side, skill by skill, with the best in each row marked.
  function renderCompare() {
    const box = document.getElementById("compare");
    const models = [...picked].map(id => data.models.find(m => m.model === id)).filter(Boolean);
    box.hidden = !models.length;
    if (!models.length) { box.innerHTML = ""; return; }
    const line = (label, cells, best = true) => {
      const vals = cells.map(c => c && c.v);
      const top = best && vals.filter(v => v != null).length > 1 ? Math.max(...vals.filter(v => v != null)) : null;
      return `<tr><td class="l">${label}</td>${cells.map(c => !c ? `<td class="est">n/a</td>`
        : `<td class="${top != null && c.v === top ? "best" : ""}${c.est ? " est" : ""}">${c.text}</td>`).join("")}</tr>`;
    };
    const skill = (m, id) => { const s = skillValue(m, id); return s && { v: s.v, est: s.est, text: `${s.v.toFixed(0)}${s.est ? "*" : ""}` }; };
    const price = m => { const c = costOf(m); return c && { v: null, text: dollars(c[1].score) }; };
    box.innerHTML = `<h3>Compare <span>${models.length < 2 ? "tick another model in the table" : `${models.length} of ${MAX_COMPARE}`} &middot; <a href="#" class="compare-clear">clear</a></span></h3>
      <p class="compare-full" hidden>${MAX_COMPARE} at most: untick one first.</p>
      <table><tr><th class="l">Skill</th>${models.map(m => `<th>${iconSvg(m, 16)} ${esc(m.name)}</th>`).join("")}</tr>
      ${line("<b>Score</b>", models.map(m => ({ v: m.index, text: `<b>${m.index.toFixed(1)}</b>` })))}
      ${liveDims.map(d => line(esc(d.name), models.map(m => skill(m, d.id)))).join("")}
      ${line("Cost of the eval run", models.map(price), false)}
      ${line("Measured", models.map(m => ({ v: null, text: `${m.coverage}%` })), false)}</table>`;
    box.querySelector(".compare-clear").addEventListener("click", e => {
      e.preventDefault();
      picked.clear();
      try { localStorage.removeItem("wi-compare"); } catch (err) { /* nothing stored */ }
      document.querySelectorAll("#ranking input.pick").forEach(b => { b.checked = false; });
      renderCompare();
    });
  }

  function toggle(a) {
    const tr = a.closest("tr");
    const next = tr.nextElementSibling;
    if (next && next.classList.contains("details")) {
      next.remove();
      a.textContent = "[+]";
      a.setAttribute("aria-expanded", "false");
      if (location.hash === `#model=${encodeURIComponent(tr.dataset.model)}`) history.replaceState(null, "", location.pathname + location.search);
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
        const notes = (r.notes || []).map(n => `<span class="${/contamination|disagrees/.test(n) ? "warn" : ""}">${linkify(n)}</span>`).join("<br>");
        const bench = benchUrl[id] ? `<a href="${esc(benchUrl[id])}">${esc(benchName[id] || id)}</a>` : esc(benchName[id] || id);
        return `<tr>${i ? "" : head}<td>${bench}</td><td class="res"><b>${val}</b>${ci}</td><td class="raw">${esc(r.model_raw)}${effort}</td><td class="notes">${notes}</td></tr>`;
      }).join("");
    }).join("");
    const detail = document.createElement("tr");
    detail.className = "details";
    const span = rankSpan(m);
    const range = m.margin >= 0.5
      ? ` If its estimated skills are off by as much as estimates typically are, its score would be anywhere from ${(m.index - m.margin).toFixed(1)} to ${(m.index + m.margin).toFixed(1)}${span ? `, ranking it ${span}` : ""}.`
      : "";
    const released = m.released ? `<p>Released ${fmtDate(m.released)}. ${m.coverage}% of this score is measured.${range}</p>` : "";
    const hash = `#model=${encodeURIComponent(m.model)}`;
    const link = new URL(hash, location.href).href;
    detail.innerHTML = `<td colspan="${liveDims.length + 4}"><div class="details-in">
      <p class="share-line">Link to this model: <a href="${esc(hash)}">${esc(link.replace(/^https?:\/\//, ""))}</a> <a href="#" class="copy">copy link</a></p>
      <div class="seal">${iconSvg(m, 64)}<span>${esc(m.title)}</span></div><p class="verdict"><b>Verdict:</b> ${esc(verdict(m))}</p>${aboutHtml(m.about)}${released}
      <table class="receipts"><tr><th>Skill</th><th>Benchmark</th><th>Result</th><th class="raw">Listed as</th><th class="notes">Notes</th></tr>${rows}</table></div></td>`;
    detail.querySelector("a.copy").addEventListener("click", e => {
      e.preventDefault();
      const copy = e.target;
      navigator.clipboard?.writeText(link).then(() => {
        copy.textContent = "link copied";
        setTimeout(() => { copy.textContent = "copy link"; }, 1500);
      }, () => { /* the link itself is still there to copy by hand */ });
    });
    tr.after(detail);
    a.textContent = "[-]";
    a.setAttribute("aria-expanded", "true");
    history.replaceState(null, "", hash);
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
      return `<li><span>${worst.dimensions[id].toFixed(0)}</span><b>${label}:</b> ${esc(worst.name)}</li>`;
    }).join("");
  }

  function renderSidebar() {
    renderShame();
    const maxW = Math.max(...liveDims.map(d => d.weight));
    document.getElementById("weights").innerHTML = liveDims.map(d =>
      `<tr><td>${esc(SHORT[d.id] || d.name)}</td><td class="wbar"><i style="width:${(100 * d.weight / maxW).toFixed(0)}%"></i></td><td>${share(d)}</td></tr>`
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
      .map(m => `<li><span>${m.index.toFixed(1)}</span>${iconSvg(m, 16)} ${esc(m.name)}</li>`).join("");
  }
})();
