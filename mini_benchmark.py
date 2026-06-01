from graph import build_graph

agent = build_graph()
test_queries = [
    "SELECT * FROM orders WHERE order_status = 'pending'",
    "SELECT * FROM users WHERE email LIKE '%gmail.com'",
    "SELECT u.name, COUNT(*) FROM users u, orders o WHERE u.id = o.user_id GROUP BY u.name",
    "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE created_at > '2024-01-01')",
    "SELECT * FROM order_items WHERE quantity > 4",
]

for q in test_queries:
    print(f"\nQuery: {q}")
    state = {
        "original_query": q, "explain_plan": "", "schema_info": "",
        "optimized_query": "", "suggested_indexes": [],
        "time_before": 0.0, "time_after_rewrite": 0.0,
        "time_after_index": 0.0, "time_after_both": 0.0,
        "final_recommendation": "", "best_time": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    final = agent.invoke(state)
    print(f"  Recommendation: {final['final_recommendation']}")
    print(f"  {final['time_before']:.0f}ms → {final['best_time']:.0f}ms")