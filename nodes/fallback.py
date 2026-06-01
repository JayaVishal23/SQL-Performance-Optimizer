from state import AgentState

def fallback_node(state: AgentState) -> dict:
    return {
        "optimized_query": state["original_query"],
        "suggested_indexes": [],
        "time_after_rewrite": state["time_before"],
        "time_after_index": state["time_before"],
        "time_after_both": state["time_before"],
        "best_time": state["time_before"],
        "final_recommendation": "NONE",
        "status": "fallback",
        "error_message": f"Could not optimize after {state['iteration_count']} iterations."
    }