"""Database loading functions."""

import io
import logging
import pandas as pd
import psycopg2
from psycopg2.extensions import connection as PgConnection

from src.config import get_db_connection_kwargs

logger = logging.getLogger(__name__)

def get_db_connection() -> PgConnection:
    """Establish and return a psycopg2 PostgreSQL database connection."""
    conn = psycopg2.connect(**get_db_connection_kwargs())
    conn.autocommit = False
    return conn

def truncate_tables(conn: PgConnection, tables: list[str]) -> None:
    """Truncate tables in CASCADE mode to ensure idempotent clean reloads."""
    with conn.cursor() as cur:
        tbl_str = ", ".join(tables)
        logger.info(f"Truncating tables for clean reload: {tbl_str}")
        cur.execute(f"TRUNCATE TABLE {tbl_str} CASCADE;")
    conn.commit()

def bulk_copy_df(conn: PgConnection, df: pd.DataFrame, table_name: str, columns: list[str]) -> int:
    """Perform ultra-fast bulk loading into PostgreSQL using copy_expert and in-memory CSV buffer."""
    if df.empty:
        return 0
        
    s_buf = io.StringIO()
    df[columns].to_csv(s_buf, index=False, header=False, na_rep='\\N')
    s_buf.seek(0)
    
    col_str = ", ".join(columns)
    sql = f"COPY {table_name} ({col_str}) FROM STDIN WITH (FORMAT csv, NULL '\\N');"
    
    with conn.cursor() as cur:
        cur.copy_expert(sql, s_buf)
    
    conn.commit()
    return len(df)

def load_dimension(conn: PgConnection, df: pd.DataFrame, table_name: str) -> int:
    """Load a dimension table in bulk."""
    cols = df.columns.tolist()
    count = bulk_copy_df(conn, df, table_name, cols)
    logger.info(f"Loaded {count:,} rows into {table_name}")
    return count

def load_fact_chunk(conn: PgConnection, df_chunk: pd.DataFrame) -> int:
    """Load a chunk of job_postings_fact."""
    cols = df_chunk.columns.tolist()
    count = bulk_copy_df(conn, df_chunk, "job_postings_fact", cols)
    return count

def load_bridge_chunk(conn: PgConnection, df_chunk: pd.DataFrame) -> int:
    """Load a chunk of skills_job_dim bridge."""
    cols = df_chunk.columns.tolist()
    count = bulk_copy_df(conn, df_chunk, "skills_job_dim", cols)
    return count
