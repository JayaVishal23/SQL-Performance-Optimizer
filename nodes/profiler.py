import psycopg2
import re
import os
import statistics
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def parse_execution_time(explain_text: str) -> float:
    """
    Parses the 'Execution Time: X ms' line from EXPLAIN ANALYZE output.
    Returns time in milliseconds. Returns -1 if not found.
    """
    match = re.search(r"Execution Time:\s*([\d.]+)\s*ms", explain_text)
    if match:
        return float(match.group(1))
    return -1.0

def run_explain_analyze(cursor, query: str) -> tuple[str, float]:
    """
    Runs EXPLAIN (ANALYZE, BUFFERS) on the query and returns (plan_text, execution_time_ms).
    """
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"
    cursor.execute(explain_query)
    rows = cursor.fetchall()
    plan_text = "\n".join([row[0] for row in rows])
    exec_time = parse_execution_time(plan_text)
    return plan_text, exec_time

def profiler_node(state: AgentState) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = state["original_query"]
    
    times = []
    last_plan = ""
    for i in range(3):
        plan_text, exec_time = run_explain_analyze(cursor, query)
        if i > 0:  # discard first run
            times.append(exec_time)
        last_plan = plan_text
    
    median_time = statistics.median(times)
    
    cursor.close()
    conn.close()
    
    return {
        "explain_plan": last_plan,
        "time_before": median_time,
        "iteration_count": 0,
        "status": "running"
    }

if __name__ == "__main__":
    test_state = {
        "original_query": "SELECT * FROM orders WHERE order_status = 'pending'",
        "explain_plan": "", "schema_info": "", "optimized_query": "",
        "time_before": 0.0, "time_after": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    result = profiler_node(test_state)
    print(f"Execution time: {result['time_before']} ms")
    print(f"Plan:\n{result['explain_plan'][:500]}")