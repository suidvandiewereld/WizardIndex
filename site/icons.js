// Draws a model's pixel icon (64 digits from index.json, see wizardindex/flair.py) as crisp SVG:
// 1 is the maker's color, 2 a dark shade of it, 3 gold, 0 empty.
(function () {
  const COLORS = {
    anthropic: "#b4532a", openai: "#1d6b57", google: "#2a5db0", "google deepmind": "#2a5db0",
    meta: "#3b5998", "meta ai": "#3b5998", moonshot: "#5b3f8f", kimi: "#5b3f8f", deepseek: "#2f6f9f",
    xai: "#4a4a4a", "z.ai (zhipu ai)": "#1f7a7a", alibaba: "#c0631c", "mistral ai": "#c4441b",
    minimax: "#9c2d5a", xiaomi: "#d0601a", nvidia: "#5a8a1a", stepfun: "#6a5a2a", upstage: "#7a4fb0",
    "institute of foundation models": "#2c6e8f", reflection: "#3f6fb0", "thinking machines": "#555577",
    inclusionai: "#2f8a6a",
  };
  const shade = hex => "#" + [1, 3, 5].map(i => Math.round(parseInt(hex.slice(i, i + 2), 16) * 0.55).toString(16).padStart(2, "0")).join("");

  // Sizes that are multiples of 8 keep every pixel square and sharp.
  window.iconSvg = function (m, size = 24) {
    if (!m.pixels) return "";
    const main = COLORS[m.org] || "#2a2d6b";
    const fill = { 1: main, 2: shade(main), 3: "#d4a12a" };
    let rects = "";
    for (let i = 0; i < 64; i++) {
      const v = m.pixels[i];
      if (v !== "0") rects += `<rect x="${i % 8}" y="${Math.floor(i / 8)}" width="1" height="1" fill="${fill[v]}"/>`;
    }
    return `<svg class="pixicon" width="${size}" height="${size}" viewBox="0 0 8 8" shape-rendering="crispEdges" aria-hidden="true">${rects}</svg>`;
  };
})();
