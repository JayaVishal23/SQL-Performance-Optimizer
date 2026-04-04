from typing import TypedDict

class AgentState(TypedDict):
    original_query: str # The slow query that user enters
    explain_plan: str # Total information about the original query, like Why its slow. By command EXPLAIN ANALYZE
    schema_info: str # Information of Database schema, like number of colums, what all rows present like that
    optimized_query: str # New Query that AI generated
    time_before: float # Time of execution by original query
    time_after: float # Time of execution by optimized_query
    iteration_count: int # number of time AI generated optimized query ( To prevent infinite loops)
    error_message: str # If AI query is wrong, then what went wrong
    status: str # running, success or failed


