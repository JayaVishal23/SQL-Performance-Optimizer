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

    # ── QUERY 1: Get all columns across all your tables ──────────────────────
    # We filter out PostgreSQL's internal system tables (those live in
    # 'pg_catalog' and 'information_schema' schemas — we only want yours)
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
    # columns is now a list of tuples like:
    # [('orders', 'id', 'integer', 'NO'),
    #  ('orders', 'status', 'character varying', 'YES'),
    #  ('orders', 'created_at', 'timestamp without time zone', 'YES'), ...]

    # ── QUERY 2: Get all indexes ──────────────────────────────────────────────
    # pg_indexes is PostgreSQL's own table that tracks every index
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
    # indexes is a list of tuples like:
    # [('orders', 'orders_pkey', 'CREATE UNIQUE INDEX orders_pkey ON orders USING btree (id)'),
    #  ('users', 'users_email_idx', 'CREATE INDEX users_email_idx ON users USING btree (email)')]

    cursor.close()
    conn.close()

    # ── FORMAT into readable text the AI can understand ───────────────────────
    # We're converting raw query results into a structured text block
    # The AI reads this like a document — so make it clear and organized

    schema_text = format_schema(columns, indexes)

    return {
        "schema_info": schema_text
    }


def format_schema(columns, indexes):
    """
    Takes raw query results and converts them into a clean readable string.
    This string goes directly into the AI's prompt in the next node.
    """

    # Group columns by table name first
    # Before: [('orders','id','integer'), ('orders','status','varchar'), ('users','id','integer')]
    # After:  {'orders': [('id','integer'), ('status','varchar')], 'users': [('id','integer')]}

    tables = {}
    for table_name, column_name, data_type, is_nullable in columns:
        if table_name not in tables:
            tables[table_name] = []
        tables[table_name].append((column_name, data_type, is_nullable))

    # Group indexes by table name the same way
    index_map = {}
    for table_name, index_name, index_def in indexes:
        if table_name not in index_map:
            index_map[table_name] = []
        index_map[table_name].append((index_name, index_def))

    # Now build the formatted string
    lines = []

    for table_name, col_list in tables.items():
        lines.append(f"TABLE: {table_name}")
        lines.append("  COLUMNS:")

        for col_name, data_type, is_nullable in col_list:
            nullable_str = "nullable" if is_nullable == "YES" else "not null"
            lines.append(f"    - {col_name} ({data_type}, {nullable_str})")

        # Show indexes for this table, or explicitly say none exist
        if table_name in index_map:
            lines.append("  INDEXES:")
            for index_name, index_def in index_map[table_name]:
                lines.append(f"    - {index_name}: {index_def}")
        else:
            lines.append("  INDEXES: none")

        lines.append("")  # blank line between tables for readability

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
