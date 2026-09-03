"""Configuration settings and mapping rules."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_REJECTS_DIR = DATA_DIR / "rejects"
SQL_DIR = BASE_DIR / "sql"

# Database connection parameters
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("NEON_DATABASE_URL")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "job_market_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require" if (DB_HOST and "neon.tech" in DB_HOST) or (DATABASE_URL and "neon.tech" in DATABASE_URL) else None)

def get_db_connection_kwargs() -> dict:
    """Return keyword arguments for psycopg2.connect based on DATABASE_URL or DB_* settings."""
    if DATABASE_URL:
        kwargs = {"dsn": DATABASE_URL}
        if "sslmode=" not in DATABASE_URL and DB_SSLMODE:
            kwargs["sslmode"] = DB_SSLMODE
        return kwargs
    
    kwargs = {
        "host": DB_HOST,
        "port": DB_PORT,
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }
    if DB_SSLMODE:
        kwargs["sslmode"] = DB_SSLMODE
    return kwargs

# Feature Flags & Processing Settings
EXCLUDE_SUDAN = os.getenv("EXCLUDE_SUDAN", "True").lower() in ("true", "1", "yes")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 100000))
MAX_BRIDGE_ROWS = int(os.getenv("MAX_BRIDGE_ROWS", 1800000))

# -----------------------------------------------------------------------------
# Business Mapping Rules
# -----------------------------------------------------------------------------

# Canonical skill mappings: variant -> canonical name
CANONICAL_SKILL_MAP = {
    "powerbi": "power bi",
    "msaccess": "ms access",
    "sqlserver": "sql server",
    "mongodb": "mongo",
    "nosql": "no-sql",
    "asp.netcore": "asp.net core",
    "angular.js": "angular",
    "angularjs": "angular",
    "vue.js": "vue",
    "vuejs": "vue",
    "react.js": "react",
    "reactjs": "react",
    "node.js": "node",
    "nodejs": "node",
    "rubyon rails": "ruby on rails",
    "golang": "go",
    "huggingface": "hugging face",
    "visualbasic": "visual basic",
    "scikitlearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "pyspark": "spark",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "gcp": "google cloud platform"
}

# Multi-type skill resolutions
MULTI_TYPE_RESOLUTIONS = {
    "sas": "analyst_tools",
    "ruby": "programming",
    "firebase": "databases"
}

# Role Family Mapping
ROLE_FAMILY_MAP = {
    "Data Analyst": "Data & Analytics",
    "Senior Data Analyst": "Data & Analytics",
    "Data Engineer": "Data & Analytics",
    "Senior Data Engineer": "Data & Analytics",
    "Business Analyst": "Data & Analytics",
    "Software Engineer": "Software Engineering",
    "Cloud Engineer": "Cloud & DevOps",
    "Machine Learning Engineer": "AI/ML",
    "Data Scientist": "AI/ML",
    "Senior Data Scientist": "AI/ML"
}

ROLE_FAMILY_DESCRIPTIONS = {
    "Data & Analytics": "Roles focused on data reporting, data pipelining, governance, and business intelligence.",
    "Software Engineering": "Roles focused on core application software development and system design.",
    "Cloud & DevOps": "Roles focused on infrastructure automation, cloud platforms, and deployment engineering.",
    "AI/ML": "Roles focused on machine learning models, statistical inference, and AI systems."
}
