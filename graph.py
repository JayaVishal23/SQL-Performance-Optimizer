from langgraph.graph import StateGraph, END
from state import AgentState
from nodes.profiler import profiler_node
from nodes.schema_extractor import schema_extractor_node
from nodes.optimizer import optimizer_node
from nodes.semantic_validator import semantic_validator_node
from nodes.performance_validator import performance_validator_node
from nodes.fallback import fallback_node

MAX_ITERATIONS = 1

def route_after_semantic(state: AgentState) -> str:
    if state["status"] == "semantically_valid":
        return "performance_validator"
    elif state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return "fallback"
    else:
        return "optimizer"

def route_after_performance(state: AgentState) -> str:
    if state["status"] == "success":
        return "end"
    elif state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return "fallback"
    else:
        return "optimizer"

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("profiler", profiler_node)
    workflow.add_node("schema_extractor", schema_extractor_node)
    workflow.add_node("optimizer", optimizer_node)
    workflow.add_node("semantic_validator", semantic_validator_node)
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
            "performance_validator": "performance_validator",
            "optimizer": "optimizer",
            "fallback": "fallback"
        }
    )
    
    workflow.add_conditional_edges(
        "performance_validator",
        route_after_performance,
        {
            "end": END,
            "optimizer": "optimizer",
            "fallback": "fallback"
        }
    )
    
    workflow.add_edge("fallback", END)
    
    return workflow.compile()

if __name__ == "__main__":
    agent = build_graph()
    
    initial_state = {
        "original_query": "SELECT * FROM orders WHERE order_status = 'pending'",
        "explain_plan": "", "schema_info": "", "optimized_query": "",
        "time_before": 0.0, "time_after": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    
    final = agent.invoke(initial_state)
    
    print(f"\n{'='*60}")
    print(f"ORIGINAL: {final['original_query']}")
    print(f"OPTIMIZED: {final['optimized_query']}")
    print(f"TIME BEFORE: {final['time_before']:.2f} ms")
    print(f"TIME AFTER: {final['time_after']:.2f} ms")
    if final['time_before'] > 0:
        improvement = ((final['time_before'] - final['time_after']) / final['time_before']) * 100
        print(f"IMPROVEMENT: {improvement:.1f}%")
    print(f"STATUS: {final['status']}")
    print(f"ITERATIONS: {final['iteration_count']}")