from __future__ import annotations

import io
import unittest

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

from data_utils import combine_selected_data, filter_columns, filter_rows_by_time, parse_uploaded_data, parse_uploaded_workbook, search_table
from plotting import FIGURE_PRESETS, PLOT_TYPES, PlotConfig, create_figure, export_figure


class CoreTests(unittest.TestCase):
    def test_cross_file_selection_preserves_samples_and_labels(self):
        first = pd.DataFrame({"x": [0, 0, 2], "signal": [10, 11, 12], "excluded": [99, 99, 99]})
        second = pd.DataFrame({"x": [0, 1, 2], "signal": [20, 21, 22]})
        sources = [("A", first, "x", ["signal"]), ("B", second, "x", ["signal"])]
        combined, x_name = combine_selected_data(sources)
        self.assertEqual(len(combined), 4)
        self.assertEqual(combined.columns.tolist(), [x_name, "A · signal", "B · signal"])
        self.assertEqual(combined["A · signal"].dropna().tolist(), [10, 11, 12])
        self.assertEqual(combined["B · signal"].dropna().tolist(), [20, 21, 22])
        config = PlotConfig(plot_type="Comparison plot", timestamp_column=x_name, columns=["A · signal", "B · signal"])
        figure = create_figure(combined, config)
        self.assertEqual([line.get_label() for line in figure.axes[0].lines], config.columns)
        self.assertEqual(figure.axes[0].lines[0].get_ydata().tolist(), [10, 11, 12])
        self.assertEqual(figure.axes[0].lines[1].get_xdata().tolist(), [0, 1, 2])

    def test_sample_alignment_and_empty_selection(self):
        sources = [("A", pd.DataFrame({"x": [10, 11], "v": [1, 2]}), "x", ["v"]),
                   ("B", pd.DataFrame({"x": [40], "v": [3]}), "x", ["v"])]
        combined, x_name = combine_selected_data(sources, "Sample index")
        self.assertEqual(combined[x_name].tolist(), [0, 1])
        self.assertTrue(pd.isna(combined["B · v"].iloc[1]))
        with self.assertRaises(ValueError):
            combine_selected_data([])

    def setUp(self) -> None:
        count = 128
        self.frame = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-01-01", periods=count, freq="100ms"),
                "signal_a": np.sin(np.linspace(0, 8 * np.pi, count)),
                "signal_b": np.cos(np.linspace(0, 6 * np.pi, count)),
                "error": np.linspace(-1, 1, count),
            }
        )

    def config(self, plot_type: str) -> PlotConfig:
        return PlotConfig(
            plot_type=plot_type,
            timestamp_column="timestamp",
            columns=["signal_a", "signal_b", "error"],
            x_column="signal_a",
            figure_preset=next(iter(FIGURE_PRESETS)),
            sampling_rate=10.0,
            max_lag=20,
        )

    def test_workbook_parsing_and_filters(self) -> None:
        buffer = io.BytesIO()
        self.frame.assign(timestamp=self.frame["timestamp"].astype(str)).to_excel(buffer, index=False)
        parsed, timestamp, note = parse_uploaded_workbook(buffer.getvalue())
        self.assertEqual(timestamp, "timestamp")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(parsed[timestamp]))
        self.assertIn("Parsed", note)
        self.assertEqual(filter_columns(parsed.columns.tolist(), "SIGNAL"), ["signal_a", "signal_b"])
        visible = filter_rows_by_time(parsed, timestamp, parsed[timestamp].iloc[4], parsed[timestamp].iloc[9])
        self.assertEqual(len(visible), 6)
        self.assertGreaterEqual(len(search_table(parsed[["error"]], "-1.0")), 1)

    def test_csv_and_tab_delimited_parsing(self) -> None:
        csv_bytes = self.frame.to_csv(index=False).encode("utf-8")
        csv_frame, csv_timestamp, _ = parse_uploaded_data(csv_bytes, "measurements.csv")
        self.assertEqual(csv_timestamp, "timestamp")
        self.assertEqual(len(csv_frame), len(self.frame))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(csv_frame[csv_timestamp]))

        tsv_bytes = self.frame.to_csv(index=False, sep="\t").encode("utf-8")
        tsv_frame, tsv_timestamp, _ = parse_uploaded_data(tsv_bytes, "measurements.txt")
        self.assertEqual(tsv_timestamp, "timestamp")
        self.assertEqual(tsv_frame.columns.tolist(), self.frame.columns.tolist())

    def test_every_plot_renders(self) -> None:
        for plot_type in PLOT_TYPES:
            with self.subTest(plot_type=plot_type):
                figure = create_figure(self.frame, self.config(plot_type))
                self.assertTrue(figure.axes)

    def test_export_formats(self) -> None:
        figure = create_figure(self.frame, self.config("Time series"))
        svg = export_figure(figure, "svg", dpi=120)
        png = export_figure(figure, "png", dpi=120)
        jpg = export_figure(figure, "jpg", dpi=120)
        self.assertTrue(svg.lstrip().startswith(b"<?xml"))
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertTrue(jpg.startswith(b"\xff\xd8"))


if __name__ == "__main__":
    unittest.main()
