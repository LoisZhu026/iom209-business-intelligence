import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class PipelineOutputTests(unittest.TestCase):
    def test_group_cleaning_snapshot_is_preserved(self) -> None:
        source_dir = ROOT / "upstream" / "group_cleaning"
        self.assertTrue((source_dir / "step1_restaurant_context.ipynb").is_file())
        self.assertTrue((source_dir / "menu_classification_reference.csv").is_file())
        manifest = (source_dir / "README.md").read_text(encoding="utf-8")
        self.assertIn("17,534", manifest)
        self.assertIn("restaurant_sales_data_enriched.csv", manifest)

    def test_model_dataset_is_complete(self) -> None:
        data = pd.read_csv(ROOT / "data" / "processed" / "final_model_dataset.csv")
        self.assertEqual(len(data), 24)
        self.assertEqual(data["YearMonth"].iloc[0], "2022-01")
        self.assertEqual(data["YearMonth"].iloc[-1], "2023-12")
        self.assertEqual(int(data.isna().sum().sum()), 0)
        self.assertGreater(float(data["Coverage_Rate"].min()), 0.89)
        self.assertTrue(0.91 < float(data["Coverage_Rate"].mean()) < 0.93)

    def test_model_outputs_have_expected_scope(self) -> None:
        result_dir = ROOT / "results" / "tables"
        metrics = pd.read_csv(result_dir / "model_metrics.csv")
        predictions = pd.read_csv(result_dir / "test_predictions.csv")
        forecast = pd.read_csv(result_dir / "forecast_jan_mar_2024.csv")
        self.assertEqual(metrics["Model"].tolist(), [
            "Historical Mean Baseline",
            "Linear Regression",
            "Random Forest",
        ])
        self.assertEqual(len(predictions), 6)
        self.assertEqual(
            forecast["Forecast_Target_Month"].tolist(),
            ["2024-01", "2024-02", "2024-03"],
        )

    def test_scripts_do_not_depend_on_a_user_home_path(self) -> None:
        for path in (ROOT / "scripts").glob("*.py"):
            self.assertNotIn("/Users/", path.read_text(encoding="utf-8"), path.name)


if __name__ == "__main__":
    unittest.main()
