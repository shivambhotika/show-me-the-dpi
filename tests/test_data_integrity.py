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
        for path in ["/healthz", "/?page=about", "/?page=insights", "/?page=fund_database", "/?page=sources", "/?page=audit", "/?page=pe_comparison"]:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_freshness_is_exposed_without_collapsing_dates(self):
        loaded = app.page_data()
        self.assertEqual(set(loaded["freshness"]), {"fund_date", "context_date", "metadata_date", "check_date"})
        self.assertNotEqual(loaded["freshness"]["fund_date"], loaded["freshness"]["check_date"])

    def test_fund_database_has_identity_for_every_visible_row(self):
        response = app.app.test_client().get("/?page=fund_database")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertGreaterEqual(body.count('class="logo-wrap"'), body.count("<tr>") - 1)

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

    def test_refresh_change_report_detects_added_changed_removed(self):
        old = pd.DataFrame({
            "fund_name": ["A", "B"], "vintage_year": [2010, 2011], "source": ["S", "S"], "reporting_period": ["P", "P"],
            "dpi": [1.0, 0.2],
        })
        new = pd.DataFrame({
            "fund_name": ["A", "C"], "vintage_year": [2010, 2012], "source": ["S", "S"], "reporting_period": ["P", "P"],
            "dpi": [1.2, 0.1],
        })
        diff = refresh.build_change_report(new, old)
        self.assertEqual(set(diff["change_type"]), {"new", "removed", "changed"})
        self.assertTrue(((diff["change_type"] == "changed") & (diff["field"] == "dpi")).any())

    def test_refresh_change_report_does_not_churn_missing_keys(self):
        frame = pd.DataFrame({
            "fund_name": ["A"], "vintage_year": [None], "source": ["S"], "reporting_period": ["P"], "dpi": [1.0],
        })
        diff = refresh.build_change_report(frame, frame.copy())
        self.assertTrue(diff.empty)


if __name__ == "__main__":
    unittest.main()
