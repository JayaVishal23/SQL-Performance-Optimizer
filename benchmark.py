import csv
import time
from graph import build_graph
from test_queries import ALL_QUERIES

agent = build_graph()
results = []

start_total = time.time()

for i, (query, category) in enumerate(ALL_QUERIES):
    print(f"\n[{i+1}/{len(ALL_QUERIES)}] {category}: {query[:80]}...")
    
    state = {
        "original_query": query, "explain_plan": "", "schema_info": "",
        "optimized_query": "", "time_before": 0.0, "time_after": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    
    query_start = time.time()
    try:
        final = agent.invoke(state)
        wall_time = time.time() - query_start
        
        improvement = 0
        if final['time_before'] > 0 and final['time_after'] > 0:
            improvement = ((final['time_before'] - final['time_after']) / final['time_before']) * 100
        
        results.append({
            "query": query,
            "category": category,
            "time_before_ms": round(final['time_before'], 2),
            "time_after_ms": round(final['time_after'], 2),
            "improvement_pct": round(improvement, 2),
            "iterations": final['iteration_count'],
            "status": final['status'],
            "agent_wall_time_sec": round(wall_time, 2),
        })
        print(f"   → {improvement:.1f}% improvement, {final['iteration_count']} iterations, {wall_time:.1f}s wall time")
    except Exception as e:
        results.append({
            "query": query, "category": category,
            "time_before_ms": -1, "time_after_ms": -1,
            "improvement_pct": 0, "iterations": 0,
            "status": f"crashed", "agent_wall_time_sec": 0,
        })
        print(f"   → CRASHED: {str(e)[:100]}")

with open("benchmark_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\n{'='*70}")
print(f"BENCHMARK SUMMARY")
print(f"{'='*70}")

successful = [r for r in results if r['status'] == 'success']
fallback = [r for r in results if r['status'] == 'fallback']
crashed = [r for r in results if 'crashed' in r['status'] or 'error' in r['status']]

print(f"Total queries: {len(results)}")
print(f"Successful optimizations: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
print(f"Fallback (gave up): {len(fallback)}")
print(f"Crashed: {len(crashed)}")
print(f"Total wall time: {(time.time()-start_total)/60:.1f} minutes")

if successful:
    improvements = [r['improvement_pct'] for r in successful]
    print(f"\nAvg improvement (successful): {sum(improvements)/len(improvements):.1f}%")
    print(f"Median improvement (successful): {sorted(improvements)[len(improvements)//2]:.1f}%")
    
    by_cat = {}
    for r in successful:
        by_cat.setdefault(r['category'], []).append(r['improvement_pct'])
    for cat, imps in by_cat.items():
        print(f"  {cat}: {sum(imps)/len(imps):.1f}% avg across {len(imps)} queries")
    
    iter_avg = sum(r['iterations'] for r in successful) / len(successful)
    print(f"\nAvg iterations to succeed: {iter_avg:.2f}")