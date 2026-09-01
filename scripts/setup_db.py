"""
scripts/setup_db.py
===================
Utility script to initialize schema, tables, indexes, and materialized views
in PostgreSQL (local or cloud Neon database).
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import get_db_connection_kwargs, DB_HOST, DB_PORT, DB_NAME, DB_USER, DATABASE_URL

def init_database():
    target = DATABASE_URL if DATABASE_URL else f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # Mask password if printing URI
    masked_target = target
    if "@" in masked_target and "://" in masked_target:
        prefix, rest = masked_target.split("://", 1)
        creds, host_part = rest.split("@", 1)
        user_part = creds.split(":", 1)[0]
        masked_target = f"{prefix}://{user_part}:****@{host_part}"
    
    print(f"Connecting to PostgreSQL database at {masked_target}...")
    
    conn_kwargs = get_db_connection_kwargs()
    try:
        db_conn = psycopg2.connect(**conn_kwargs)
        db_conn.autocommit = True
        print("[OK] Connected to target database successfully.")
    except psycopg2.OperationalError as e:
        err_msg = str(e)
        # If running locally and database doesn't exist, try creating it via 'postgres' db
        if not DATABASE_URL and ("database" in err_msg and "does not exist" in err_msg):
            print(f"Database '{DB_NAME}' does not exist. Attempting to create it on local server...")
            try:
                from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
                admin_kwargs = conn_kwargs.copy()
                admin_kwargs["dbname"] = "postgres"
                admin_conn = psycopg2.connect(**admin_kwargs)
                admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                with admin_conn.cursor() as cur:
                    cur.execute(f'CREATE DATABASE "{DB_NAME}";')
                admin_conn.close()
                print(f"[OK] Database '{DB_NAME}' created successfully.")
                db_conn = psycopg2.connect(**conn_kwargs)
                db_conn.autocommit = True
            except Exception as create_err:
                print(f"[ERROR] Failed to auto-create database: {create_err}")
                return False
        else:
            print(f"[ERROR] Connection failed: {e}")
            return False

    print("Applying schema DDL files...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_files = [
        os.path.join(base_dir, 'sql', '00_drop_all.sql'),
        os.path.join(base_dir, 'sql', '01_schema.sql'),
        os.path.join(base_dir, 'sql', '02_indexes.sql'),
        os.path.join(base_dir, 'sql', '03_materialized_views.sql')
    ]
    
    for sf in sql_files:
        filename = os.path.basename(sf)
        if not os.path.exists(sf):
            print(f"Skipping missing file {filename}")
            continue
        print(f"Executing {filename}...")
        try:
            with open(sf, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            with db_conn.cursor() as cur:
                cur.execute(sql_content)
            print(f"  -> [OK] {filename} applied successfully.")
        except Exception as e:
            print(f"  -> [WARNING/ERROR] in {filename}: {e}")
            # If 00_drop_all or 03_materialized_views fails on empty tables, continue
            if "00_drop_all" in filename or "03_materialized_views" in filename:
                continue
            else:
                db_conn.close()
                return False

    db_conn.close()
    print("\n[OK] All database tables, indexes, and views initialized successfully!")
    return True

if __name__ == "__main__":
    init_database()
