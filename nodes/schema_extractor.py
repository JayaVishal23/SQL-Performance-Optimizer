import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
from state import AgentState

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def schema_extractor_node(state: AgentState) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    columns = cursor.fetchall()

    cursor.execute("""
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    indexes = cursor.fetchall()

    cursor.close()
    conn.close()

    schema_text = format_schema(columns, indexes)

    return {
        "schema_info": schema_text
    }


def format_schema(columns, indexes):
    """
    Takes raw query results and converts them into a clean readable string.
    This string goes directly into the AI's prompt in the next node.
    """


    tables = {}
    for table_name, column_name, data_type, is_nullable in columns:
        if table_name not in tables:
            tables[table_name] = []
        tables[table_name].append((column_name, data_type, is_nullable))

    index_map = {}
    for table_name, index_name, index_def in indexes:
        if table_name not in index_map:
            index_map[table_name] = []
        index_map[table_name].append((index_name, index_def))

    lines = []

    for table_name, col_list in tables.items():
        lines.append(f"TABLE: {table_name}")
        lines.append("  COLUMNS:")

        for col_name, data_type, is_nullable in col_list:
            nullable_str = "nullable" if is_nullable == "YES" else "not null"
            lines.append(f"    - {col_name} ({data_type}, {nullable_str})")

        if table_name in index_map:
            lines.append("  INDEXES:")
            for index_name, index_def in index_map[table_name]:
                lines.append(f"    - {index_name}: {index_def}")
        else:
            lines.append("  INDEXES: none")

        lines.append("") 

    return "\n".join(lines)

test_state = {
    "original_query": "SELECT * FROM orders WHERE status = 'pending'",
    "explain_plan": "",
    "schema_info": "",
    "optimized_query": "",
    "time_before": 0.0,
    "time_after": 0.0,
    "iteration_count": 0,
    "error_message": "",
    "status": "running"
}

result = schema_extractor_node(test_state)
print(result["schema_info"])
