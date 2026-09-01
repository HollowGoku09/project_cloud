-- Materialized views for analytical aggregations

-- 1. Top Skills Overall
CREATE MATERIALIZED VIEW mv_top_skills_overall AS
SELECT 
    s.skill_id,
    s.skills AS skill_name,
    s.type AS skill_type,
    COUNT(sj.job_id) AS demand_count,
    ROUND(COUNT(sj.job_id)::NUMERIC / (SELECT COUNT(*) FROM job_postings_fact) * 100, 2) AS pct_of_total_postings
FROM skills_dim s
JOIN skills_job_dim sj ON s.skill_id = sj.skill_id
JOIN job_postings_fact j ON sj.job_id = j.job_id
WHERE s.is_canonical = TRUE
GROUP BY s.skill_id, s.skills, s.type;

CREATE UNIQUE INDEX idx_mv_top_skills_overall_id ON mv_top_skills_overall(skill_id);

-- 2. Top Skills by Role Family
CREATE MATERIALIZED VIEW mv_top_skills_by_role_family AS
SELECT 
    rf.role_family_id,
    rf.role_family_name,
    j.seniority,
    s.skill_id,
    s.skills AS skill_name,
    s.type AS skill_type,
    COUNT(j.job_id) AS posting_count,
    DENSE_RANK() OVER (
        PARTITION BY rf.role_family_id, j.seniority 
        ORDER BY COUNT(j.job_id) DESC
    ) AS rank_in_family
FROM job_postings_fact j
JOIN role_family_dim rf ON j.role_family_id = rf.role_family_id
JOIN skills_job_dim sj ON j.job_id = sj.job_id
JOIN skills_dim s ON sj.skill_id = s.skill_id
WHERE s.is_canonical = TRUE
GROUP BY rf.role_family_id, rf.role_family_name, j.seniority, s.skill_id, s.skills, s.type;

CREATE INDEX idx_mv_skills_rf_id ON mv_top_skills_by_role_family(role_family_id, seniority);

-- 3. Top Skills by Category
CREATE MATERIALIZED VIEW mv_top_skills_by_category AS
SELECT 
    s.type AS skill_type,
    s.skill_id,
    s.skills AS skill_name,
    COUNT(sj.job_id) AS demand_count,
    DENSE_RANK() OVER (
        PARTITION BY s.type 
        ORDER BY COUNT(sj.job_id) DESC
    ) AS rank_in_type
FROM skills_dim s
JOIN skills_job_dim sj ON s.skill_id = sj.skill_id
WHERE s.is_canonical = TRUE
GROUP BY s.type, s.skill_id, s.skills;

CREATE INDEX idx_mv_skills_cat_type ON mv_top_skills_by_category(skill_type);

-- 4. Monthly Skill Demand Trend
CREATE MATERIALIZED VIEW mv_skill_demand_monthly AS
SELECT 
    TO_CHAR(j.job_posted_date, 'YYYY-MM') AS year_month,
    rf.role_family_id,
    s.skill_id,
    s.skills AS skill_name,
    s.type AS skill_type,
    COUNT(j.job_id) AS monthly_postings
FROM job_postings_fact j
JOIN role_family_dim rf ON j.role_family_id = rf.role_family_id
JOIN skills_job_dim sj ON j.job_id = sj.job_id
JOIN skills_dim s ON sj.skill_id = s.skill_id
WHERE s.is_canonical = TRUE
GROUP BY TO_CHAR(j.job_posted_date, 'YYYY-MM'), rf.role_family_id, s.skill_id, s.skills, s.type;

CREATE INDEX idx_mv_skill_monthly ON mv_skill_demand_monthly(year_month, role_family_id);

-- 5. Salary by Role Family and Seniority
CREATE MATERIALIZED VIEW mv_salary_by_role_seniority AS
SELECT 
    rf.role_family_id,
    rf.role_family_name,
    j.seniority,
    l.country,
    COUNT(j.job_id) AS total_postings,
    COUNT(j.salary_year_avg) AS postings_with_salary,
    ROUND(COUNT(j.salary_year_avg)::NUMERIC / COUNT(j.job_id) * 100, 2) AS pct_disclosed,
    ROUND(AVG(j.salary_year_avg), 2) AS avg_yearly_salary,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY j.salary_year_avg)::NUMERIC, 2) AS median_yearly_salary,
    ROUND(MIN(j.salary_year_avg), 2) AS min_yearly_salary,
    ROUND(MAX(j.salary_year_avg), 2) AS max_yearly_salary
FROM job_postings_fact j
JOIN role_family_dim rf ON j.role_family_id = rf.role_family_id
JOIN location_dim l ON j.location_id = l.location_id
GROUP BY rf.role_family_id, rf.role_family_name, j.seniority, l.country;

CREATE INDEX idx_mv_salary_rf_country ON mv_salary_by_role_seniority(role_family_id, country);

-- 6. Salary Premium Per Skill
CREATE MATERIALIZED VIEW mv_skill_salary_premium AS
WITH global_sal AS (
    SELECT AVG(salary_year_avg) AS global_avg
    FROM job_postings_fact
    WHERE salary_year_avg IS NOT NULL
)
SELECT 
    s.skill_id,
    s.skills AS skill_name,
    s.type AS skill_type,
    COUNT(j.job_id) AS postings_with_salary,
    ROUND(AVG(j.salary_year_avg), 2) AS avg_salary_with_skill,
    ROUND((SELECT global_avg FROM global_sal), 2) AS global_avg_salary,
    ROUND(AVG(j.salary_year_avg) - (SELECT global_avg FROM global_sal), 2) AS salary_premium_usd,
    ROUND(((AVG(j.salary_year_avg) - (SELECT global_avg FROM global_sal)) / (SELECT global_avg FROM global_sal)) * 100, 2) AS pct_salary_premium
FROM skills_dim s
JOIN skills_job_dim sj ON s.skill_id = sj.skill_id
JOIN job_postings_fact j ON sj.job_id = j.job_id
WHERE j.salary_year_avg IS NOT NULL
  AND s.is_canonical = TRUE
GROUP BY s.skill_id, s.skills, s.type
HAVING COUNT(j.job_id) >= 50;

CREATE UNIQUE INDEX idx_mv_skill_sal_prem_id ON mv_skill_salary_premium(skill_id);

-- 7. Top Hiring Companies
CREATE MATERIALIZED VIEW mv_top_hiring_companies AS
SELECT 
    c.company_id,
    c.name AS company_name,
    c.thumbnail,
    COUNT(j.job_id) AS total_postings,
    COUNT(j.salary_year_avg) AS salaried_postings_count,
    ROUND(AVG(j.salary_year_avg), 2) AS avg_salary_usd
FROM company_dim c
JOIN job_postings_fact j ON c.company_id = j.company_id
GROUP BY c.company_id, c.name, c.thumbnail;

CREATE UNIQUE INDEX idx_mv_top_comp_id ON mv_top_hiring_companies(company_id);

-- 8. Remote Work Rates
CREATE MATERIALIZED VIEW mv_remote_work_rates AS
SELECT 
    l.country,
    rf.role_family_id,
    rf.role_family_name,
    j.seniority,
    COUNT(j.job_id) AS total_postings,
    SUM(CASE WHEN j.job_work_from_home THEN 1 ELSE 0 END) AS remote_postings_count,
    ROUND(SUM(CASE WHEN j.job_work_from_home THEN 1 ELSE 0 END)::NUMERIC / COUNT(j.job_id) * 100, 2) AS remote_work_pct
FROM job_postings_fact j
JOIN location_dim l ON j.location_id = l.location_id
JOIN role_family_dim rf ON j.role_family_id = rf.role_family_id
GROUP BY l.country, rf.role_family_id, rf.role_family_name, j.seniority;

CREATE INDEX idx_mv_remote_cntry ON mv_remote_work_rates(country, role_family_id);

-- 9. Degree Requirement Rates
CREATE MATERIALIZED VIEW mv_degree_requirement_rates AS
SELECT 
    rf.role_family_id,
    rf.role_family_name,
    j.seniority,
    COUNT(j.job_id) AS total_postings,
    SUM(CASE WHEN j.job_no_degree_mention THEN 1 ELSE 0 END) AS no_degree_mention_count,
    ROUND(SUM(CASE WHEN j.job_no_degree_mention THEN 1 ELSE 0 END)::NUMERIC / COUNT(j.job_id) * 100, 2) AS no_degree_mention_pct,
    ROUND(100 - (SUM(CASE WHEN j.job_no_degree_mention THEN 1 ELSE 0 END)::NUMERIC / COUNT(j.job_id) * 100), 2) AS degree_required_or_preferred_pct
FROM job_postings_fact j
JOIN role_family_dim rf ON j.role_family_id = rf.role_family_id
GROUP BY rf.role_family_id, rf.role_family_name, j.seniority;

-- 10. Health Insurance Rates
CREATE MATERIALIZED VIEW mv_health_insurance_rates AS
SELECT 
    l.country,
    COUNT(j.job_id) AS total_postings,
    SUM(CASE WHEN j.job_health_insurance THEN 1 ELSE 0 END) AS health_insurance_offered_count,
    ROUND(SUM(CASE WHEN j.job_health_insurance THEN 1 ELSE 0 END)::NUMERIC / COUNT(j.job_id) * 100, 2) AS health_insurance_offer_pct
FROM job_postings_fact j
JOIN location_dim l ON j.location_id = l.location_id
GROUP BY l.country;

-- 11. Pay Transparency Rates
CREATE MATERIALIZED VIEW mv_pay_transparency AS
SELECT 
    l.country,
    rf.role_family_id,
    rf.role_family_name,
    COUNT(j.job_id) AS total_postings,
    COUNT(j.salary_year_avg) AS postings_with_salary_disclosed,
    ROUND(COUNT(j.salary_year_avg)::NUMERIC / COUNT(j.job_id) * 100, 2) AS pay_transparency_pct
FROM job_postings_fact j
JOIN location_dim l ON j.location_id = l.location_id
JOIN role_family_dim rf ON j.role_family_id = rf.role_family_id
GROUP BY l.country, rf.role_family_id, rf.role_family_name;

-- 12. Platform Comparison
CREATE MATERIALIZED VIEW mv_platform_comparison AS
SELECT 
    p.platform_name,
    rf.role_family_id,
    rf.role_family_name,
    COUNT(j.job_id) AS posting_volume,
    COUNT(j.salary_year_avg) AS salaried_postings_count,
    ROUND(COUNT(j.salary_year_avg)::NUMERIC / COUNT(j.job_id) * 100, 2) AS salary_disclosure_rate_pct,
    ROUND(AVG(j.salary_year_avg), 2) AS avg_disclosed_salary_usd
FROM job_postings_fact j
JOIN platform_dim p ON j.platform_id = p.platform_id
JOIN role_family_dim rf ON j.role_family_id = rf.role_family_id
GROUP BY p.platform_name, rf.role_family_id, rf.role_family_name;

-- Refresh Script Function
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_top_skills_overall;
    REFRESH MATERIALIZED VIEW mv_top_skills_by_role_family;
    REFRESH MATERIALIZED VIEW mv_top_skills_by_category;
    REFRESH MATERIALIZED VIEW mv_skill_demand_monthly;
    REFRESH MATERIALIZED VIEW mv_salary_by_role_seniority;
    REFRESH MATERIALIZED VIEW mv_skill_salary_premium;
    REFRESH MATERIALIZED VIEW mv_top_hiring_companies;
    REFRESH MATERIALIZED VIEW mv_remote_work_rates;
    REFRESH MATERIALIZED VIEW mv_degree_requirement_rates;
    REFRESH MATERIALIZED VIEW mv_health_insurance_rates;
    REFRESH MATERIALIZED VIEW mv_pay_transparency;
    REFRESH MATERIALIZED VIEW mv_platform_comparison;
END;
$$ LANGUAGE plpgsql;
