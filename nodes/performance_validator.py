import os
import psycopg2
import statistics
from dotenv import load_dotenv
from state import AgentState
from nodes.profiler import parse_execution_time

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def performance_validator_node(state: AgentState) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    optimized = state["optimized_query"]
    
    try:
        cursor.execute("BEGIN")
        
        times = []
        for i in range(3):
            cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS) {optimized}")
            rows = cursor.fetchall()
            plan = "\n".join([r[0] for r in rows])
            t = parse_execution_time(plan)
            if i > 0:
                times.append(t)
        
        cursor.execute("ROLLBACK")
        cursor.close()
        conn.close()
        
        median_time = statistics.median(times)
        time_before = state["time_before"]
        
        if median_time < time_before:
            return {
                "time_after": median_time,
                "status": "success",
                "error_message": ""
            }
        else:
            slowdown = ((median_time - time_before) / time_before) * 100
            return {
                "time_after": median_time,
                "status": "performance_regression",
                "error_message": f"Optimized query is {slowdown:.1f}% slower than original. Try a different optimization approach."
            }
    except Exception as e:
        try:
            cursor.execute("ROLLBACK")
            cursor.close()
            conn.close()
        except:
            pass
        return {
            "error_message": f"Performance test failed: {str(e)[:300]}",
            "status": "execution_error"
        }