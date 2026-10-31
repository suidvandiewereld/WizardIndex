// Fills the header status box on every page from the same index data.
(async function () {
  const data = await (await fetch("data/index.json", { cache: "no-cache" })).json();
  const set = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
  const live = data.dimensions.flatMap(d => d.benchmarks).filter(b => b.n_results > 0);
  set("hs-ranked", data.models.filter(m => m.ranked).length);
  set("hs-bench", live.length);
  set("head-stamp", new Date(data.generated_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }));
})();
