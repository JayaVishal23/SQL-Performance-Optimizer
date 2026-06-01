from langgraph.graph import StateGraph, END
from state import AgentState
from nodes.profiler import profiler_node
from nodes.schema_extractor import schema_extractor_node
from nodes.optimizer import optimizer_node
from nodes.semantic_validator import semantic_validator_node
from nodes.index_advisor import index_advisor_node
from nodes.performance_validator import performance_validator_node
from nodes.fallback import fallback_node

MAX_ITERATIONS = 3

def route_after_semantic(state: AgentState) -> str:
    """After semantic check: pass → index advisor. Fail → retry optimizer or fallback."""
    if state["status"] == "semantically_valid":
        return "index_advisor"
    elif state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return "fallback"
    else:
        return "optimizer"

def route_after_performance(state: AgentState) -> str:
    """After performance test: success → end. No improvement → retry or end."""
    if state["status"] == "success":
        return "end"
    if state["status"] == "no_improvement" and state.get("iteration_count", 0) < MAX_ITERATIONS:
        return "optimizer"
    return "end"

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("profiler", profiler_node)
    workflow.add_node("schema_extractor", schema_extractor_node)
    workflow.add_node("optimizer", optimizer_node)
    workflow.add_node("semantic_validator", semantic_validator_node)
    workflow.add_node("index_advisor", index_advisor_node)
    workflow.add_node("performance_validator", performance_validator_node)
    workflow.add_node("fallback", fallback_node)
    
    workflow.set_entry_point("profiler")
    workflow.add_edge("profiler", "schema_extractor")
    workflow.add_edge("schema_extractor", "optimizer")
    workflow.add_edge("optimizer", "semantic_validator")
    
    workflow.add_conditional_edges(
        "semantic_validator",
        route_after_semantic,
        {
            "index_advisor": "index_advisor",
            "optimizer": "optimizer",
            "fallback": "fallback"
        }
    )
    
    workflow.add_edge("index_advisor", "performance_validator")
    
    workflow.add_conditional_edges(
        "performance_validator",
        route_after_performance,
        {
            "end": END,
            "optimizer": "optimizer",
        }
    )
    
    workflow.add_edge("fallback", END)
    
    return workflow.compile()

if __name__ == "__main__":
    agent = build_graph()
    
    initial_state = {
        "original_query": "SELECT * FROM orders WHERE order_status = 'pending'",
        "explain_plan": "", "schema_info": "",
        "optimized_query": "", "suggested_indexes": [],
        "time_before": 0.0, "time_after_rewrite": 0.0,
        "time_after_index": 0.0, "time_after_both": 0.0,
        "final_recommendation": "", "best_time": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    
    final = agent.invoke(initial_state)
    
    print(f"\n{'='*70}")
    print(f"AGENT FINAL OUTPUT")
    print(f"{'='*70}")
    print(f"Original query:\n  {final['original_query']}\n")
    print(f"Baseline time: {final['time_before']:.2f} ms")
    print(f"\nRecommendation: {final['final_recommendation']}")
    print(f"Best time: {final['best_time']:.2f} ms")
    
    if final['time_before'] > 0:
        improvement = ((final['time_before'] - final['best_time']) / final['time_before']) * 100
        print(f"Improvement: {improvement:.1f}%")
    
    if final['final_recommendation'] in ("REWRITE_ONLY", "BOTH"):
        print(f"\nRewritten query:\n  {final['optimized_query']}")
    
    if final['final_recommendation'] in ("INDEX_ONLY", "BOTH"):
        print(f"\nSuggested indexes:")
        for idx in final['suggested_indexes']:
            print(f"  {idx}")
    
    if final['final_recommendation'] == "NONE":
        print("\nNo optimization improved performance. Query is already well-optimized.")