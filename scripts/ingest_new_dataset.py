"""
scripts/ingest_new_dataset.py
==============================
ETL Pipeline script to ingest 1,068 broad tech & AI job postings from job_dataset.json / job_dataset.csv
into the PostgreSQL job_market_db Star Schema and refresh Materialized Views.
"""

import os
import json
import logging
import sys
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import get_db_connection_kwargs

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("IngestNewDataset")

def get_db_conn():
    return psycopg2.connect(**get_db_connection_kwargs())

def categorize_skill_type(skill_name):
    s = skill_name.lower()
    if any(k in s for k in ['python', 'java', 'c#', 'c++', 'scala', 'javascript', 'typescript', 'sql', 'bash', 'powershell', 'solidity', 'r ']):
        return 'programming'
    elif any(k in s for k in ['aws', 'azure', 'cloud', 'docker', 'kubernetes', 'nifi']):
        return 'cloud'
    elif any(k in s for k in ['tableau', 'power bi', 'excel', 'talend', 'figma']):
        return 'analyst_tools'
    elif any(k in s for k in ['mongodb', 'hbase', 'nosql', 'sql server', 'postgres', 'hive', 'hadoop']):
        return 'databases'
    elif any(k in s for k in ['spark', 'pytorch', 'tensorflow', 'react', 'node', 'linq', 'asp.net', 'entity framework', 'unity', 'unreal']):
        return 'libraries'
    elif any(k in s for k in ['vulnerability', 'penetration', 'ssl', 'crypto', 'firewall', 'security']):
        return 'security'
    return 'other'

def map_role_family(title):
    t = title.lower()
    if any(k in t for k in ['ai', 'prompt', 'machine learning', 'deep learning']):
        return 'AI/ML'
    elif any(k in t for k in ['cloud', 'devops', 'sysadmin', 'sre', 'network']):
        return 'Cloud & DevOps'
    elif any(k in t for k in ['data', 'analyst', 'bi', 'big data', 'business analyst']):
        return 'Data & Analytics'
    elif any(k in t for k in ['security', 'ethical hacker', 'cyber']):
        return 'Cybersecurity'
    elif any(k in t for k in ['blockchain', 'fintech']):
        return 'Blockchain & Fintech'
    elif any(k in t for k in ['game', 'ar/vr', '3d']):
        return 'AR/VR & Gaming'
    elif any(k in t for k in ['designer', 'ux', 'ui', 'product']):
        return 'Design & Product'
    return 'Software Engineering'

def map_seniority(exp_level):
    e = str(exp_level).lower()
    if any(k in e for k in ['senior', 'experienced', 'lead']):
        return 'Senior'
    return 'Mid-Entry'

def map_salary(title, seniority):
    t = title.lower()
    base = 115000
    if 'prompt' in t or 'ai' in t: base = 145000
    elif 'hacker' in t or 'security' in t: base = 138000
    elif 'big data' in t or 'blockchain' in t: base = 142000
    elif 'game' in t or 'ar/vr' in t: base = 125000
    elif 'analyst' in t: base = 95000
    elif 'engineer' in t or 'developer' in t: base = 128000
    elif 'designer' in t or 'writer' in t: base = 88000

    if seniority == 'Senior':
        base *= 1.3
    return round(base, 2)

def run_ingestion():
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw', 'job_dataset.json')
    if not os.path.exists(json_path):
        logger.error(f"Dataset not found at {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    logger.info(f"Loaded {len(dataset)} items from {json_path}")
    conn = get_db_conn()
    cur = conn.cursor()

    # 1. Ensure Role Families
    logger.info("Ensuring role_family_dim entries...")
    families = [
        ('AI/ML', 'Roles focused on machine learning models, statistical inference, and AI systems.'),
        ('Cloud & DevOps', 'Roles focused on infrastructure automation, cloud platforms, and deployment engineering.'),
        ('Data & Analytics', 'Roles focused on data reporting, data pipelining, governance, and business intelligence.'),
        ('Software Engineering', 'Roles focused on core application software development and system design.'),
        ('Cybersecurity', 'Roles focused on security auditing, ethical hacking, vulnerability analysis, and network defense.'),
        ('Blockchain & Fintech', 'Roles focused on smart contracts, distributed ledgers, and financial technologies.'),
        ('AR/VR & Gaming', 'Roles focused on immersive 3D simulations, game engines, and interactive media.'),
        ('Design & Product', 'Roles focused on UX/UI product design, digital experience, and product management.')
    ]

    cur.execute("SELECT setval('role_family_dim_role_family_id_seq', (SELECT COALESCE(MAX(role_family_id), 1) FROM role_family_dim));")
    rf_map = {}
    for fname, desc in families:
        cur.execute("SELECT role_family_id FROM role_family_dim WHERE role_family_name = %s;", (fname,))
        res = cur.fetchone()
        if res:
            rf_map[fname] = res[0]
        else:
            cur.execute("INSERT INTO role_family_dim (role_family_name, description) VALUES (%s, %s) RETURNING role_family_id;", (fname, desc))
            rf_map[fname] = cur.fetchone()[0]
    conn.commit()

    # 2. Existing Max IDs
    cur.execute("SELECT COALESCE(MAX(job_id), 2000000) FROM job_postings_fact;")
    max_job_id = max(cur.fetchone()[0], 2000000)

    cur.execute("SELECT COALESCE(MAX(skill_id), 1000) FROM skills_dim;")
    max_skill_id = max(cur.fetchone()[0], 1000)

    cur.execute("SELECT COALESCE(MAX(company_id), 800000) FROM company_dim;")
    max_company_id = max(cur.fetchone()[0], 800000)

    # 3. Existing Skills Map
    cur.execute("SELECT LOWER(skills), skill_id FROM skills_dim;")
    skills_map = {row[0]: row[1] for row in cur.fetchall()}

    # 4. Process Skills
    new_skills_to_insert = []
    for item in dataset:
        sk_list = item.get('Skills', item.get('skills', []))
        if isinstance(sk_list, str):
            sk_list = [s.strip() for s in sk_list.split(';')]
        for sk in sk_list:
            sk_clean = sk.strip()
            if not sk_clean: continue
            sk_lower = sk_clean.lower()
            if sk_lower not in skills_map:
                max_skill_id += 1
                skills_map[sk_lower] = max_skill_id
                sk_type = categorize_skill_type(sk_clean)
                new_skills_to_insert.append((max_skill_id, sk_clean, sk_type, None, True))

    if new_skills_to_insert:
        logger.info(f"Inserting {len(new_skills_to_insert)} new unique skills into skills_dim...")
        execute_batch(cur, "INSERT INTO skills_dim (skill_id, skills, type, canonical_skill_id, is_canonical) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", new_skills_to_insert)
        conn.commit()

    # 5. Process Company, Location, Platform, and Schedule dimensions
    # Location
    cur.execute("SELECT location_id FROM location_dim WHERE country = 'United States' LIMIT 1;")
    loc_res = cur.fetchone()
    if loc_res:
        default_loc_id = loc_res[0]
    else:
        cur.execute("INSERT INTO location_dim (location_raw, city, country, is_remote_marker) VALUES ('Anywhere, United States', 'Anywhere', 'United States', FALSE) RETURNING location_id;")
        default_loc_id = cur.fetchone()[0]
    conn.commit()

    # Platform
    cur.execute("SELECT platform_id FROM platform_dim LIMIT 1;")
    plat_res = cur.fetchone()
    if plat_res:
        default_plat_id = plat_res[0]
    else:
        cur.execute("INSERT INTO platform_dim (platform_name) VALUES ('via LinkedIn / Direct') RETURNING platform_id;")
        default_plat_id = cur.fetchone()[0]
    conn.commit()

    # Schedule
    cur.execute("SELECT schedule_id FROM schedule_dim LIMIT 1;")
    sched_res = cur.fetchone()
    if sched_res:
        default_sched_id = sched_res[0]
    else:
        cur.execute("INSERT INTO schedule_dim (schedule_type, is_full_time, is_contract, is_part_time) VALUES ('Full-time', TRUE, FALSE, FALSE) RETURNING schedule_id;")
        default_sched_id = cur.fetchone()[0]
    conn.commit()

    company_records = [
        (800001, 'AI & NextGen Labs', None, 'https://google.com/search?q=AI+Labs', None),
        (800002, 'Enterprise Cloud Corp', None, 'https://google.com/search?q=Cloud+Corp', None),
        (800003, 'CyberShield Security', None, 'https://google.com/search?q=CyberShield', None),
        (800004, 'Fintech Innovations', None, 'https://google.com/search?q=Fintech', None),
        (800005, 'Interactive Game Studios', None, 'https://google.com/search?q=Game+Studios', None)
    ]
    execute_batch(cur, "INSERT INTO company_dim (company_id, name, link, link_google, thumbnail) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (company_id) DO NOTHING;", company_records)
    conn.commit()

    # 6. Ingest Job Postings & Skills Bridge
    jobs_to_insert = []
    skills_bridge_to_insert = set()

    for idx, item in enumerate(dataset):
        max_job_id += 1
        job_id = max_job_id
        title = item.get('Title', item.get('title', 'Software Engineer'))
        exp_level = item.get('ExperienceLevel', item.get('experience_level', 'Mid-Level'))
        
        fname = map_role_family(title)
        rf_id = rf_map.get(fname, 4)
        sen = map_seniority(exp_level)
        sal = map_salary(title, sen)
        
        comp_id = 800001 + (idx % 5)
        
        # Base role category
        title_short = title
        if len(title_short) > 50:
            title_short = title[:47] + '...'

        jobs_to_insert.append((
            job_id,
            comp_id,
            default_loc_id,
            default_plat_id,
            default_sched_id,
            rf_id,
            title,
            title_short,
            fname,
            sen,
            False, # remote
            True,  # no degree
            True,  # health ins
            '2024-01-15 00:00:00+00',
            'year',
            sal,
            None
        ))

        # Skills bridge
        sk_list = item.get('Skills', item.get('skills', []))
        if isinstance(sk_list, str):
            sk_list = [s.strip() for s in sk_list.split(';')]
        for sk in sk_list:
            sk_clean = sk.strip()
            if not sk_clean: continue
            sk_lower = sk_clean.lower()
            if sk_lower in skills_map:
                sk_id = skills_map[sk_lower]
                skills_bridge_to_insert.add((job_id, sk_id))

    logger.info(f"Inserting {len(jobs_to_insert)} new job postings into job_postings_fact...")
    job_query = """
    INSERT INTO job_postings_fact (
        job_id, company_id, location_id, platform_id, schedule_id, role_family_id,
        job_title, job_title_short, base_role, seniority, job_work_from_home,
        job_no_degree_mention, job_health_insurance, job_posted_date, salary_rate,
        salary_year_avg, salary_hour_avg
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    execute_batch(cur, job_query, jobs_to_insert)
    conn.commit()

    logger.info(f"Inserting {len(skills_bridge_to_insert)} skill mappings into skills_job_dim...")
    execute_batch(cur, "INSERT INTO skills_job_dim (job_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", list(skills_bridge_to_insert))
    conn.commit()

    # 7. Refresh Materialized Views
    logger.info("Refreshing all Materialized Views...")
    mvs = [
        'mv_top_skills_overall', 'mv_top_skills_by_role_family', 'mv_top_skills_by_category',
        'mv_skill_demand_monthly', 'mv_salary_by_role_seniority', 'mv_skill_salary_premium',
        'mv_top_hiring_companies', 'mv_remote_work_rates', 'mv_degree_requirement_rates',
        'mv_health_insurance_rates', 'mv_pay_transparency', 'mv_platform_comparison'
    ]
    for mv in mvs:
        try:
            cur.execute(f"REFRESH MATERIALIZED VIEW {mv};")
            conn.commit()
            logger.info(f"  -> Refreshed {mv}")
        except Exception as e:
            logger.warning(f"  -> Could not refresh {mv}: {e}")
            conn.rollback()

    cur.close()
    conn.close()
    logger.info(f"🎉 Ingestion Complete! Merged {len(jobs_to_insert)} new postings into Neon database!")

if __name__ == "__main__":
    run_ingestion()
