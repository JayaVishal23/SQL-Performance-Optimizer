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
        "optimized_query": "", "suggested_indexes": [],
        "time_before": 0.0, "time_after_rewrite": 0.0,
        "time_after_index": 0.0, "time_after_both": 0.0,
        "final_recommendation": "", "best_time": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    
    query_start = time.time()
    try:
        final = agent.invoke(state)
        wall_time = time.time() - query_start
        
        improvement = 0
        if final['time_before'] > 0 and final['best_time'] > 0:
            improvement = ((final['time_before'] - final['best_time']) / final['time_before']) * 100
        
        results.append({
            "query": query,
            "category": category,
            "time_before_ms": round(final['time_before'], 2),
            "time_after_rewrite_ms": round(final['time_after_rewrite'], 2),
            "time_after_index_ms": round(final['time_after_index'], 2),
            "time_after_both_ms": round(final['time_after_both'], 2),
            "best_time_ms": round(final['best_time'], 2),
            "improvement_pct": round(improvement, 2),
            "recommendation": final['final_recommendation'],
            "num_indexes_suggested": len(final.get('suggested_indexes', [])),
            "iterations": final['iteration_count'],
            "status": final['status'],
            "wall_time_sec": round(wall_time, 2),
        })
        print(f"   → {final['final_recommendation']}: {improvement:.1f}% improvement, {wall_time:.1f}s wall time")
    except Exception as e:
        results.append({
            "query": query, "category": category,
            "time_before_ms": -1, "time_after_rewrite_ms": -1,
            "time_after_index_ms": -1, "time_after_both_ms": -1,
            "best_time_ms": -1, "improvement_pct": 0,
            "recommendation": "CRASHED", "num_indexes_suggested": 0,
            "iterations": 0, "status": "crashed", "wall_time_sec": 0,
        })
        print(f"   → CRASHED: {str(e)[:100]}")

with open("benchmark_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\n{'='*70}")
print(f"BENCHMARK SUMMARY")
print(f"{'='*70}")

improved = [r for r in results if r['improvement_pct'] > 5]
no_improvement = [r for r in results if r['recommendation'] == 'NONE' and r['status'] != 'crashed']
crashed = [r for r in results if r['status'] == 'crashed']

print(f"Total queries: {len(results)}")
print(f"Improved (>5%): {len(improved)} ({len(improved)/len(results)*100:.1f}%)")
print(f"No improvement found: {len(no_improvement)}")
print(f"Crashed: {len(crashed)}")
print(f"Total wall time: {(time.time()-start_total)/60:.1f} minutes")

from collections import Counter
rec_counts = Counter(r['recommendation'] for r in results)
print(f"\nRecommendation breakdown:")
for rec, count in rec_counts.most_common():
    matching = [r for r in results if r['recommendation'] == rec and r['improvement_pct'] > 0]
    if matching:
        avg_imp = sum(r['improvement_pct'] for r in matching) / len(matching)
        print(f"  {rec}: {count} queries, avg {avg_imp:.1f}% improvement")
    else:
        print(f"  {rec}: {count} queries")

print(f"\nBy query category:")
for cat in ["INDEX", "STRUCTURAL"]:
    cat_results = [r for r in improved if r['category'] == cat]
    if cat_results:
        avg = sum(r['improvement_pct'] for r in cat_results) / len(cat_results)
        print(f"  {cat}: {len(cat_results)} improved, avg {avg:.1f}% improvement")

if improved:
    improvements = [r['improvement_pct'] for r in improved]
    print(f"\nOverall (improved queries):")
    print(f"  Avg improvement: {sum(improvements)/len(improvements):.1f}%")
    print(f"  Median improvement: {sorted(improvements)[len(improvements)//2]:.1f}%")
    print(f"  Max improvement: {max(improvements):.1f}%")