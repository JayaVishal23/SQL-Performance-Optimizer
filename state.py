from typing import TypedDict, List

class AgentState(TypedDict):
    original_query: str
    
    explain_plan: str
    schema_info: str

    optimized_query: str
    suggested_indexes: List[str]
    
    time_before: float           # ms — original query baseline
    time_after_rewrite: float    # ms — after query rewrite only
    time_after_index: float      # ms — after applying suggested index (no rewrite)
    time_after_both: float       # ms — rewrite + index combined
    
    final_recommendation: str    # based on 4 things, normal, rewrite, index, both
    best_time: float             
    
    iteration_count: int
    error_message: str
    status: str                  # running , success , fallback , semantic_mismatch , execution_error