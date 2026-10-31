# WizardIndex — Benchmark Research (2026-10-28)

Goal: a software-engineering-centric index built only from benchmarks we can **re-run ourselves**
(open tasks + open harness), instead of trusting third-party aggregates.

Selection rules used below:
1. **Reproducible** — public tasks and a runnable harness (Docker preferred).
2. **Not saturated** — top models well below ceiling.
3. **Contamination-resistant** — fresh/rolling tasks, original tasks, or private holdout.
4. Avoid benchmarks with known integrity problems (e.g. **SWE-bench Verified**: OpenAI stopped
   reporting it in Feb 2026 over contamination and flawed tests).

---

## 1. Dimension → benchmark map

| # | Dimension | Primary (use now) | Secondary / supporting | Coverage |
|---|-----------|-------------------|------------------------|----------|
| 1 | Real-world SWE (core) | SWE-Bench Pro (with the *Pro Verified* fixes), SWE-rebench (monthly fresh), DeepSWE (113 original long-horizon tasks) | SWE-Lancer Diamond (502 Upwork tasks, $-weighted), Commit0 (build a library from scratch) | Strong |
| 2 | Agentic / terminal work | Terminal-Bench 2.0 (89 tasks, Harbor harness) | — | Strong |
| 3 | Modeling / spatial reasoning | VoxelCodeBench (Meta FAIR, open; code → 3D voxel scenes) | MUSE (manufacturable/assemblable text-to-CAD), Op-CAD (ICML 2026), Text-to-CadQuery, FloorplanQA | Medium |
| 4 | Overall reasoning | LiveCodeBench Pro (competitive programming, Elo, rolling) | ARC-AGI-2 | Strong |
| 5 | Adaptability to unknown environments | ARC-AGI-3 (interactive, no instructions; open Python toolkit) | EsoLang-Bench (Brainfuck/Befunge/etc.; frontier 0–11% vs 100% in Python), CodeGlance (unseen functions) | Strong |
| 6 | Architecture knowledge & capability | SWE-Lancer *managerial* tasks (choose between real implementation proposals) | OODEval (requirements → class diagrams), ENGDESIGN OS / computer-architecture subset | Thin (existing only) |
| 7 | Code cleanliness | Linters run over published patches from #1 (see §3) | ReviewBench (GitHub, 219 PRs / 19 langs), SWR-Bench, CR-Bench | Thin (existing only) |
| 8 | Instruction following | IFBench (58 novel verifiable constraints), AgentIF (707 instructions, ~1.7k-word agent prompts) | Our own "constraint compliance" checks inside SWE tasks | Medium |
| 9 | Intuition & creativity | NeoCoder (Codeforces + Denial Prompting, NeoGauge metric) | Action-efficiency from ARC-AGI-3 as an "intuition" proxy | Thin (existing only) |
| 10 | "Being a software engineer" | Composite of 1–9, plus code review (ReviewBench) and judgment (SWE-Lancer managerial) | — | Derived |

### Excluded / demoted
| Benchmark | Reason |
|-----------|--------|
| SWE-bench Verified | Contaminated; gold patches reproducible from memory. Deprecated by OpenAI. |
| Aider Polyglot | Near-saturated (~88–89%). |
| LiveCodeBench (original) | Near-saturated (~93%). Use LiveCodeBench **Pro** instead. |
| SnorkelSpatial | Top score 99%; also too narrow (2D grid). |
| CodeSmellEval | Its PSC metric reads **model logits** — unusable on closed API models. Borrow its 13 smell types only. |

---

## 2. Notes per primary benchmark

- **SWE-Bench Pro** (Scale AI) — 1,865 tasks, 41 repos, copyleft + held-out + private commercial
  split. The Sept 2026 *Pro Verified* paper (arXiv 2609.08149) found reward-hacking channels and
  bad tasks that inflate scores; adopt its safeguards and corrected instances.
- **SWE-rebench** (Nebius) — new GitHub issue/PR tasks every month; 860 curated Python tasks with
  prebuilt Docker images on the Harbor hub. Only score models on months **after** their release.
- **DeepSWE** (Datacurve, arXiv 2607.07946) — 113 tasks written from scratch, 91 repos, 5 languages,
  behavior-based verifiers, short prompts (agent must locate the change itself). Runs on
  mini-swe-agent.
- **Terminal-Bench 2.0** — 89 hand-verified terminal tasks. Official harness is Harbor:
  `harbor run -d terminal-bench/terminal-bench-2 -a <agent> -m <model> -k 5`.
- **SWE-Lancer Diamond** (OpenAI, MIT) — public split of freelance tasks with dollar values; includes
  manager-style proposal selection. Warning: open harness ≠ OpenAI's internal one, so our numbers
  won't match the paper's — fine as long as we're internally consistent.
- **Commit0** — 54 Python libraries implemented from spec + tests. The only greenfield benchmark here.
- **VoxelCodeBench** — the clearest open spatial benchmark; finds that runnable code ≠ spatially
  correct output. Repo: `facebookresearch/voxelcodebench`.
- **ARC-AGI-3** — hundreds of turn-based game environments with no rules given; scored by action
  efficiency vs humans (frontier ≈ 0.3%, humans 100%). Open toolkit for local runs.
- **EsoLang-Bench** — same 80 problems as in Python/JS, but in esoteric languages. Clean measure of
  learning an unfamiliar environment vs. recalling training data.
- **IFBench / AgentIF** — IFBench for precise novel constraints; AgentIF for long, dense agent
  system prompts and tool specs (closest to how coding agents are actually instructed).
- **NeoCoder** — 199 Codeforces problems with 30 human solutions each; Denial Prompting forbids
  previously used techniques and NeoGauge scores correct + novel solutions.

---

## 3. Budget mode: no benchmark production

Constraint: we do **not** author tasks or build test suites. Everything comes from existing
benchmarks, and we run as little ourselves as possible.

### Filling the gaps with existing benchmarks only
| Dimension | Use instead of building |
|-----------|-------------------------|
| Architecture | SWE-Lancer Diamond **managerial** split (pick the right proposal; cheap, no code execution) + OODEval + ENGDESIGN's open OS / computer-architecture tasks |
| Code cleanliness | ReviewBench (finding problems in PRs) + free static analysis on **already-published** trajectories (see below) |
| Instruction following | IFBench + AgentIF as-is |
| Creativity / intuition | NeoCoder as-is; ARC-AGI-3 action-efficiency score as the intuition proxy |
| Modeling / spatial | VoxelCodeBench + MUSE as-is |

### The cheap trick for code cleanliness
Terminal-Bench publishes verified trajectories, and SWE-rebench / DeepSWE publish results per
model. Download the patches models already produced and run free linters (ruff, pylint, radon,
semgrep) over them. Zero inference cost, zero task authoring — just a script.

### Don't run what's already published credibly
Three tiers, cheapest first:
1. **Ingest official leaderboards** from the benchmark maintainers (not aggregators): SWE-rebench,
   Terminal-Bench (audited, trajectories public), DeepSWE, LiveCodeBench Pro, ARC Prize, Ai2 IFBench.
   These run fixed harnesses themselves, which is exactly what we can't trust ArtificialAnalysis to do.
2. **Spot-check, don't fully reproduce.** For each model, re-run a small random sample
   (~20–30 tasks) of one or two suites. If our pass rate lands inside the published CI, trust the
   leaderboard; if not, flag the score. This is what keeps the index honest for a few dollars.
3. **Fully run only where nobody publishes results** (likely OODEval, NeoCoder, EsoLang-Bench,
   SWE-Lancer managerial) — these are small, non-agentic, and cheap: single prompts, no Docker loops.

## 4. Reproducibility protocol (for the spot-checks we do run)

- **One harness for agentic tasks** — Harbor (already hosts Terminal-Bench 2.0 and SWE-rebench) and
  mini-swe-agent as the fixed reference scaffold.
- **Pin everything** — task set version, Docker image digests, harness commit, model ID, temperature,
  reasoning-effort setting, token/time budgets.
- **Repeat runs** — ≥3 runs per sampled task (pass@1 mean ± 95% CI).
- **Contamination** — prefer rolling (SWE-rebench, LiveCodeBench Pro) and original (DeepSWE) tasks;
  only count SWE-rebench months after a model's release date.
- **Cost axis** — record $ per task; publish score-per-dollar alongside raw score.

## 5. Index scoring (draft)

Normalize each benchmark to 0–100 against a floor (weak baseline) and ceiling (human expert),
average within a dimension, then weight dimensions:

| Dimension | Weight |
|-----------|--------|
| Real-world SWE | 25% |
| Agentic / terminal | 10% |
| Architecture | 10% |
| Code cleanliness | 10% |
| Reasoning | 10% |
| Adaptability | 10% |
| Instruction following | 10% |
| Modeling / spatial | 8% |
| Creativity / intuition | 7% |

Architecture and creativity rest on thinner evidence than the rest; show their benchmark count
next to the score. After the first run, merge dimensions whose scores correlate > 0.9.

## 6. Open items

- Licenses not yet verified for: VoxelCodeBench, MUSE, Op-CAD, DeepSWE, ReviewBench, NeoCoder.
- Several scores above came from aggregator sites, not official leaderboards — verify before quoting.
- Decide model roster and the spot-check budget per model.
- Check which leaderboards expose per-task results / patches (needed for the cleanliness script).

## Sources

- [OpenAI — Why we no longer evaluate SWE-bench Verified](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)
- [SWE-Bench Pro leaderboard (Morph)](https://www.morphllm.com/swe-bench-pro)
- [SWE-Bench Pro Verified (arXiv 2609.08149)](https://arxiv.org/pdf/2609.08149)
- [SWE-rebench (Nebius)](https://nebius.com/blog/posts/introducing-swe-rebench) · [Harbor dataset](https://hub.harborframework.com/datasets/swe-rebench/swe-rebench-leaderboard/latest)
- [DeepSWE (arXiv 2607.07946)](https://arxiv.org/abs/2607.07946) · [leaderboard](https://deepswe.datacurve.ai/)
- [Terminal-Bench 2.0 dataset](https://huggingface.co/datasets/harborframework/terminal-bench-2.0/blob/main/README.md) · [tbench docs](https://tbench.ai/docs)
- [SWE-Lancer (OpenAI)](https://openai.com/index/swe-lancer/)
- [Commit0 (arXiv 2412.01769)](https://arxiv.org/pdf/2412.01769)
- [VoxelCodeBench (arXiv 2604.02580)](https://arxiv.org/abs/2604.02580) · [MUSE (arXiv 2605.28579)](https://arxiv.org/pdf/2605.28579) · [Op-CAD](https://proceedings.mlr.press/v306/bai26a.html) · [FloorplanQA](https://arxiv.org/abs/2507.07644v3) · [SnorkelSpatial](https://devweb26.snorkel.ai/blog/introducing-snorkelspatial/)
- [LiveCodeBench Pro](https://www.alphaxiv.org/benchmarks/university-of-washington/livecodebench-pro) · [Aider Polyglot (Epoch)](https://epoch.ai/benchmarks/aider-polyglot)
- [ARC-AGI-3 launch](https://arcprize.org/blog/arc-agi-3-launch) · [ARC docs](https://docs.arcprize.org/vocabulary)
- [EsoLang-Bench](https://www.alphaxiv.org/abs/2603.09678) · [Agents adapting to unfamiliar languages (arXiv 2606.10933)](https://arxiv.org/pdf/2606.10933)
- [OODEval (arXiv 2601.07602)](https://arxiv.org/pdf/2601.07602) · [ENGDESIGN (arXiv 2509.16204)](https://arxiv.org/pdf/2509.16204)
- [CodeSmellEval (arXiv 2412.18989)](https://arxiv.org/html/2412.18989v2)
- [ReviewBench (GitHub)](https://github.blog/ai-and-ml/reviewbench-an-open-benchmark-for-ai-code-review/) · [CR-Bench](https://arxiv.org/html/2603.11078v1) · [SWR-Bench](https://alphaxiv.org/benchmarks/northwestern-polytechnical-university/swr-bench)
- [IFBench (Ai2)](https://allenai.org/blog/ifbench-artificial-analysis) · [AgentIF (arXiv 2505.16944)](https://arxiv.org/html/2505.16944v1)
- [NeoCoder (arXiv 2407.09007)](https://arxiv.org/pdf/2407.09007)
