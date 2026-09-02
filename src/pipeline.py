"""ETL pipeline execution script."""

import sys
import time
import argparse
import logging
from typing import Set

from src.extract import (
    extract_companies,
    extract_skills,
    extract_job_postings,
    extract_skills_job,
    get_csv_path
)
from src.transform import (
    transform_companies,
    transform_skills,
    build_role_family_dim,
    build_location_dim,
    build_platform_dim,
    build_schedule_dim,
    transform_job_postings_chunk,
    transform_skills_job_chunk,
    log_rejected_rows
)
from src.load import (
    get_db_connection,
    truncate_tables,
    load_dimension,
    load_fact_chunk,
    load_bridge_chunk
)
from src.validate import validate_post_load

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def run_dimensions_pipeline(conn) -> dict:
    """Extract, transform, and load all dimension tables."""
    start_time = time.time()
    logger.info("Starting dimension ETL stage")
    
    dim_tables = [
        'skills_job_dim', 'job_postings_fact', 'company_dim',
        'skills_dim', 'location_dim', 'platform_dim', 'schedule_dim', 'role_family_dim'
    ]
    truncate_tables(conn, dim_tables)
    
    df_comp_raw = extract_companies()
    df_comp = transform_companies(df_comp_raw)
    load_dimension(conn, df_comp, "company_dim")
    
    df_skills_raw = extract_skills()
    df_skills = transform_skills(df_skills_raw)
    load_dimension(conn, df_skills, "skills_dim")
    
    df_role_fam = build_role_family_dim()
    load_dimension(conn, df_role_fam, "role_family_dim")

    logger.info("Building dynamic location, platform, and schedule dimensions from postings data...")
    import pandas as pd
    postings_path = get_csv_path("job_postings_fact.csv")
    df_p_sample = pd.read_csv(postings_path, usecols=['job_location', 'job_country', 'job_via', 'job_schedule_type'], low_memory=False)
    
    df_loc = build_location_dim(df_p_sample)
    load_dimension(conn, df_loc, "location_dim")
    
    df_plat = build_platform_dim(df_p_sample)
    load_dimension(conn, df_plat, "platform_dim")
    
    df_sched = build_schedule_dim(df_p_sample)
    load_dimension(conn, df_sched, "schedule_dim")
    
    elapsed = time.time() - start_time
    logger.info(f"=== COMPLETED DIMENSION ETL STAGE IN {elapsed:.2f}s ===")
    
    return {
        'comp_df': df_comp,
        'skills_df': df_skills,
        'role_fam_df': df_role_fam,
        'loc_df': df_loc,
        'plat_df': df_plat,
        'sched_df': df_sched
    }

def run_full_pipeline() -> None:
    """Run end-to-end ETL pipeline from empty/dirty state to verified warehouse."""
    total_start = time.time()
    logger.info("==================================================================")
    logger.info("         STARTING JOB MARKET ANALYTICS ETL PIPELINE               ")
    logger.info("==================================================================")
    
    conn = get_db_connection()
    try:
        dims = run_dimensions_pipeline(conn)
        
        loc_lookup = dict(zip(dims['loc_df']['location_raw'], dims['loc_df']['location_id']))
        plat_lookup = dict(zip(dims['plat_df']['platform_name'], dims['plat_df']['platform_id']))
        sched_lookup = dict(zip(dims['sched_df']['schedule_type'], dims['sched_df']['schedule_id']))
        from src.config import ROLE_FAMILY_MAP
        rf_name_to_id = dict(zip(dims['role_fam_df']['role_family_name'], dims['role_fam_df']['role_family_id']))
        title_short_to_rf_id = {t: rf_name_to_id[fam] for t, fam in ROLE_FAMILY_MAP.items()}
        
        company_id_set = set(dims['comp_df']['company_id'])
        skill_id_set = set(dims['skills_df']['skill_id'])
        
        logger.info("=== STARTING JOB POSTINGS FACT ETL STAGE (CHUNKED) ===")
        fact_start = time.time()
        total_postings_read = 0
        total_postings_loaded = 0
        total_postings_rejected = 0
        valid_job_ids: Set[int] = set()
        
        for idx, chunk in enumerate(extract_job_postings()):
            total_postings_read += len(chunk)
            df_valid, df_rej = transform_job_postings_chunk(
                chunk, loc_lookup, plat_lookup, sched_lookup,
                title_short_to_rf_id, company_id_set
            )
            
            if not df_rej.empty:
                total_postings_rejected += len(df_rej)
                log_rejected_rows(df_rej, "job_postings")
                
            loaded = load_fact_chunk(conn, df_valid)
            total_postings_loaded += loaded
            valid_job_ids.update(df_valid['job_id'])
            
            logger.info(f"Processed postings chunk {idx+1}: read {len(chunk):,}, loaded {loaded:,}, cumulative loaded: {total_postings_loaded:,}")

        fact_elapsed = time.time() - fact_start
        logger.info(f"=== COMPLETED FACT ETL STAGE: Loaded {total_postings_loaded:,} rows (Rejected {total_postings_rejected:,}) in {fact_elapsed:.2f}s ===")
        
        logger.info("=== STARTING SKILLS_JOB_DIM BRIDGE ETL STAGE (CHUNKED) ===")
        bridge_start = time.time()
        total_bridge_read = 0
        total_bridge_loaded = 0
        total_bridge_rejected = 0
        
        from src.config import MAX_BRIDGE_ROWS
        
        for idx, chunk in enumerate(extract_skills_job()):
            if MAX_BRIDGE_ROWS > 0 and total_bridge_loaded >= MAX_BRIDGE_ROWS:
                logger.info(f"Reached MAX_BRIDGE_ROWS safe cap ({MAX_BRIDGE_ROWS:,}). Concluded bridge loading to preserve cloud storage.")
                break
            total_bridge_read += len(chunk)
            df_valid_b, df_rej_b = transform_skills_job_chunk(chunk, valid_job_ids, skill_id_set)
            
            if not df_rej_b.empty:
                total_bridge_rejected += len(df_rej_b)
                log_rejected_rows(df_rej_b, "skills_job_bridge")
                
            loaded = load_bridge_chunk(conn, df_valid_b)
            total_bridge_loaded += loaded
            
            if (idx + 1) % 5 == 0 or idx == 0:
                logger.info(f"Processed bridge chunk {idx+1}: read {total_bridge_read:,}, loaded {total_bridge_loaded:,}")

        bridge_elapsed = time.time() - bridge_start
        logger.info(f"Completed bridge ETL stage: Loaded {total_bridge_loaded:,} rows in {bridge_elapsed:.2f}s")
        
        logger.info("=== OPTIMIZING QUERY STATISTICS (ANALYZE) ===")
        try:
            with conn.cursor() as cur:
                cur.execute("ANALYZE;")
            conn.commit()
            logger.info("Database statistics analyzed successfully.")
        except Exception as anz_err:
            logger.warning(f"Could not run ANALYZE: {anz_err}")
        
        logger.info("=== REFRESHING MATERIALIZED VIEWS ===")
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT refresh_all_materialized_views();")
            conn.commit()
            logger.info("All Materialized Views refreshed successfully.")
        except Exception as mv_err:
            logger.warning(f"Error calling refresh_all_materialized_views: {mv_err}. Trying individual refresh...")
            mv_list = [
                'mv_top_skills_overall', 'mv_top_skills_by_role_family', 'mv_top_skills_by_category',
                'mv_skill_demand_monthly', 'mv_salary_by_role_seniority', 'mv_skill_salary_premium',
                'mv_top_hiring_companies', 'mv_remote_work_rates', 'mv_degree_requirement_rates',
                'mv_health_insurance_rates', 'mv_pay_transparency', 'mv_platform_comparison'
            ]
            for mv in mv_list:
                try:
                    with conn.cursor() as cur:
                        cur.execute(f"REFRESH MATERIALIZED VIEW {mv};")
                    conn.commit()
                except Exception as ex:
                    logger.warning(f"Could not refresh {mv}: {ex}")
    finally:
        conn.close()
        
    logger.info("Running post-load validation")
    success = validate_post_load()
    
    total_elapsed = time.time() - total_start
    if success:
        logger.info(f"SUCCESS: ETL Pipeline completed end-to-end in {total_elapsed:.2f}s")
    else:
        logger.error(f"FAILURE: ETL Pipeline completed in {total_elapsed:.2f}s with validation errors.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Job Market Analytics ETL Pipeline Orchestrator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full", action="store_true", help="Execute complete end-to-end ETL pipeline")
    group.add_argument("--dimensions-only", action="store_true", help="Extract and load dimension tables only")
    group.add_argument("--validate-only", action="store_true", help="Execute post-load data quality validation assertions")
    
    args = parser.parse_args()
    
    if args.full:
        run_full_pipeline()
    elif args.dimensions_only:
        conn = get_db_connection()
        try:
            run_dimensions_pipeline(conn)
        finally:
            conn.close()
    elif args.validate_only:
        success = validate_post_load()
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()
