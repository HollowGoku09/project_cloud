-- Indexes for foreign keys, filter predicates, and join keys

-- Foreign Key Indexes on job_postings_fact
CREATE INDEX IF NOT EXISTS idx_job_postings_company_id ON job_postings_fact(company_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_location_id ON job_postings_fact(location_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_platform_id ON job_postings_fact(platform_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_schedule_id ON job_postings_fact(schedule_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_role_family_id ON job_postings_fact(role_family_id);

-- Filter & Analysis Indexes on job_postings_fact
CREATE INDEX IF NOT EXISTS idx_job_postings_posted_date ON job_postings_fact(job_posted_date);
CREATE INDEX IF NOT EXISTS idx_job_postings_seniority ON job_postings_fact(seniority);
-- High-Value Filter Indexes on job_postings_fact
CREATE INDEX IF NOT EXISTS idx_job_postings_salary_year_avg ON job_postings_fact(salary_year_avg) WHERE salary_year_avg IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_job_postings_title_short ON job_postings_fact(job_title_short);

-- Indexes on Dimension Tables
CREATE INDEX IF NOT EXISTS idx_location_country ON location_dim(country);
CREATE INDEX IF NOT EXISTS idx_skills_type ON skills_dim(type);
CREATE INDEX IF NOT EXISTS idx_skills_canonical_id ON skills_dim(canonical_skill_id);

-- Indexes on Bridge Table (PRIMARY KEY already indexes (job_id, skill_id) and job_id prefix)
CREATE INDEX IF NOT EXISTS idx_skills_job_skill_id ON skills_job_dim(skill_id);
