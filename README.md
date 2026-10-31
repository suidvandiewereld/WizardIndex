# WizardIndex

A software-engineering benchmark index built only from **official, reproducible leaderboards**,
published to GitHub Pages and refreshed weekly.

Background and benchmark selection: [docs/benchmark-research.md](docs/benchmark-research.md).

## How it works

```
config/index.yaml        dimensions, weights, and the benchmarks behind each
wizardindex/sources/     one ingestor per leaderboard
data/results/*.json      fetched results (committed, so every published score is auditable)
data/manual/*.yaml       results transcribed by hand from papers without an API
data/aliases.yaml        fixes for model names that don't match across leaderboards
site/                    the static page; reads site/data/index.json
```

Live sources today:

- Direct from the official leaderboard: SWE-rebench, DeepSWE, Terminal-Bench, ARC-AGI-2, ARC-AGI-3,
  SimpleBench.
- Via [Epoch AI's benchmarking hub](https://epoch.ai/benchmarks) (CC BY 4.0): FrontierSWE,
  CursorBench, FrontierCode, MirrorCode, FrontierMath, WeirdML v3, furniture assembly,
  Blueprint-Bench 2, ALE-Bench, WebDev Arena, Chess Puzzles, Mystery Game Puzzles, EBR-bench.
- From [Design Arena](https://www.designarena.ai/leaderboard) (blind human votes): websites, UI
  components, data visualization, 3D scenes, game dev.
- Run by [Artificial Analysis](https://artificialanalysis.ai) on their own harness: Terminal-Bench 4.0,
  Humanity's Last Exam, SciCode, AA-Omniscience, and FrontierCode (only for models missing from
  Cognition's official board). Their Intelligence Index is never used.

Architecture, code cleanliness and instruction following have no current published data yet;
they appear on the site as "no published data yet" and are left out of the weights until they do.
Where a model hasn't been tested in a live dimension, the score is estimated and shown as
estimated on the site: from a relative that was tested there (same product line or variant group
in `config/families.yaml`) when there is one, otherwise from its standing on the other dimensions
(see `wizardindex/scoring.py`).

Price counts as a dimension too (Thrift, `skill: false` in `config/index.yaml`): the dollars
Artificial Analysis spent running its evaluation suite on the model, at the model's
second-highest reasoning setting (see `_price_setting` in `wizardindex/sources/artificial_analysis.py`),
scaled by square root so cheaper scores higher. It is never used to estimate a model's missing skills.
Where a lab's subscription is subsidised, the cost is divided by how many dollars of API usage a
subscription dollar buys on its largest plan (`data/subscriptions.yaml`, from SemiAnalysis's
measurements; applied at build time by `wizardindex/subsidies.py`).

## Model picker

"Which model for my job?" on the rankings page is driven by `config/tasks.yaml`: each job weights
the skills it needs and names the benchmarks that look like it, and each bar sets the fit a model
needs. The picker recommends the cheapest model that clears the bar and marks the rest as step-ups,
overkill (a cheaper model does the job as well) or not enough.

## History page

`site/history.html` follows each product line (Opus, Sonnet, GPT, Gemini, ...) across generations.
Lines are defined by regexes in `config/families.yaml`, which also lists the long-running
benchmarks shown as raw scores. Generations with under 40% of their score measured are listed
but not charted.

## Model descriptions

`data/descriptions.yaml` holds a short summary of what users and independent reviewers say
about each ranked model, with sources and an evidence rating (solid / mixed / thin). Unlike the
scores, these are researched by hand and are not refreshed by the weekly job; update `as_of`
when you revise them.

## Run locally

```bash
uv venv && uv pip install -e .
uv run wizardindex fetch      # pull leaderboards into data/results/
uv run wizardindex build      # compute site/data/index.json
python -m http.server -d site 8000
```

## Adding results by hand

For benchmarks with no machine-readable leaderboard, create `data/manual/<benchmark id>.yaml`
(see the format in `wizardindex/sources/manual.py`), then run `fetch` and `build`.

## Deploying

`.github/workflows/pages.yml` fetches every Monday, commits the refreshed data, and deploys `site/`.
In the repository settings, set **Pages → Source** to **GitHub Actions** once.
