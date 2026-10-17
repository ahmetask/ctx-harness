"""Totals per arm from results.jsonl: python3 aggregate.py"""
import json, pathlib, statistics as st
rows = [json.loads(l) for l in open(pathlib.Path(__file__).resolve().parent / "results.jsonl")]
for mode in ("baseline", "harness"):
    rs = [r for r in rows if r["mode"] == mode]
    print(mode, f"runs={len(rs)} pass={sum(r['passed'] for r in rs)}",
          f"tokens={sum(r['tokens_total'] for r in rs)/1e6:.2f}M",
          f"median_tokens={st.median(r['tokens_total'] for r in rs)/1000:.1f}k",
          f"median_uncached={st.median(r['tokens_uncached'] for r in rs)/1000:.1f}k",
          f"steps={sum(r['steps'] for r in rs)}", f"cost=${sum(r['cost_usd'] or 0 for r in rs):.2f}")
