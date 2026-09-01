"""
Handles the SQL Server connection, schema discovery, and SAFE (read-only) query execution.

Safety notes:
- We enforce read-only at two levels: (1) we strongly recommend a read-only DB login,
  and (2) we block any query that isn't a SELECT statement before it ever reaches the server.
- Only tables listed in SQL_ALLOWED_TABLES (if set) are described to the AI, to keep it
  from wandering into sensitive tables you didn't intend to expose.
"""

import os
import re
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text, inspect

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|EXEC|EXECUTE|MERGE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def get_engine():
    server = os.environ["SQL_SERVER"]
    database = os.environ["SQL_DATABASE"]
    username = os.environ["SQL_USERNAME"]
    password = os.environ["SQL_PASSWORD"]
    driver = os.environ.get("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

    params = urllib.parse.quote_plus(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        f"UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;"
    )
    conn_str = f"mssql+pyodbc:///?odbc_connect={params}"
    return create_engine(conn_str, pool_pre_ping=True)


def get_schema_summary(engine, allowed_tables=None):
    """Returns a text description of tables and columns for the AI to reason over."""
    inspector = inspect(engine)
    lines = []
    for table_name in inspector.get_table_names():
        if allowed_tables and table_name not in allowed_tables:
            continue
        cols = inspector.get_columns(table_name)
        col_desc = ", ".join(f"{c['name']} ({c['type']})" for c in cols)
        lines.append(f"- {table_name}: {col_desc}")
    return "\n".join(lines) if lines else "(no tables found or none allowed)"


def is_safe_select(sql: str) -> bool:
    stripped = sql.strip().rstrip(";")
    if not re.match(r"^\s*(SELECT|WITH)\b", stripped, re.IGNORECASE):
        return False
    if FORBIDDEN_KEYWORDS.search(stripped):
        return False
    if ";" in stripped:  # block stacked statements
        return False
    return True


def run_query(engine, sql: str, row_limit: int = 500) -> pd.DataFrame:
    if not is_safe_select(sql):
        raise ValueError(
            "Blocked: only single read-only SELECT statements are allowed. "
            f"Received: {sql}"
        )
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    if len(df) > row_limit:
        df = df.head(row_limit)
    return df
