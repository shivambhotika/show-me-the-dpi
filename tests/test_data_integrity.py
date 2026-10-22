import unittest
import tempfile
from pathlib import Path

import pandas as pd

import app
from data_quality import audit_frame, enrich_records
from scripts import refresh


ROOT = Path(__file__).resolve().parents[1]


class DataIntegrityTests(unittest.TestCase):
    def test_metrics_are_not_silently_converted_to_zero(self):
        df = pd.DataFrame({
            "fund_name": ["Fund A"],
            "vintage_year": [2020],
            "source": ["Test"],
            "reporting_period": ["2025-Q4"],
            "capital_contributed": [100.0],
            "capital_distributed": [None],
            "nav": [None],
            "dpi": [None],
            "tvpi": [None],
            "net_irr": [None],
        })
        enriched = enrich_records(df, ROOT)
        self.assertTrue(pd.isna(enriched.loc[0, "dpi"]))
        self.assertTrue(pd.isna(enriched.loc[0, "tvpi"]))

    def test_inconsistent_dpi_is_reported(self):
        df = pd.DataFrame({
            "fund_name": ["Fund A"], "vintage_year": [2010], "source": ["Test"], "reporting_period": ["2025-Q4"],
            "capital_contributed": [100.0], "capital_distributed": [25.0], "nav": [50.0], "dpi": [0.9], "tvpi": [0.75], "net_irr": [0.1],
        })
        findings = audit_frame(df, source_name="test")
        self.assertTrue((findings["metric"] == "dpi/tvpi").any())
        self.assertEqual(findings.loc[findings["metric"].eq("dpi/tvpi"), "severity"].iloc[0], "disputed")
        self.assertTrue((findings["metric"] == "dpi").any())

    def test_source_inconsistency_is_not_verified(self):
        df = pd.DataFrame({
            "fund_name": ["Fund A"], "vintage_year": [2010], "source": ["Test"], "reporting_period": ["2025-Q4"],
            "capital_contributed": [100.0], "capital_distributed": [125.0], "nav": [0.0], "dpi": [1.25], "tvpi": [1.0],
        })
        enriched = enrich_records(df, ROOT)
        self.assertEqual(enriched.loc[0, "verification_status"], "disputed-source")
        self.assertIn("exceeds", enriched.loc[0, "dispute_reason"])

    def test_app_routes_render(self):
        client = app.app.test_client()
        for path in ["/healthz", "/?page=insights", "/?page=sources", "/?page=audit", "/?page=pe_comparison"]:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_market_data_is_separate_from_master(self):
        market = app.load_market()
        self.assertEqual(len(market), len(pd.read_csv(ROOT / "gp_disclosed_funds.csv")))
        self.assertTrue(set(market["data_source_type"].dropna()) <= {"GP-Disclosed"})

    def test_refresh_approval_supports_external_snapshot_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(refresh.display_path(Path(tmp) / "snapshot.csv"), str(Path(tmp) / "snapshot.csv"))

    def test_source_registry_is_classified_without_being_fund_data(self):
        registry = pd.read_csv(ROOT / "data" / "external_benchmark_sources.csv")
        self.assertGreaterEqual(len(registry), 6)
        self.assertIn("Ribbit Capital Perspective", set(registry["name"]))
        ribbit = registry.loc[registry["name"].eq("Ribbit Capital Perspective")].iloc[0]
        self.assertEqual(ribbit["status"], "Monitor")
        self.assertNotIn("unified_funds.csv", str(ribbit.to_dict()))


if __name__ == "__main__":
    unittest.main()
