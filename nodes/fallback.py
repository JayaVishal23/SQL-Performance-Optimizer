from state import AgentState

def fallback_node(state: AgentState) -> dict:
    return {
        "optimized_query": state["original_query"],
        "time_after": state["time_before"],
        "status": "fallback",
        "error_message": f"Could not optimize after {state['iteration_count']} iterations."
    }