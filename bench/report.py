#!/usr/bin/env python3
"""Summarize a benchmark run: python3 bench/report.py bench/results/<run>

Writes <run>/report.md and prints it. Correctness comes first: tokens are
only compared alongside pass rates, and 'tokens per pass' charges failed runs
to the mode that produced them.
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def load(run_dir: Path):
    rows = [json.loads(line) for line in (run_dir / "results.jsonl").read_text().splitlines() if line.strip()]
    meta = json.loads((run_dir / "run.json").read_text()) if (run_dir / "run.json").exists() else {}
    return meta, rows


def quartiles(xs):
    xs = sorted(xs)
    if not xs:
        return None, None, None
    if len(xs) == 1:
        return xs[0], xs[0], xs[0]
    q1, q2, q3 = statistics.quantiles(xs, n=4, method="inclusive")
    return q1, q2, q3


def k(n):
    """Compact token count: 12345 -> 12.3k."""
    if n is None:
        return "-"
    return f"{n / 1000:.1f}k" if abs(n) >= 1000 else f"{n:.0f}"


def summarize(rows):
    out = {}
    for r in rows:
        out.setdefault((r["task"], r["mode"]), []).append(r)
    stats = {}
    for key, rs in out.items():
        tokens = [r["tokens_total"] for r in rs if r.get("tokens_total") is not None]
        uncached = [r["tokens_uncached"] for r in rs if r.get("tokens_uncached") is not None]
        steps = [r["steps"] for r in rs if r.get("steps") is not None]
        costs = [r["cost_usd"] for r in rs if r.get("cost_usd") is not None]
        passes = sum(1 for r in rs if r["passed"])
        q1, med, q3 = quartiles(tokens)
        stats[key] = {
            "category": rs[0].get("category", ""), "runs": len(rs), "passes": passes,
            "pass_rate": passes / len(rs), "q1": q1, "median": med, "q3": q3,
            "median_uncached": statistics.median(uncached) if uncached else None,
            "median_steps": statistics.median(steps) if steps else None,
            "tokens_per_pass": (sum(tokens) / passes) if passes and tokens else None,
            "cost": sum(costs) if costs else None,
        }
    return stats


def render(meta, rows):
    stats = summarize(rows)
    work = [r for r in rows if r["mode"] != "bootstrap"]
    tasks = sorted({r["task"] for r in work})
    modes = [m for m in ("harness", "baseline") if any(r["mode"] == m for r in work)]
    L = [f"# Benchmark {meta.get('run', '')}", ""]
    L.append(f"Agent: {meta.get('agent', '?')}" + (f" (model {meta['model']})" if meta.get("model") else "")
             + f" · tasks: {len(tasks)} · repeats: {meta.get('repeats', '?')}"
             + f" · review gate: {'on' if meta.get('review_gate', True) else 'off'}")
    if meta.get("synthetic"):
        L += ["", "> Offline agent: token numbers are synthetic. This run checks the benchmark platform, "
                  "not the harness."]

    L += ["", "## Overall", "", "| mode | runs | pass rate | median tokens | median uncached | median steps "
                                "| tokens per pass | cost |", "|---|---|---|---|---|---|---|---|"]
    for m in modes:
        rs = [r for r in work if r["mode"] == m]
        tok = [r["tokens_total"] for r in rs if r.get("tokens_total") is not None]
        unc = [r["tokens_uncached"] for r in rs if r.get("tokens_uncached") is not None]
        st = [r["steps"] for r in rs if r.get("steps") is not None]
        costs = [r["cost_usd"] for r in rs if r.get("cost_usd") is not None]
        passes = sum(r["passed"] for r in rs)
        L.append(f"| {m} | {len(rs)} | {passes / len(rs):.0%} | {k(statistics.median(tok) if tok else None)} | "
                 f"{k(statistics.median(unc) if unc else None)} | {statistics.median(st) if st else '-'} | "
                 f"{k(sum(tok) / passes) if passes and tok else '-'} | "
                 f"{f'${sum(costs):.2f}' if costs else '-'} |")

    L += ["", "## Per task", "", "| task | category | mode | pass | median tokens (IQR) | uncached | steps "
                                 "| Δ tokens vs baseline |", "|---|---|---|---|---|---|---|---|"]
    deltas = {}
    for t in tasks:
        base = stats.get((t, "baseline"), {}).get("median")
        for m in modes:
            s = stats.get((t, m))
            if not s:
                continue
            delta = ""
            if m == "harness" and base and s["median"] is not None:
                deltas[t] = (s["median"] - base, (s["median"] - base) / base, s["category"])
                delta = f"{deltas[t][1]:+.0%}"
            iqr = f"{k(s['median'])} ({k(s['q1'])}–{k(s['q3'])})" if s["median"] is not None else "-"
            L.append(f"| {t} | {s['category']} | {m} | {s['passes']}/{s['runs']} | {iqr} | "
                     f"{k(s['median_uncached'])} | {s['median_steps'] if s['median_steps'] is not None else '-'} "
                     f"| {delta} |")

    cats = sorted({r["category"] for r in work})
    if len(modes) == 2:
        L += ["", "## By category", "", "| category | harness pass | baseline pass | median Δ tokens |",
              "|---|---|---|---|"]
        for c in cats:
            pr = {m: [r["passed"] for r in work if r["category"] == c and r["mode"] == m] for m in modes}
            ds = [d[1] for t, d in deltas.items() if d[2] == c]
            L.append(f"| {c} | {sum(pr['harness'])}/{len(pr['harness'])} | "
                     f"{sum(pr['baseline'])}/{len(pr['baseline'])} | "
                     f"{f'{statistics.median(ds):+.0%}' if ds else '-'} |")

    boot = [r for r in rows if r["mode"] == "bootstrap"]
    if boot or meta.get("ctx_from"):
        L += ["", "## Harness overhead", ""]
        if boot:
            b = boot[0]
            cost = f", ${b['cost_usd']:.2f}" if b.get("cost_usd") is not None else ""
            L.append(f"- Bootstrap (`/ctx-harness:build`, once per repo): {k(b.get('tokens_total'))} tokens{cost}, "
                     f"{b['seconds']:.0f}s.")
            if deltas:
                saving = -statistics.mean(d[0] for d in deltas.values())
                if saving > 0 and b.get("tokens_total"):
                    L.append(f"- Mean saving per task (paired medians): {k(saving)} tokens; "
                             f"break-even after ~{b['tokens_total'] / saving:.1f} tasks.")
                else:
                    L.append("- No net token saving on these tasks: the harness does not pay for its bootstrap here.")
        else:
            L.append(f"- Reused context from `{meta['ctx_from']}`; bootstrap cost not measured in this run.")

    failed = [r for r in work if not r["passed"]]
    if failed:
        L += ["", "## Failed runs", ""]
        for r in failed:
            first = (r.get("check") or r.get("error") or "").strip().splitlines()[:1]
            L.append(f"- {r['task']} · {r['mode']} · r{r['repeat']}: {first[0] if first else 'no detail'}")
    missing = [r for r in work if not r.get("transcript_ok")]
    if missing:
        L += ["", f"Note: {len(missing)} runs had no readable transcript usage; their tokens are excluded."]
    return "\n".join(L) + "\n"


def write(run_dir) -> str:
    run_dir = Path(run_dir)
    meta, rows = load(run_dir)
    text = render(meta, rows)
    (run_dir / "report.md").write_text(text)
    return text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(write(sys.argv[1]))
