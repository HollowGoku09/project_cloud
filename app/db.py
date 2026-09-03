"""
app/db.py
=========
High-performance PostgreSQL database data loader for Web BI Dashboard.
Queries pre-aggregated Materialized Views with @st.cache_data (TTL=3600).
Provides fallback mock dataset generator for standalone execution if PostgreSQL is offline.
"""

import os
import logging
import pandas as pd
import numpy as np
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_db_connection():
    """Attempt database connection via st.secrets or environment variables."""
    try:
        import psycopg2
        
        database_url = None
        if hasattr(st, "secrets"):
            database_url = st.secrets.get("DATABASE_URL") or st.secrets.get("postgres_url")
        if not database_url:
            database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("NEON_DATABASE_URL")
            
        if database_url:
            kwargs = {"dsn": database_url, "connect_timeout": 5}
            if "sslmode=" not in database_url and ("neon.tech" in database_url or os.getenv("DB_SSLMODE")):
                kwargs["sslmode"] = os.getenv("DB_SSLMODE", "require")
            return psycopg2.connect(**kwargs)
            
        secrets_pg = st.secrets.get("postgres", {}) if hasattr(st, "secrets") else {}
        host = secrets_pg.get("host", os.getenv("DB_HOST", "localhost"))
        port = int(secrets_pg.get("port", os.getenv("DB_PORT", 5432)))
        dbname = secrets_pg.get("dbname", os.getenv("DB_NAME", "job_market_db"))
        user = secrets_pg.get("user", os.getenv("DB_USER", "postgres"))
        password = secrets_pg.get("password", os.getenv("DB_PASSWORD", "postgres"))
        sslmode = secrets_pg.get("sslmode", os.getenv("DB_SSLMODE", "require" if host and "neon.tech" in host else None))
        
        kwargs = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
            "connect_timeout": 5
        }
        if sslmode:
            kwargs["sslmode"] = sslmode
            
        conn = psycopg2.connect(**kwargs)
        return conn
    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Falling back to offline dataset engine.")
        return None

@st.cache_data(ttl=3600)
def query_mv(query_str: str) -> pd.DataFrame:
    """Execute SQL query against PostgreSQL warehouse or return empty DataFrame."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql(query_str, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            conn.close()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_top_skills(role_family=None, seniority=None):
    """Load top skills from mv_top_skills_overall or mv_top_skills_by_role_family."""
    conn = get_db_connection()
    if conn:
        try:
            if role_family and role_family != "All Role Families":
                q = f"""
                SELECT skill_name, skill_type, SUM(posting_count) AS demand_count,
                       ROUND(SUM(posting_count)::NUMERIC / 767235 * 100, 2) AS pct_of_total_postings
                FROM mv_top_skills_by_role_family
                WHERE role_family_name = '{role_family}'
                """
                if seniority and seniority != "All Levels":
                    q += f" AND seniority = '{seniority}'"
                q += " GROUP BY skill_name, skill_type ORDER BY demand_count DESC LIMIT 25;"
                df = pd.read_sql(q, conn)
            else:
                q = "SELECT skill_name, skill_type, demand_count, pct_of_total_postings FROM mv_top_skills_overall ORDER BY demand_count DESC LIMIT 25;"
                df = pd.read_sql(q, conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            if conn: conn.close()
            
    skills = [
        ("Python", "programming", 238420, 31.12), ("SQL", "programming", 214580, 28.01),
        ("R", "programming", 95340, 12.44), ("AWS", "cloud", 83920, 10.95),
        ("Tableau", "analyst_tools", 80150, 10.46), ("Power BI", "analyst_tools", 77240, 10.08),
        ("Excel", "analyst_tools", 74890, 9.77), ("Spark", "libraries", 52910, 6.91),
        ("Azure", "cloud", 49840, 6.50), ("Pandas", "libraries", 47620, 6.22),
        ("Snowflake", "databases", 45210, 5.90), ("Java", "programming", 43100, 5.62),
        ("Docker", "other", 38920, 5.08), ("Hadoop", "libraries", 34510, 4.50),
        ("Git", "other", 32410, 4.23), ("Kafka", "libraries", 28940, 3.78),
        ("Airflow", "libraries", 27650, 3.61), ("PostgreSQL", "databases", 26410, 3.45),
        ("GCP", "cloud", 25180, 3.29), ("TensorFlow", "libraries", 23840, 3.11),
        ("PyTorch", "libraries", 22190, 2.90), ("Scala", "programming", 20950, 2.73),
        ("NoSQL", "databases", 19320, 2.52), ("Kubernetes", "other", 18140, 2.37),
        ("Scikit-Learn", "libraries", 16980, 2.22)
    ]
    return pd.DataFrame(skills, columns=['skill_name', 'skill_type', 'demand_count', 'pct_of_total_postings'])

@st.cache_data(ttl=3600)
def load_salary_insights():
    """Load salary analytics from mv_salary_by_role_seniority."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT role_family_name, seniority, country, total_postings, postings_with_salary, pct_disclosed, avg_yearly_salary, median_yearly_salary FROM mv_salary_by_role_seniority;", conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            if conn: conn.close()
            
    records = [
        {"role_family_name": "Data & Analytics", "seniority": "Senior", "country": "United States", "total_postings": 43820, "postings_with_salary": 2140, "pct_disclosed": 4.88, "avg_yearly_salary": 138500, "median_yearly_salary": 135000},
        {"role_family_name": "Data & Analytics", "seniority": "Mid-Entry", "country": "United States", "total_postings": 204500, "postings_with_salary": 8320, "pct_disclosed": 4.07, "avg_yearly_salary": 92000, "median_yearly_salary": 89000},
        {"role_family_name": "Software Engineering", "seniority": "Senior", "country": "United States", "total_postings": 11840, "postings_with_salary": 642, "pct_disclosed": 5.42, "avg_yearly_salary": 165000, "median_yearly_salary": 160000},
        {"role_family_name": "Software Engineering", "seniority": "Mid-Entry", "country": "United States", "total_postings": 33179, "postings_with_salary": 1398, "pct_disclosed": 4.21, "avg_yearly_salary": 115000, "median_yearly_salary": 110000},
        {"role_family_name": "Cloud & DevOps", "seniority": "Senior", "country": "United States", "total_postings": 3940, "postings_with_salary": 218, "pct_disclosed": 5.53, "avg_yearly_salary": 155000, "median_yearly_salary": 150000},
        {"role_family_name": "Cloud & DevOps", "seniority": "Mid-Entry", "country": "United States", "total_postings": 8406, "postings_with_salary": 406, "pct_disclosed": 4.83, "avg_yearly_salary": 108000, "median_yearly_salary": 105000},
        {"role_family_name": "AI/ML", "seniority": "Senior", "country": "United States", "total_postings": 8310, "postings_with_salary": 476, "pct_disclosed": 5.73, "avg_yearly_salary": 178000, "median_yearly_salary": 172000},
        {"role_family_name": "AI/ML", "seniority": "Mid-Entry", "country": "United States", "total_postings": 27815, "postings_with_salary": 1195, "pct_disclosed": 4.30, "avg_yearly_salary": 125000, "median_yearly_salary": 120000},
        {"role_family_name": "Cybersecurity", "seniority": "Senior", "country": "United States", "total_postings": 12, "postings_with_salary": 12, "pct_disclosed": 100.0, "avg_yearly_salary": 179400, "median_yearly_salary": 179400},
        {"role_family_name": "Cybersecurity", "seniority": "Mid-Entry", "country": "United States", "total_postings": 11, "postings_with_salary": 11, "pct_disclosed": 100.0, "avg_yearly_salary": 138000, "median_yearly_salary": 138000},
        {"role_family_name": "Blockchain & Fintech", "seniority": "Senior", "country": "United States", "total_postings": 10, "postings_with_salary": 10, "pct_disclosed": 100.0, "avg_yearly_salary": 184600, "median_yearly_salary": 184600},
        {"role_family_name": "Blockchain & Fintech", "seniority": "Mid-Entry", "country": "United States", "total_postings": 10, "postings_with_salary": 10, "pct_disclosed": 100.0, "avg_yearly_salary": 142000, "median_yearly_salary": 142000},
        {"role_family_name": "AR/VR & Gaming", "seniority": "Senior", "country": "United States", "total_postings": 20, "postings_with_salary": 20, "pct_disclosed": 100.0, "avg_yearly_salary": 162500, "median_yearly_salary": 162500},
        {"role_family_name": "AR/VR & Gaming", "seniority": "Mid-Entry", "country": "United States", "total_postings": 20, "postings_with_salary": 20, "pct_disclosed": 100.0, "avg_yearly_salary": 125000, "median_yearly_salary": 125000}
    ]
    return pd.DataFrame(records)

@st.cache_data(ttl=3600)
def load_top_companies():
    """Load employer hiring leaderboard from mv_top_hiring_companies."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT company_name, total_postings, salaried_postings_count, avg_salary_usd FROM mv_top_hiring_companies ORDER BY total_postings DESC LIMIT 25;", conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            if conn: conn.close()
            
    comps = [
        ("Booz Allen Hamilton", 12450, 480, 118000), ("Upwork", 9820, 210, 85000),
        ("Walmart", 7640, 310, 125000), ("Amazon", 6890, 410, 142000),
        ("Dice", 5430, 150, 95000), ("Capital One", 4980, 290, 135000),
        ("Humana", 4320, 180, 108000), ("Deloitte", 3950, 190, 115000),
        ("Wells Fargo", 3670, 140, 112000), ("Meta", 3210, 220, 168000),
        ("JPMorgan Chase", 3100, 195, 132000), ("Google", 2980, 240, 175000),
        ("Apple", 2750, 185, 162000), ("Microsoft", 2640, 210, 158000),
        ("CVS Health", 2490, 130, 105000)
    ]
    return pd.DataFrame(comps, columns=['company_name', 'total_postings', 'salaried_postings_count', 'avg_salary_usd'])

@st.cache_data(ttl=3600)
def load_market_conditions():
    """Load remote work and country market stats from mv_remote_work_rates."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT country, SUM(total_postings) AS total_postings, ROUND(AVG(remote_work_pct), 2) AS remote_work_pct FROM mv_remote_work_rates GROUP BY country ORDER BY total_postings DESC LIMIT 20;", conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            if conn: conn.close()
            
    records = [
        {"country": "United States", "total_postings": 524100, "remote_work_pct": 11.2, "no_degree_mention_pct": 32.1, "pay_transparency_pct": 5.4},
        {"country": "United Kingdom", "total_postings": 48200, "remote_work_pct": 9.4, "no_degree_mention_pct": 28.4, "pay_transparency_pct": 3.8},
        {"country": "Canada", "total_postings": 31400, "remote_work_pct": 10.8, "no_degree_mention_pct": 31.0, "pay_transparency_pct": 4.1},
        {"country": "Germany", "total_postings": 18900, "remote_work_pct": 12.1, "no_degree_mention_pct": 25.8, "pay_transparency_pct": 2.9},
        {"country": "Ghana", "total_postings": 1420, "remote_work_pct": 14.5, "no_degree_mention_pct": 35.2, "pay_transparency_pct": 2.1},
        {"country": "Nigeria", "total_postings": 3850, "remote_work_pct": 16.8, "no_degree_mention_pct": 38.4, "pay_transparency_pct": 1.8},
        {"country": "India", "total_postings": 58900, "remote_work_pct": 7.8, "no_degree_mention_pct": 24.5, "pay_transparency_pct": 1.2}
    ]
    return pd.DataFrame(records)

@st.cache_data(ttl=3600)
def load_skill_salary_premiums():
    """Load skill salary premiums from mv_skill_salary_premium."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT skill_name, skill_type, postings_with_salary, avg_salary_with_skill, global_avg_salary, salary_premium_usd, pct_salary_premium FROM mv_skill_salary_premium ORDER BY salary_premium_usd DESC LIMIT 20;", conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            if conn: conn.close()
            
    premiums = [
        ("PyTorch", "libraries", 185, 142500, 112400, 30100, 26.78),
        ("TensorFlow", "libraries", 210, 138900, 112400, 26500, 23.58),
        ("Spark", "libraries", 412, 134200, 112400, 21800, 19.39),
        ("AWS", "cloud", 680, 131500, 112400, 19100, 16.99),
        ("Snowflake", "databases", 390, 129800, 112400, 17400, 15.48),
        ("Azure", "cloud", 520, 126400, 112400, 14000, 12.46),
        ("Python", "programming", 1840, 124100, 112400, 11700, 10.41),
        ("SQL", "programming", 1950, 118200, 112400, 5800, 5.16),
        ("Tableau", "analyst_tools", 710, 109500, 112400, -2900, -2.58),
        ("Excel", "analyst_tools", 890, 96200, 112400, -16200, -14.41)
    ]
    return pd.DataFrame(premiums, columns=['skill_name', 'skill_type', 'postings_with_salary', 'avg_salary_with_skill', 'global_avg_salary', 'salary_premium_usd', 'pct_salary_premium'])
