import unittest
from pathlib import Path

import pandas as pd

import app
from data_quality import audit_frame, enrich_records


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
        self.assertTrue((findings["metric"] == "dpi").any())

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


if __name__ == "__main__":
    unittest.main()
