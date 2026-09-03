"""Data transformation and normalization functions."""

import logging
from typing import Tuple, Dict, Set
import pandas as pd
import numpy as np

from src.config import (
    CANONICAL_SKILL_MAP,
    MULTI_TYPE_RESOLUTIONS,
    ROLE_FAMILY_MAP,
    ROLE_FAMILY_DESCRIPTIONS,
    DATA_REJECTS_DIR,
    EXCLUDE_SUDAN
)

logger = logging.getLogger(__name__)

DATA_REJECTS_DIR.mkdir(parents=True, exist_ok=True)

def log_rejected_rows(df_rejected: pd.DataFrame, source_name: str) -> None:
    """Write rejected rows to data/rejects/ with reason explanation."""
    if df_rejected.empty:
        return
    reject_path = DATA_REJECTS_DIR / f"{source_name}_rejected.csv"
    hdr = not reject_path.exists()
    df_rejected.to_csv(reject_path, mode='a', header=hdr, index=False)
    logger.warning(f"Logged {len(df_rejected):,} rejected rows to {reject_path}")

def transform_skills(df_skills: pd.DataFrame) -> pd.DataFrame:
    """
    Clean skills dimension:
    1. Resolve multi-type categories (sas, ruby, firebase).
    2. Build canonical_skill_id self-reference mapping for near-duplicates.
    """
    df = df_skills.copy()
    
    for skill_name, resolved_type in MULTI_TYPE_RESOLUTIONS.items():
        mask = df['skills'].str.lower() == skill_name
        df.loc[mask, 'type'] = resolved_type
        
    df = df.drop_duplicates(subset=['skill_id']).copy()

    name_to_id = dict(zip(df['skills'].str.lower(), df['skill_id']))
    
    canonical_ids = []
    is_canonical_flags = []
    
    for _, row in df.iterrows():
        raw_name = str(row['skills']).strip().lower()
        if raw_name in CANONICAL_SKILL_MAP:
            target_canonical = CANONICAL_SKILL_MAP[raw_name]
            parent_id = name_to_id.get(target_canonical, row['skill_id'])
            canonical_ids.append(parent_id)
            is_canonical_flags.append(False)
        else:
            canonical_ids.append(row['skill_id'])
            is_canonical_flags.append(True)

    df['canonical_skill_id'] = canonical_ids
    df['is_canonical'] = is_canonical_flags
    
    df['skill_id'] = df['skill_id'].astype('Int64')
    df['canonical_skill_id'] = df['canonical_skill_id'].astype('Int64')
    
    logger.info(f"Transformed skills_dim: {len(df):,} rows, {sum(~df['is_canonical']):,} duplicate mappings")
    return df

def transform_companies(df_company: pd.DataFrame) -> pd.DataFrame:
    """Clean company_dim data."""
    df = df_company.copy()
    df = df.drop_duplicates(subset=['company_id'])
    df['company_id'] = df['company_id'].astype('Int64')
    df['name'] = df['name'].fillna('Unknown Company')
    logger.info(f"Transformed company_dim: {len(df):,} rows")
    return df

def build_role_family_dim() -> pd.DataFrame:
    """Construct static role_family_dim DataFrame."""
    records = []
    family_names = sorted(list(set(ROLE_FAMILY_MAP.values())))
    for idx, fam in enumerate(family_names, 1):
        records.append({
            'role_family_id': idx,
            'role_family_name': fam,
            'description': ROLE_FAMILY_DESCRIPTIONS.get(fam, 'Tech role family')
        })
    df = pd.DataFrame(records)
    df['role_family_id'] = df['role_family_id'].astype('Int64')
    logger.info(f"Built role_family_dim: {len(df):,} families")
    return df

def build_location_dim(df_postings: pd.DataFrame) -> pd.DataFrame:
    """Extract deduplicated location_dim from raw job_location and job_country columns."""
    df_loc = df_postings[['job_location', 'job_country']].dropna(subset=['job_location']).copy()
    df_loc = df_loc.rename(columns={'job_location': 'location_raw', 'job_country': 'country'})
    
    df_loc['is_remote_marker'] = df_loc['location_raw'].str.strip().str.lower() == 'anywhere'
    
    df_loc['country'] = np.where(
        df_loc['country'].isna() | (df_loc['country'].str.strip() == ''),
        np.where(df_loc['is_remote_marker'], 'Remote / Worldwide', 'Unknown'),
        df_loc['country']
    )
    
    df_loc = df_loc.drop_duplicates(subset=['location_raw']).copy()
    
    def parse_city(loc_raw):
        if str(loc_raw).strip().lower() == 'anywhere':
            return None
        parts = str(loc_raw).split(',')
        return parts[0].strip() if len(parts) > 1 else str(loc_raw).strip()
        
    df_loc['city'] = df_loc['location_raw'].apply(parse_city)
    df_loc = df_loc.reset_index(drop=True)
    df_loc['location_id'] = (df_loc.index + 1).astype('Int64')
    
    logger.info(f"Built location_dim: {len(df_loc):,} unique locations")
    return df_loc[['location_id', 'location_raw', 'city', 'country', 'is_remote_marker']]

def build_platform_dim(df_postings: pd.DataFrame) -> pd.DataFrame:
    """Extract deduplicated platform_dim from raw job_via column (stripping 'via ' prefix)."""
    raw_vias = df_postings['job_via'].dropna().unique()
    platforms = set()
    for v in raw_vias:
        v_str = str(v).strip()
        if v_str.lower().startswith('via '):
            v_str = v_str[4:].strip()
        if v_str:
            platforms.add(v_str)
            
    records = [{'platform_id': idx + 1, 'platform_name': name} for idx, name in enumerate(sorted(list(platforms)))]
    df_plat = pd.DataFrame(records)
    df_plat['platform_id'] = df_plat['platform_id'].astype('Int64')
    logger.info(f"Built platform_dim: {len(df_plat):,} unique platforms")
    return df_plat

def build_schedule_dim(df_postings: pd.DataFrame) -> pd.DataFrame:
    """Extract deduplicated schedule_dim from raw job_schedule_type column."""
    raw_schedules = df_postings['job_schedule_type'].dropna().unique()
    records = []
    for idx, sched in enumerate(sorted([str(s).strip() for s in raw_schedules]), 1):
        sched_lower = sched.lower()
        records.append({
            'schedule_id': idx,
            'schedule_type': sched,
            'is_full_time': 'full-time' in sched_lower,
            'is_contract': 'contract' in sched_lower,
            'is_part_time': 'part-time' in sched_lower
        })
    df_sched = pd.DataFrame(records)
    df_sched['schedule_id'] = df_sched['schedule_id'].astype('Int64')
    logger.info(f"Built schedule_dim: {len(df_sched):,} unique schedule types")
    return df_sched

def transform_job_postings_chunk(
    df_chunk: pd.DataFrame,
    loc_lookup: Dict[str, int],
    plat_lookup: Dict[str, int],
    sched_lookup: Dict[str, int],
    role_fam_lookup: Dict[str, int],
    company_id_set: Set[int]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Clean, validate, and enrich a chunk of job_postings_fact."""
    df = df_chunk.copy()
    rejects = []
    
    if EXCLUDE_SUDAN:
        sudan_mask = df['job_country'] == 'Sudan'
        if sudan_mask.any():
            sudan_df = df[sudan_mask].copy()
            sudan_df['rejection_reason'] = 'Sudan anomaly exclusion flag'
            rejects.append(sudan_df)
            df = df[~sudan_mask].copy()
            
    is_senior = df['job_title_short'].str.startswith('Senior ', na=False)
    df['seniority'] = np.where(is_senior, 'Senior', 'Mid-Entry')
    df['base_role'] = np.where(is_senior, df['job_title_short'].str.replace('Senior ', '', regex=False), df['job_title_short'])
    
    df['job_title'] = df['job_title'].fillna(df['job_title_short']).fillna('Unknown Title')
    
    df['role_family_id'] = df['job_title_short'].map(role_fam_lookup)
    df['location_id'] = df['job_location'].map(loc_lookup)
    
    def clean_via(val):
        if pd.isna(val): return None
        v = str(val).strip()
        return v[4:].strip() if v.lower().startswith('via ') else v
    df['clean_via'] = df['job_via'].apply(clean_via)
    df['platform_id'] = df['clean_via'].map(plat_lookup)
    
    df['schedule_id'] = df['job_schedule_type'].str.strip().map(sched_lookup)
    
    comp_invalid_mask = df['company_id'].notna() & (~df['company_id'].isin(company_id_set))
    if comp_invalid_mask.any():
        comp_rej = df[comp_invalid_mask].copy()
        comp_rej['rejection_reason'] = 'Orphaned company_id FK'
        rejects.append(comp_rej)
        df.loc[comp_invalid_mask, 'company_id'] = None
        
    neg_salary_mask = (df['salary_year_avg'] < 0) | (df['salary_hour_avg'] < 0)
    if neg_salary_mask.any():
        neg_sal_df = df[neg_salary_mask].copy()
        neg_sal_df['rejection_reason'] = 'Negative salary value'
        rejects.append(neg_sal_df)
        df = df[~neg_salary_mask].copy()

    valid_rates = {'year', 'hour', 'month', 'week', 'day'}
    df['salary_rate'] = df['salary_rate'].apply(
        lambda r: str(r).strip().lower() if pd.notna(r) and str(r).strip().lower() in valid_rates else None
    )
        
    df['job_posted_date'] = pd.to_datetime(df['job_posted_date'], errors='coerce')
    bad_date_mask = df['job_posted_date'].isna()
    if bad_date_mask.any():
        bad_date_df = df[bad_date_mask].copy()
        bad_date_df['rejection_reason'] = 'Invalid posted timestamp'
        rejects.append(bad_date_df)
        df = df[~bad_date_mask].copy()

    for bool_col in ['job_work_from_home', 'job_no_degree_mention', 'job_health_insurance']:
        df[bool_col] = df[bool_col].fillna(False).astype(bool)

    int_id_cols = ['job_id', 'company_id', 'location_id', 'platform_id', 'schedule_id', 'role_family_id']
    for col in int_id_cols:
        df[col] = df[col].astype('Int64')

    cols = [
        'job_id', 'company_id', 'location_id', 'platform_id', 'schedule_id',
        'role_family_id', 'job_title', 'job_title_short', 'base_role',
        'seniority', 'job_work_from_home', 'job_no_degree_mention',
        'job_health_insurance', 'job_posted_date', 'salary_rate',
        'salary_year_avg', 'salary_hour_avg'
    ]
    df_valid = df[cols].copy()
    df_rejected = pd.concat(rejects, ignore_index=True) if rejects else pd.DataFrame()
    return df_valid, df_rejected

def transform_skills_job_chunk(
    df_chunk: pd.DataFrame,
    valid_job_ids: Set[int],
    valid_skill_ids: Set[int]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validate skills_job_dim bridge chunk for valid job_id and skill_id foreign keys."""
    df = df_chunk.copy()
    rejects = []
    
    invalid_mask = (~df['job_id'].isin(valid_job_ids)) | (~df['skill_id'].isin(valid_skill_ids))
    if invalid_mask.any():
        rej_df = df[invalid_mask].copy()
        rej_df['rejection_reason'] = 'Orphaned bridge FK (job_id or skill_id)'
        rejects.append(rej_df)
        df = df[~invalid_mask].copy()
        
    df_valid = df.drop_duplicates(subset=['job_id', 'skill_id'])[['job_id', 'skill_id']]
    df_valid['job_id'] = df_valid['job_id'].astype('Int64')
    df_valid['skill_id'] = df_valid['skill_id'].astype('Int64')
    df_rejected = pd.concat(rejects, ignore_index=True) if rejects else pd.DataFrame()
    return df_valid, df_rejected
