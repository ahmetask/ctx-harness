import json,statistics as st
runs={'baseline':[], 'harness':[], 'maponly':[]}
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
def load(name):
    return [json.loads(l) for l in open(HERE / (name + '.jsonl'))]
for r in load('baseline-vs-harness'):
    if r['task']=='bootstrap': continue
    if r['task'].startswith('t1') and r['mode']=='harness' and r['repeat']==4 and not r['passed']:
        continue
    runs[r['mode']].append(r)
for r in load('rerun-t1-harness-r4'):
    if r['task']!='bootstrap': runs['harness'].append(r)
for r in load('map-only'):
    if r['task']!='bootstrap': runs['maponly'].append(r)
tasks=sorted({r['task'] for r in runs['baseline']})
def agg(rs):
    return dict(n=len(rs),p=sum(r['passed'] for r in rs),tok=st.median(r['tokens_total'] for r in rs),unc=st.median(r['tokens_uncached'] for r in rs),steps=st.median(r['steps'] for r in rs),sec=st.median(r['seconds'] for r in rs),cost=sum(r['cost_usd'] or 0 for r in rs),files=st.median(r['files_read'] for r in rs))
print("task | arm | pass | med tokens | uncached | steps | files | time | cost")
for t in tasks+['ALL']:
    for a in runs:
        rs=[r for r in runs[a] if t=='ALL' or r['task']==t]
        g=agg(rs); print(f"{t[:22]} | {a} | {g['p']}/{g['n']} | {g['tok']/1000:.1f}k | {g['unc']/1000:.1f}k | {g['steps']} | {g['files']} | {g['sec']:.0f}s | ${g['cost']:.2f}")
print({a:sum(r['tokens_total'] for r in runs[a]) for a in runs})
