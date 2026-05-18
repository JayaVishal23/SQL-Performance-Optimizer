import os
import json
import re
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ValidationError
from state import AgentState

load_dotenv()

class OptimizedQueryOutput(BaseModel):
    optimized_sql: str = Field(description="The optimized SQL query, valid PostgreSQL syntax only")
    reasoning: str = Field(description="Brief explanation of changes made")
    optimization_type: str = Field(description="One of: INDEX_SUGGESTION, QUERY_REWRITE, JOIN_REORDER, SUBQUERY_REWRITE, NO_OPTIMIZATION")

OPTIMIZER_PROMPT = """You are an expert PostgreSQL query optimizer. Analyze the slow query and rewrite it to be faster.

DATABASE SCHEMA:
{schema_info}

ORIGINAL SLOW QUERY:
{original_query}

EXPLAIN ANALYZE OUTPUT (this shows why the query is slow):
{explain_plan}

{previous_error_section}

YOUR TASK:
Analyze the EXPLAIN plan. Look for problems like:
- Seq Scan on large tables (suggests missing index)
- Expensive Sort operations
- Nested Loop on large datasets
- Correlated subqueries that should be JOINs
- SELECT * that fetches unnecessary columns

Rewrite the query to be faster. Common optimizations:
- Rewrite correlated subqueries as JOINs
- Replace IN (SELECT...) with EXISTS where appropriate  
- Replace SELECT * with specific columns when only some are needed
- Convert comma-joins (FROM a, b WHERE) to explicit JOIN syntax
- Restructure WHERE clauses to filter earlier

CRITICAL RULES:
1. The optimized query MUST return the same result rows as the original.
2. Output ONLY valid PostgreSQL syntax.
3. If the query is already optimal and just needs an index, return the original query unchanged with optimization_type = INDEX_SUGGESTION and mention the needed index in reasoning.

You MUST respond with ONLY a JSON object in this exact format, with no other text before or after:

{{
  "optimized_sql": "your optimized SQL query here",
  "reasoning": "brief explanation of what you changed and why",
  "optimization_type": "INDEX_SUGGESTION or QUERY_REWRITE or JOIN_REORDER or SUBQUERY_REWRITE or NO_OPTIMIZATION"
}}

Do not include markdown code fences. Do not include any text outside the JSON object. Just the raw JSON."""

def extract_json_from_response(text: str) -> dict:
    """
    Local models often add text around JSON. This extracts the JSON object.
    Tries multiple strategies because qwen sometimes wraps in ```json blocks.
    """
    # Strategy 1: Look for ```json ... ``` block
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass
    
    # Strategy 2: Find first { ... last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"Could not extract valid JSON from LLM response:\n{text[:500]}")

def optimizer_node(state: AgentState) -> dict:
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
        num_ctx=8192,  # context window — qwen2.5-coder supports this
    )
    
    previous_error = state.get("error_message", "")
    if previous_error:
        previous_error_section = f"""PREVIOUS ATTEMPT FAILED:
Previous optimized query: {state.get('optimized_query', '')}
Error: {previous_error}
Try a DIFFERENT approach. Do not repeat this mistake."""
    else:
        previous_error_section = ""
    
    prompt = ChatPromptTemplate.from_template(OPTIMIZER_PROMPT)
    chain = prompt | llm
    
    response = chain.invoke({
        "schema_info": state["schema_info"],
        "original_query": state["original_query"],
        "explain_plan": state["explain_plan"][:3000],  # truncate massive plans
        "previous_error_section": previous_error_section
    })
    
    raw_text = response.content
    
    try:
        parsed = extract_json_from_response(raw_text)
        validated = OptimizedQueryOutput(**parsed)
        
        return {
            "optimized_query": validated.optimized_sql,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "error_message": ""
        }
    except (ValueError, ValidationError) as e:
        return {
            "optimized_query": state.get("optimized_query", ""),
            "iteration_count": state.get("iteration_count", 0) + 1,
            "error_message": f"LLM output parsing failed: {str(e)[:200]}"
        }

if __name__ == "__main__":
    from profiler import profiler_node
    from schema_extractor import schema_extractor_node
    
    state = {
        "original_query": "SELECT * FROM orders WHERE order_status = 'pending'",
        "explain_plan": "", "schema_info": "", "optimized_query": "",
        "time_before": 0.0, "time_after": 0.0,
        "iteration_count": 0, "error_message": "", "status": "running"
    }
    state.update(profiler_node(state))
    state.update(schema_extractor_node(state))
    result = optimizer_node(state)
    print(f"Optimized: {result['optimized_query']}")
    print(f"Error (if any): {result['error_message']}")