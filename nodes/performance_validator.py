import os
import psycopg2
import statistics
import re
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

def measure_query_time(cursor, query: str, runs: int = 3) -> float:
    """Run query 3 times with EXPLAIN ANALYZE, return median of last 2."""
    times = []
    for i in range(runs):
        cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS) {query}")
        rows = cursor.fetchall()
        plan = "\n".join([r[0] for r in rows])
        t = parse_execution_time(plan)
        if i > 0 and t > 0:
            times.append(t)
    return statistics.median(times) if times else -1.0

def performance_validator_node(state: AgentState) -> dict:
    """
    Tests up to 4 scenarios in sandboxed transactions:
    1. Original query (baseline already in state.time_before)
    2. Rewritten query alone
    3. Original query + suggested indexes
    4. Rewritten query + suggested indexes
    
    Picks the fastest valid option.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    original = state["original_query"]
    rewritten = state.get("optimized_query", "")
    indexes = state.get("suggested_indexes", [])
    time_before = state["time_before"]
    
    rewrite_changed = rewritten and rewritten.strip() != original.strip()
    has_indexes = len(indexes) > 0
    
    time_after_rewrite = time_before  
    time_after_index = time_before
    time_after_both = time_before
    
    errors = []
    
    try:
        if rewrite_changed:
            try:
                cursor.execute("BEGIN")
                time_after_rewrite = measure_query_time(cursor, rewritten)
                cursor.execute("ROLLBACK")
                if time_after_rewrite < 0:
                    time_after_rewrite = time_before
            except Exception as e:
                cursor.execute("ROLLBACK")
                errors.append(f"Rewrite test failed: {str(e)[:100]}")
                time_after_rewrite = time_before
        
        if has_indexes:
            try:
                cursor.execute("BEGIN")
                for idx_stmt in indexes:
                    cursor.execute(idx_stmt)
                time_after_index = measure_query_time(cursor, original)
                cursor.execute("ROLLBACK")
                if time_after_index < 0:
                    time_after_index = time_before
            except Exception as e:
                cursor.execute("ROLLBACK")
                errors.append(f"Index test failed: {str(e)[:100]}")
                time_after_index = time_before
        
        if rewrite_changed and has_indexes:
            try:
                cursor.execute("BEGIN")
                for idx_stmt in indexes:
                    cursor.execute(idx_stmt)
                time_after_both = measure_query_time(cursor, rewritten)
                cursor.execute("ROLLBACK")
                if time_after_both < 0:
                    time_after_both = time_before
            except Exception as e:
                cursor.execute("ROLLBACK")
                errors.append(f"Combined test failed: {str(e)[:100]}")
                time_after_both = time_before
        
        cursor.close()
        conn.close()
        
        options = {
            "NONE": time_before,
        }
        if rewrite_changed:
            options["REWRITE_ONLY"] = time_after_rewrite
        if has_indexes:
            options["INDEX_ONLY"] = time_after_index
        if rewrite_changed and has_indexes:
            options["BOTH"] = time_after_both
        
        winner = min(options, key=options.get)
        best_time = options[winner]
        
        if winner != "NONE" and best_time >= time_before * 0.95:
            winner = "NONE"
            best_time = time_before
        
        if winner == "NONE":
            return {
                "time_after_rewrite": time_after_rewrite,
                "time_after_index": time_after_index,
                "time_after_both": time_after_both,
                "final_recommendation": "NONE",
                "best_time": best_time,
                "status": "no_improvement",
                "error_message": "No optimization improved performance by >5%. " + " ".join(errors)
            }
        
        return {
            "time_after_rewrite": time_after_rewrite,
            "time_after_index": time_after_index,
            "time_after_both": time_after_both,
            "final_recommendation": winner,
            "best_time": best_time,
            "status": "success",
            "error_message": ""
        }
    
    except Exception as e:
        try:
            cursor.execute("ROLLBACK")
            cursor.close()
            conn.close()
        except:
            pass
        return {
            "status": "execution_error",
            "error_message": f"Performance validation crashed: {str(e)[:300]}",
            "final_recommendation": "NONE",
            "best_time": time_before
        }