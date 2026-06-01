import os
import psycopg2
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

def add_limit(query: str, limit: int = 1000) -> str:
    """Adds LIMIT for safe semantic comparison."""
    q = query.strip().rstrip(";")
    if "limit" in q.lower():
        return q
    return f"{q} LIMIT {limit}"

def semantic_validator_node(state: AgentState) -> dict:
    optimized = state.get("optimized_query", "")
    original = state["original_query"]
    
    if not optimized or optimized.strip() == original.strip():
        return {"error_message": "", "status": "semantically_valid"}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    original_limited = add_limit(original)
    optimized_limited = add_limit(optimized)
    
    try:
        cursor.execute(original_limited)
        original_rows = cursor.fetchall()
        original_set = set(map(tuple, original_rows))
        
        cursor.execute(optimized_limited)
        optimized_rows = cursor.fetchall()
        optimized_set = set(map(tuple, optimized_rows))
        
        cursor.close()
        conn.close()
        
        if original_set == optimized_set:
            return {"error_message": "", "status": "semantically_valid"}
        else:
            diff = len(original_set.symmetric_difference(optimized_set))
            return {
                "error_message": f"Result sets differ by {diff} rows. Original returned {len(original_set)}, optimized returned {len(optimized_set)}.",
                "status": "semantic_mismatch"
            }
    except Exception as e:
        try:
            cursor.close()
            conn.close()
        except:
            pass
        return {
            "error_message": f"Optimized query failed: {str(e)[:300]}",
            "status": "execution_error"
        }