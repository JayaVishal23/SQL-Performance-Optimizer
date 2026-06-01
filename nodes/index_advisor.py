import os
import json
import re
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ValidationError
from typing import List
from state import AgentState

load_dotenv()

class IndexSuggestion(BaseModel):
    indexes: List[str] = Field(description="List of CREATE INDEX statements. Empty list if no indexes needed.")
    reasoning: str = Field(description="Why these indexes will help, based on the EXPLAIN plan")

INDEX_ADVISOR_PROMPT = """You are an expert PostgreSQL DBA. Analyze the query, EXPLAIN plan, and existing schema. Suggest indexes that would speed up this query.

DATABASE SCHEMA (existing tables and indexes):
{schema_info}

QUERY:
{query}

EXPLAIN ANALYZE OUTPUT:
{explain_plan}

YOUR TASK:
Look at the EXPLAIN plan for these signals that indicate missing indexes:
- "Seq Scan" on large tables (instead of Index Scan) — column in WHERE clause needs an index
- "Filter:" lines with high "Rows Removed by Filter" — filter columns need an index  
- Hash Join with high cost — join columns might benefit from indexes
- Sort operations on large datasets — ORDER BY columns might benefit

RULES:
1. ONLY suggest indexes on columns NOT already indexed (check the schema's INDEXES section).
2. Suggest indexes on columns that appear in WHERE, JOIN ON, or ORDER BY clauses.
3. For multi-column WHERE clauses, consider composite indexes (column order matters: equality first, then range).
4. Use this naming convention: idx_<tablename>_<columnname>  (e.g., idx_orders_order_status)
5. Don't suggest indexes on tables with under 1000 rows — overhead exceeds benefit.
6. If the query already has all needed indexes, return an empty list.

You MUST respond with ONLY a JSON object in this exact format. No markdown, no extra text:

{{
  "indexes": ["CREATE INDEX idx_table_col ON table(col)", "CREATE INDEX idx_other ON other(x, y)"],
  "reasoning": "brief explanation of why these indexes help based on the EXPLAIN plan"
}}

If no indexes needed:
{{
  "indexes": [],
  "reasoning": "Query already uses available indexes efficiently"
}}"""

def extract_json_from_response(text: str) -> dict:
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass
    
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"Could not parse JSON: {text[:300]}")

def validate_index_statement(stmt: str) -> bool:
    """Basic safety check: must be a CREATE INDEX statement, nothing else."""
    s = stmt.strip().upper()
    if not s.startswith("CREATE INDEX") and not s.startswith("CREATE UNIQUE INDEX"):
        return False
    # Block any dangerous keywords
    forbidden = ["DROP", "DELETE", "TRUNCATE", "ALTER TABLE", "GRANT", "REVOKE", ";"]
    body = stmt.strip().rstrip(";")
    if ";" in body:  # no chained statements
        return False
    return True

def index_advisor_node(state: AgentState) -> dict:
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
        num_ctx=8192,
    )
    
    # Use the optimized query if we have one, otherwise the original
    query_to_analyze = state.get("optimized_query") or state["original_query"]
    
    prompt = ChatPromptTemplate.from_template(INDEX_ADVISOR_PROMPT)
    chain = prompt | llm
    
    response = chain.invoke({
        "schema_info": state["schema_info"],
        "query": query_to_analyze,
        "explain_plan": state["explain_plan"][:3000],
    })
    
    try:
        parsed = extract_json_from_response(response.content)
        validated = IndexSuggestion(**parsed)
        
        # Filter out unsafe or malformed index statements
        safe_indexes = [idx for idx in validated.indexes if validate_index_statement(idx)]
        
        return {
            "suggested_indexes": safe_indexes,
            "error_message": ""
        }
    except (ValueError, ValidationError) as e:
        return {
            "suggested_indexes": [],
            "error_message": f"Index advisor parsing failed: {str(e)[:200]}"
        }

if __name__ == "__main__":
    from .profiler import profiler_node
    from .schema_extractor import schema_extractor_node
    
    state = {
        "original_query": "SELECT * FROM orders WHERE order_status = 'pending'",
        "explain_plan": "", "schema_info": "", "optimized_query": "",
        "suggested_indexes": [],
        "time_before": 0.0, "time_after_rewrite": 0.0,
        "time_after_index": 0.0, "time_after_both": 0.0,
        "final_recommendation": "", "best_time": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    state.update(profiler_node(state))
    state.update(schema_extractor_node(state))
    result = index_advisor_node(state)
    print("Suggested indexes:")
    for idx in result["suggested_indexes"]:
        print(f"  - {idx}")