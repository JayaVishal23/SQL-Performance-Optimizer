import psycopg2
import time
import os
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

def get_db_connection():
    # This function creates a connection to your PostgreSQL database
    # Think of it like opening a phone call to the database
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def profiler_node(state: AgentState) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    # A cursor is like a pen that writes queries to the database

    query = state["original_query"]
    # Prefix the user's query with EXPLAIN ANALYZE
    explain_query = f"EXPLAIN ANALYZE {query}"

    start = time.time()
    cursor.execute(explain_query)   # Send the query to PostgreSQL
    end = time.time()

    explain_output = cursor.fetchall()  # Get all the rows of output back
    # Each row is a tuple like ("Seq Scan on orders  (cost=...)",)
    # We join them into one big string the AI can read
    explain_text = "\n".join([row[0] for row in explain_output])

    execution_time = end - start

    cursor.close()
    conn.close()
    # Always close connections — leaving them open wastes database resources

    # Return only the fields this node changed
    # LangGraph merges this dict back into the full state automatically
    return {
        "explain_plan": explain_text,
        "time_before": execution_time,
        "iteration_count": 0,
        "status": "running"
    }

# test_state = {
#     "original_query": "SELECT * FROM orders WHERE order_status = 'pending' AND created_at > '2024-01-01'",
#     "explain_plan": "",
#     "schema_info": "",
#     "optimized_query": "",
#     "time_before": 0.0,
#     "time_after": 0.0,
#     "iteration_count": 0,
#     "error_message": "",
#     "status": "running"
# }

# result = profiler_node(test_state)
# print(result)

# "This node profiles a SQL query by executing it with EXPLAIN ANALYZE, capturing the execution plan and runtime, and storing it for further optimization steps."