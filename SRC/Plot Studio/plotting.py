from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PLOT_TYPES = [
    "Time series",
    "Box plot",
    "Comparison plot",
    "Scatter plot",
    "Histogram",
    "Violin plot",
    "Summary bar chart",
    "Correlation heatmap",
    "Pair plot",
    "Autocorrelation",
    "FFT spectrum",
    "Power spectral density",
    "Spectrogram",
]

FIGURE_PRESETS: dict[str, tuple[float, float]] = {
    "IEEE single column · 3.50 × 2.63 in": (3.50, 2.63),
    "IEEE double column · 7.16 × 3.50 in": (7.16, 3.50),
    "Square · 4.00 × 4.00 in": (4.00, 4.00),
    "Full width · 7.16 × 5.00 in": (7.16, 5.00),
}

THEMES = {
    "Modern Research": {
        "colors": ["#2563EB", "#E76F51", "#089981", "#8B5CF6", "#D99A00", "#64748B"],
        "font": "DejaVu Sans",
        "grid": "#E2E8F0",
        "face": "#FFFFFF",
        "ink": "#243247",
    },
    "IEEE Classic": {
        "colors": ["#0057A8", "#D1495B", "#00876C", "#7A5195", "#E07A1F", "#444444"],
        "font": "DejaVu Serif",
        "grid": "#D4D9DE",
        "face": "#FFFFFF",
        "ink": "#111111",
    },
    "IEEE Grayscale": {
        "colors": ["#111111", "#555555", "#888888", "#B0B0B0", "#333333", "#747474"],
        "font": "DejaVu Serif",
        "grid": "#D0D0D0",
        "face": "#FFFFFF",
        "ink": "#111111",
    },
    "Q1 Clean": {
        "colors": ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"],
        "font": "DejaVu Sans",
        "grid": "#DDE3E8",
        "face": "#FFFFFF",
        "ink": "#17212B",
    },
    "High Contrast": {
        "colors": ["#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442"],
        "font": "DejaVu Sans",
        "grid": "#C7CDD2",
        "face": "#FFFFFF",
        "ink": "#000000",
    },
}


@dataclass(frozen=True)
class PlotConfig:
    plot_type: str
    timestamp_column: str
    columns: list[str]
    x_column: str | None = None
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    legend_title: str = ""
    theme: str = "IEEE Classic"
    figure_preset: str = "IEEE single column · 3.50 × 2.63 in"
    show_grid: bool = True
    show_legend: bool = True
    log_x: bool = False
    log_y: bool = False
    line_width: float = 1.2
    marker_size: float = 3.5
    normalize: bool = False
    aggregation: str = "Mean"
    max_lag: int = 50
    sampling_rate: float = 0.0
    legend_labels: dict[str, str] = field(default_factory=dict)
    legend_columns: int = 2
    annotations: list[dict] = field(default_factory=list)


def numeric_columns(frame: pd.DataFrame, exclude: list[str] | None = None) -> list[str]:
    excluded = set(exclude or [])
    return [
        column for column in frame.select_dtypes(include=np.number).columns.tolist()
        if column not in excluded
    ]


def _style_context(config: PlotConfig) -> dict[str, object]:
    theme = THEMES[config.theme]
    return {
        "font.family": theme["font"],
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "axes.linewidth": 0.8,
        "axes.edgecolor": theme["ink"],
        "axes.labelcolor": theme["ink"],
        "axes.facecolor": theme["face"],
        "figure.facecolor": theme["face"],
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "xtick.color": theme["ink"],
        "ytick.color": theme["ink"],
        "legend.fontsize": 7,
        "legend.frameon": False,
        "lines.linewidth": config.line_width,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "axes.prop_cycle": mpl.cycler(color=theme["colors"]),
    }


def _clean_series(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    valid = [column for column in columns if column in frame and pd.api.types.is_numeric_dtype(frame[column])]
    if not valid:
        raise ValueError("Choose at least one numeric data column.")
    return frame[valid].replace([np.inf, -np.inf], np.nan)


def _time_axis(frame: pd.DataFrame, timestamp_column: str) -> tuple[pd.Series, str]:
    if timestamp_column in frame:
        return frame[timestamp_column], timestamp_column
    return pd.Series(frame.index, index=frame.index), "Sample"


def _sampling_rate(frame: pd.DataFrame, config: PlotConfig) -> float:
    if config.sampling_rate > 0:
        return config.sampling_rate
    values = frame[config.timestamp_column] if config.timestamp_column in frame else None
    if values is not None and pd.api.types.is_datetime64_any_dtype(values):
        seconds = values.dropna().sort_values().diff().dt.total_seconds()
        median_dt = seconds[seconds > 0].median()
        if pd.notna(median_dt) and median_dt > 0:
            return 1.0 / float(median_dt)
    return 1.0


def create_figure(frame: pd.DataFrame, config: PlotConfig) -> plt.Figure:
    if frame.empty:
        raise ValueError("The selected timeframe contains no records.")
    if config.plot_type not in PLOT_TYPES:
        raise ValueError("Unsupported plot type.")

    data = _clean_series(frame, config.columns)
    figsize = FIGURE_PRESETS[config.figure_preset]
    theme = THEMES[config.theme]

    with mpl.rc_context(_style_context(config)):
        if config.plot_type == "Pair plot":
            figure = _pair_plot(data, figsize, config)
            axes = list(figure.axes)
        else:
            figure, axis = plt.subplots(figsize=figsize, constrained_layout=True)
            axes = [axis]
            _draw(axis, frame, data, config, theme)

        if config.title:
            if config.plot_type == "Pair plot":
                figure.suptitle(config.title, fontsize=9, y=1.01)
            else:
                axes[0].set_title(config.title, pad=7, fontweight="semibold")

        for axis in axes:
            axis.tick_params(direction="out", length=3, width=0.7)
            if config.log_x:
                axis.set_xscale("log")
            if config.log_y:
                axis.set_yscale("log")
            if config.show_grid and config.plot_type != "Pair plot":
                axis.grid(True, color=theme["grid"], linewidth=0.55, alpha=0.85)
                axis.set_axisbelow(True)
            else:
                axis.grid(False)
            sns.despine(ax=axis, trim=False)

        if config.plot_type != "Pair plot":
            _add_annotations(axes[0], frame, config)
            handles, names = axes[0].get_legend_handles_labels()
            if config.show_legend and handles:
                figure.legend(
                    handles, [config.legend_labels.get(name, name) for name in names],
                    title=config.legend_title or None, loc="outside lower center",
                    ncol=config.legend_columns, frameon=False,
                )

        return figure


def _add_annotations(axis: plt.Axes, frame: pd.DataFrame, config: PlotConfig) -> None:
    """Draw reference lines and translucent bands in the displayed axis units."""
    time_x = config.plot_type in {"Time series", "Comparison plot"} or (
        config.plot_type == "Scatter plot" and (config.x_column or config.timestamp_column) == config.timestamp_column
    )
    date_x = time_x and pd.api.types.is_datetime64_any_dtype(frame[config.timestamp_column])
    for item in config.annotations:
        kind = item["Kind"]
        vertical = kind.startswith("Vertical")
        def coordinate(value):
            if vertical and date_x:
                result = pd.Timestamp(value)
                if pd.isna(result):
                    raise ValueError("Enter a valid timestamp for vertical annotations.")
                return result
            result = float(value)
            if not np.isfinite(result):
                raise ValueError("Reference positions must be finite numbers.")
            return result
        start = coordinate(item["Start"])
        color = item.get("Color") or "#64748B"
        label = item.get("Label") or "_nolegend_"
        if kind.endswith("band"):
            end = coordinate(item["End"])
            if end <= start:
                raise ValueError("A shaded band's end must be greater than its start.")
            draw = axis.axvspan if vertical else axis.axhspan
            draw(start, end, color=color, alpha=float(item.get("Opacity", 0.15)), label=label, zorder=0)
        else:
            draw = axis.axvline if vertical else axis.axhline
            draw(start, color=color, linestyle="--", linewidth=1.0, label=label)


def _draw(axis: plt.Axes, frame: pd.DataFrame, data: pd.DataFrame, config: PlotConfig, theme: dict) -> None:
    kind = config.plot_type
    x, automatic_x_label = _time_axis(frame, config.timestamp_column)
    labels = data.columns.tolist()

    if kind in {"Time series", "Comparison plot"}:
        values = data.copy()
        if kind == "Comparison plot" and config.normalize:
            std = values.std(ddof=0).replace(0, np.nan)
            values = (values - values.mean()) / std
        for column in values:
            valid = x.notna() & values[column].notna()
            axis.plot(x[valid], values.loc[valid, column], label=column, marker=None)
        default_y = "Normalized amplitude" if config.normalize else "Value"
        _labels(axis, config, automatic_x_label, default_y)

    elif kind == "Box plot":
        clean = [data[column].dropna().to_numpy() for column in labels]
        axis.boxplot(
            clean,
            tick_labels=labels,
            patch_artist=True,
            medianprops={"color": "#111111", "linewidth": 1.1},
            boxprops={"facecolor": theme["colors"][0], "alpha": 0.55, "linewidth": 0.8},
            whiskerprops={"linewidth": 0.8},
            capprops={"linewidth": 0.8},
            flierprops={"markersize": max(1.5, config.marker_size * 0.7), "alpha": 0.45},
        )
        axis.tick_params(axis="x", rotation=25)
        _labels(axis, config, "Series", "Value")

    elif kind == "Scatter plot":
        x_name = config.x_column or config.timestamp_column
        if x_name not in frame:
            raise ValueError("Choose a valid X variable.")
        for column in labels:
            if column == x_name:
                continue
            axis.scatter(frame[x_name], data[column], s=config.marker_size**2, alpha=0.75, label=column, edgecolors="none")
        _labels(axis, config, x_name, "Value")

    elif kind == "Histogram":
        for column in labels:
            axis.hist(data[column].dropna(), bins="auto", alpha=0.5, label=column, edgecolor="white", linewidth=0.35)
        _labels(axis, config, "Value", "Frequency")

    elif kind == "Violin plot":
        clean = [data[column].dropna().to_numpy() for column in labels]
        parts = axis.violinplot(clean, showmeans=True, showextrema=True)
        for body, color in zip(parts["bodies"], theme["colors"] * 10):
            body.set_facecolor(color)
            body.set_edgecolor("black")
            body.set_alpha(0.65)
        axis.set_xticks(range(1, len(labels) + 1), labels, rotation=25)
        _labels(axis, config, "Series", "Value")

    elif kind == "Summary bar chart":
        aggregations = {"Mean": "mean", "Median": "median", "Minimum": "min", "Maximum": "max"}
        values = getattr(data, aggregations[config.aggregation])()
        axis.bar(labels, values, edgecolor="black", linewidth=0.45)
        axis.tick_params(axis="x", rotation=25)
        _labels(axis, config, "Series", config.aggregation)

    elif kind == "Correlation heatmap":
        if len(labels) < 2:
            raise ValueError("A correlation heatmap needs at least two data columns.")
        sns.heatmap(
            data.corr(), ax=axis, cmap="vlag", center=0, vmin=-1, vmax=1,
            annot=len(labels) <= 8, fmt=".2f", square=True,
            cbar_kws={"label": "Pearson r", "shrink": 0.8},
        )
        _labels(axis, config, config.x_label, config.y_label)

    elif kind == "Autocorrelation":
        for column in labels:
            series = data[column].dropna().to_numpy(dtype=float)
            if len(series) < 3:
                continue
            centered = series - series.mean()
            variance = np.dot(centered, centered)
            lag_count = min(config.max_lag, len(series) - 1)
            corr = np.correlate(centered, centered, mode="full")[len(series) - 1: len(series) + lag_count]
            corr = corr / variance if variance else np.zeros_like(corr)
            axis.plot(np.arange(lag_count + 1), corr, label=column)
        axis.axhline(0, color="#555555", linewidth=0.7)
        _labels(axis, config, "Lag (samples)", "Autocorrelation")

    elif kind == "FFT spectrum":
        for column in labels:
            sample_rate = _sampling_rate(frame.loc[data[column].notna()], config)
            series = data[column].dropna().to_numpy(dtype=float)
            if len(series) < 4:
                continue
            centered = series - series.mean()
            frequencies = np.fft.rfftfreq(len(centered), d=1.0 / sample_rate)
            amplitude = 2.0 * np.abs(np.fft.rfft(centered)) / len(centered)
            axis.plot(frequencies, amplitude, label=column)
        _labels(axis, config, "Frequency (Hz)", "Amplitude")

    elif kind == "Power spectral density":
        for column in labels:
            sample_rate = _sampling_rate(frame.loc[data[column].notna()], config)
            series = data[column].dropna().to_numpy(dtype=float)
            if len(series) < 8:
                continue
            nfft = min(256, 2 ** int(np.floor(np.log2(len(series)))))
            axis.psd(series - series.mean(), NFFT=nfft, Fs=sample_rate, label=column)
        _labels(axis, config, "Frequency (Hz)", "Power / frequency (dB/Hz)")

    elif kind == "Spectrogram":
        column = labels[0]
        series = data[column].dropna().to_numpy(dtype=float)
        if len(series) < 16:
            raise ValueError("A spectrogram needs at least 16 valid samples.")
        sample_rate = _sampling_rate(frame.loc[data[column].notna()], config)
        nfft = min(256, 2 ** int(np.floor(np.log2(len(series) / 2))))
        spectrum = axis.specgram(series - series.mean(), NFFT=max(8, nfft), Fs=sample_rate, noverlap=max(0, nfft // 2))[3]
        colorbar = axis.figure.colorbar(spectrum, ax=axis, pad=0.02)
        colorbar.set_label("Power (dB)", fontsize=8)
        colorbar.ax.tick_params(labelsize=7)
        _labels(axis, config, "Time (s)", "Frequency (Hz)")

    # The figure-level legend is added after reference lines and bands so it
    # includes their optional labels and reserves space below the axes.


def _labels(axis: plt.Axes, config: PlotConfig, default_x: str, default_y: str) -> None:
    axis.set_xlabel(config.x_label or default_x)
    axis.set_ylabel(config.y_label or default_y)


def _pair_plot(data: pd.DataFrame, figsize: tuple[float, float], config: PlotConfig) -> plt.Figure:
    selected = data.iloc[:, :5].dropna()
    if selected.shape[1] < 2:
        raise ValueError("A pair plot needs at least two data columns.")
    if selected.empty:
        raise ValueError("No complete rows are available for the selected pair-plot columns.")

    count = selected.shape[1]
    side = max(figsize[0], figsize[1], 1.35 * count)
    figure, axes = plt.subplots(count, count, figsize=(side, side), squeeze=False, constrained_layout=True)
    colors = THEMES[config.theme]["colors"]
    for row, y_name in enumerate(selected.columns):
        for column, x_name in enumerate(selected.columns):
            axis = axes[row, column]
            if row == column:
                axis.hist(selected[x_name], bins="auto", color=colors[row % len(colors)], alpha=0.75)
            else:
                axis.scatter(selected[x_name], selected[y_name], s=config.marker_size**2, alpha=0.55, edgecolors="none")
            axis.set_xlabel(x_name if row == count - 1 else "")
            axis.set_ylabel(y_name if column == 0 else "")
            if row != count - 1:
                axis.tick_params(labelbottom=False)
            if column != 0:
                axis.tick_params(labelleft=False)
    return figure


def export_figure(figure: plt.Figure, file_format: str, dpi: int = 1200) -> bytes:
    normalized = file_format.lower()
    if normalized not in {"svg", "png", "jpg", "jpeg"}:
        raise ValueError("Export format must be SVG, PNG, or JPG.")
    buffer = BytesIO()
    save_format = "jpeg" if normalized in {"jpg", "jpeg"} else normalized
    figure.savefig(
        buffer,
        format=save_format,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.04,
        facecolor="white",
        metadata={"Creator": "IEEE Plot Studio"} if save_format in {"svg", "png"} else None,
    )
    return buffer.getvalue()
