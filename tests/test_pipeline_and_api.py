"""Unit tests for data transforms and API endpoints."""

import unittest
import pandas as pd
from src.config import CANONICAL_SKILL_MAP
from src.transform import transform_skills
from src.validate import validate_dataframe_integrity
from app.server import WebBIHandler

class TestPipelineAndAPI(unittest.TestCase):

    def test_expanded_canonical_skills(self):
        """Test newly added skill variants map to correct canonical names."""
        self.assertEqual(CANONICAL_SKILL_MAP.get("scikitlearn"), "scikit-learn")
        self.assertEqual(CANONICAL_SKILL_MAP.get("pyspark"), "spark")
        self.assertEqual(CANONICAL_SKILL_MAP.get("postgres"), "postgresql")
        self.assertEqual(CANONICAL_SKILL_MAP.get("k8s"), "kubernetes")
        self.assertEqual(CANONICAL_SKILL_MAP.get("tf"), "tensorflow")
        self.assertEqual(CANONICAL_SKILL_MAP.get("reactjs"), "react")

    def test_transform_skills_expanded(self):
        """Verify expanded canonical skills transform correctly in DataFrame."""
        df_sample = pd.DataFrame([
            {"skill_id": 1, "skills": "scikitlearn", "type": "libraries"},
            {"skill_id": 2, "skills": "scikit-learn", "type": "libraries"},
            {"skill_id": 3, "skills": "pyspark", "type": "libraries"},
            {"skill_id": 4, "skills": "spark", "type": "libraries"},
            {"skill_id": 5, "skills": "k8s", "type": "other"}
        ])
        
        transformed = transform_skills(df_sample)
        
        row_sklearn_variant = transformed[transformed['skill_id'] == 1].iloc[0]
        self.assertFalse(row_sklearn_variant['is_canonical'])
        self.assertEqual(row_sklearn_variant['canonical_skill_id'], 2)

        row_pyspark_variant = transformed[transformed['skill_id'] == 3].iloc[0]
        self.assertFalse(row_pyspark_variant['is_canonical'])
        self.assertEqual(row_pyspark_variant['canonical_skill_id'], 4)

    def test_dataframe_integrity_validator(self):
        """Verify validate_dataframe_integrity flags missing columns and duplicates."""
        df_valid = pd.DataFrame([
            {"job_id": 1, "job_title": "Data Engineer", "salary_year_avg": 120000},
            {"job_id": 2, "job_title": "Data Analyst", "salary_year_avg": 90000}
        ])
        res_valid = validate_dataframe_integrity(df_valid, ["job_id", "job_title"])
        self.assertTrue(res_valid["is_valid"])
        self.assertEqual(res_valid["duplicate_job_ids"], 0)

        df_invalid = pd.DataFrame([
            {"job_id": 1, "job_title": "Data Engineer"},
            {"job_id": 1, "job_title": "Duplicate Engineer"}
        ])
        res_invalid = validate_dataframe_integrity(df_invalid, ["job_id", "job_title"])
        self.assertFalse(res_invalid["is_valid"])
        self.assertEqual(res_invalid["duplicate_job_ids"], 1)

    def test_server_health_status(self):
        """Verify server health endpoint returns valid status schema."""
        handler = WebBIHandler.__new__(WebBIHandler)
        health = handler.get_health_status()
        self.assertEqual(health["status"], "healthy")
        self.assertIn("timestamp", health)
        self.assertIn("version", health)

    def test_server_export_data(self):
        """Verify server export endpoint returns structured dataset lists."""
        handler = WebBIHandler.__new__(WebBIHandler)
        export = handler.get_export_data("skills")
        self.assertIsInstance(export, list)
        self.assertTrue(len(export) > 0)
        self.assertIn("skill_name", export[0])

    def test_career_gap_analysis(self):
        """Verify career gap analysis calculates missing skills and salary uplift."""
        handler = WebBIHandler.__new__(WebBIHandler)
        gap = handler.get_career_gap_analysis("Data Engineer", "SQL,Python")
        self.assertEqual(gap["target_role"], "Data Engineer")
        missing_names = [s["name"] for s in gap["missing_skills"]]
        self.assertIn("potential_salary_boost", gap)
        self.assertIn("readiness_score", gap)

    def test_neon_db_connection_kwargs(self):
        """Verify get_db_connection_kwargs properly constructs connection dicts."""
        from src.config import get_db_connection_kwargs
        kwargs = get_db_connection_kwargs()
        self.assertIsInstance(kwargs, dict)
        self.assertTrue("dsn" in kwargs or "host" in kwargs)

if __name__ == "__main__":
    unittest.main()

