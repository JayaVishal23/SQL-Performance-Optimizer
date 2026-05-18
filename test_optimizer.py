import sys
sys.path.insert(0, ".")
from nodes.profiler import profiler_node
from nodes.schema_extractor import schema_extractor_node
from nodes.optimizer import optimizer_node

test_queries = [
    "SELECT * FROM orders WHERE order_status = 'pending'",
    "SELECT * FROM users WHERE email LIKE '%gmail.com'",
    "SELECT u.name, COUNT(*) FROM users u, orders o WHERE u.id = o.user_id GROUP BY u.name",
    "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE created_at > '2024-01-01')",
    "SELECT o.* FROM orders o WHERE EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.id AND oi.quantity > 3)",
]

for q in test_queries:
    print(f"\n{'='*70}")
    print(f"ORIGINAL: {q}")
    state = {
        "original_query": q, "explain_plan": "", "schema_info": "",
        "optimized_query": "", "time_before": 0.0, "time_after": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    state.update(profiler_node(state))
    state.update(schema_extractor_node(state))
    result = optimizer_node(state)
    print(f"OPTIMIZED: {result['optimized_query']}")
    if result['error_message']:
        print(f"ERROR: {result['error_message']}")