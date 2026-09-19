from __future__ import annotations

import hashlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from data_utils import (
    combine_selected_data,
    excel_sheet_names,
    filter_columns,
    filter_rows_by_time,
    parse_uploaded_data,
    search_table,
)
from plotting import (
    FIGURE_PRESETS,
    PLOT_TYPES,
    THEMES,
    PlotConfig,
    create_figure,
    export_figure,
    numeric_columns,
)


st.set_page_config(
    page_title="IEEE Plot Studio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --ink:#12212f; --accent:#0b6bcb; --muted:#5d6a76; --line:#dce3e9; }
    .stApp { background: #f4f7f9; color: var(--ink); }
    [data-testid="stSidebar"] { background: #0d1d2a; }
    [data-testid="stSidebar"] * { color: #f3f7fa; }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea { color: #12212f !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] * { color: #12212f; }
    .block-container { max-width: 1540px; padding-top: 1.4rem; }
    .app-title { font-size: 2rem; font-weight: 760; letter-spacing: -0.035em; margin: 0; }
    .app-kicker { color: #0b6bcb; font-size: .78rem; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; }
    .app-subtitle { color: var(--muted); margin: .2rem 0 1.2rem; max-width: 780px; }
    .metric-strip { display:flex; gap:.55rem; flex-wrap:wrap; margin:.25rem 0 1rem; }
    .metric-chip { background:white; border:1px solid var(--line); border-radius:999px; padding:.35rem .7rem; font-size:.82rem; }
    [data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-color:var(--line); border-radius:12px; }
    .stButton button, .stDownloadButton button { border-radius:8px; font-weight:650; }
    .stButton button[kind="primary"] { background:#0b6bcb; border-color:#0b6bcb; }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
    h1, h2, h3 { color:var(--ink); letter-spacing:-.02em; }
    </style>
    """,
    unsafe_allow_html=True,
)


def clear_export_cache() -> None:
    st.session_state.pop("exports", None)
    st.session_state.pop("export_key", None)


cached_parse = st.cache_data(max_entries=32, show_spinner=False)(parse_uploaded_data)
cached_sheets = st.cache_data(max_entries=32, show_spinner=False)(excel_sheet_names)


st.markdown('<div class="app-kicker">Research figure workspace</div>', unsafe_allow_html=True)
st.markdown('<div class="app-title">IEEE Plot Studio</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Inspect timestamped Excel, CSV, or tab-delimited data, compose publication-ready figures, and export vector or 1200-DPI artwork.</div>',
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("Load data", icon=":material/upload_file:")
    st.caption(
        "Add one or more Excel workbooks, CSV files, or tab-delimited text files. "
        "The first column should contain timestamps when time-based plotting is required."
    )
    uploads = st.file_uploader(
        "Choose data files",
        type=["xlsx", "xlsm", "xls", "csv", "tsv", "txt"],
        accept_multiple_files=True,
        help="Supported formats: .xlsx, .xlsm, .xls, .csv, .tsv, and tab-delimited .txt.",
        on_change=clear_export_cache,
    )

if not uploads:
    st.info(
        "Upload at least one .xlsx, .xlsm, .xls, .csv, .tsv, or tab-delimited .txt file to begin.",
        icon=":material/info:",
    )

if not uploads:
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Expected workbook layout")
            example = pd.DataFrame(
                {
                    "timestamp": ["2026-01-01 10:00:00", "2026-01-01 10:00:01", "2026-01-01 10:00:02"],
                    "joint_angle_deg": [11.2, 11.8, 12.4],
                    "motor_current_a": [0.71, 0.75, 0.73],
                    "tracking_error_mm": [1.9, 1.3, 0.8],
                }
            )
            st.dataframe(example, width="stretch", hide_index=True)
    with right:
        with st.container(border=True):
            st.subheader("Built for publication")
            st.markdown(
                "IEEE single- and double-column dimensions, restrained scientific themes, configurable labels and legends, plus SVG, PNG, and JPG exports."
            )
            st.caption("Timestamp parsing, missing-value handling, and numeric-column checks are built in.")
    st.stop()

sources = []
source_signature = []
with st.container(border=True):
    st.subheader("Select columns to plot")
    st.caption("Choose any number of measurement columns from each file. Only these selections are plotted.")
    alignment = st.selectbox(
        "Align files by", ["First column", "Sample index"],
        help="First column matches timestamps or X values exactly. Sample index compares row positions starting at zero.",
        on_change=clear_export_cache,
    )
    for index, upload in enumerate(uploads):
        file_bytes = upload.getvalue()
        digest = hashlib.sha256(file_bytes).hexdigest()
        source_key = f"{index}_{digest}"
        label = f"{index + 1}. {upload.name}"
        with st.expander(label, expanded=True):
            sheet = 0
            try:
                if upload.name.casefold().endswith((".xlsx", ".xlsm", ".xls")):
                    sheet = st.selectbox(
                        "Worksheet", cached_sheets(file_bytes, upload.name),
                        key=f"sheet_{source_key}", on_change=clear_export_cache,
                    )
                    label += f" / {sheet}"
                with st.spinner(f"Reading {upload.name}…"):
                    frame, x_name, note = cached_parse(file_bytes, upload.name, sheet)
            except Exception as exc:
                st.error(f"{upload.name} could not be read: {exc}")
                continue
            if frame.empty:
                st.warning("This file or worksheet has no data rows.")
                continue
            choices = numeric_columns(frame, exclude=[x_name])
            columns = st.multiselect(
                "Columns to plot", choices, default=[],
                key=f"columns_{source_key}_{sheet}", on_change=clear_export_cache,
            )
            st.caption(f"{len(frame):,} rows · X: {x_name}. {note}")
            sources.append((label, frame, x_name, columns))
            source_signature.append((upload.name, digest, sheet, columns))

try:
    data, timestamp_column = combine_selected_data(sources, alignment)
except ValueError as exc:
    st.info(str(exc))
    st.stop()

plot_tab, data_tab = st.tabs(["Figure studio", "Data inspector"])
original_columns = data.columns.tolist()
# Keep aliases separate from widget state so deselecting a series does not
# discard its name. Scope them to the uploaded files and worksheets.
rename_scope = hashlib.sha256(repr(([(name, digest, sheet) for name, digest, sheet, _ in source_signature], alignment)).encode()).hexdigest()
rename_key = f"column_names_{rename_scope}"
aliases = st.session_state.get(rename_key, {})
with data_tab:
    with st.expander("Rename columns for all plots", expanded=True):
        st.caption("Edit Plot name, then apply. Names are used in the table, plot axes, legends, and exports. Each name must be non-empty and unique.")
        with st.form(f"rename_form_{rename_scope}"):
            name_table = st.data_editor(
                pd.DataFrame({"Original column": original_columns,
                              "Plot name": [aliases.get(column, column) for column in original_columns]}),
                disabled=["Original column"], hide_index=True, width="stretch",
                key=f"rename_editor_{rename_scope}_{hashlib.sha256(repr(original_columns).encode()).hexdigest()}",
                column_config={"Plot name": st.column_config.TextColumn("Plot name", required=True)},
            )
            apply_names = st.form_submit_button("Apply column names", on_click=clear_export_cache)
        if apply_names:
            names = [str(value).strip() if pd.notna(value) else "" for value in name_table["Plot name"]]
            if not all(names):
                st.error("Column names cannot be blank. The previous names are still in use.")
            elif len(set(names)) != len(names):
                st.error("Column names must be unique, including the time column. The previous names are still in use.")
            else:
                aliases = {**aliases, **dict(zip(original_columns, names))}
                st.session_state[rename_key] = aliases
                st.success("Column names applied to the table and all plots.")

renamed_columns = [aliases.get(column, column) for column in original_columns]
if len(set(renamed_columns)) != len(renamed_columns):
    st.warning("The selected columns have conflicting saved names. Assign unique names in Data inspector to continue.")
    st.stop()
data = data.rename(columns=aliases)
timestamp_column = aliases.get(timestamp_column, timestamp_column)
selected_series = data.columns[1:].tolist()
all_numeric = selected_series
parse_note = "Selected columns from all files; missing matches are left empty without interpolation."
st.caption(f"Plotting {len(selected_series)} selected series. Rename their labels in Data inspector.")

with st.sidebar:
    st.divider()
    st.subheader("2 · Choose figure")
    plot_type = st.selectbox("Plot type", PLOT_TYPES, on_change=clear_export_cache)

    x_column = None
    if plot_type == "Scatter plot":
        x_options = [timestamp_column] + all_numeric
        x_column = st.selectbox("X variable", x_options, on_change=clear_export_cache)

    normalize = False
    if plot_type == "Comparison plot":
        normalize = st.checkbox("Normalize each series (z-score)", value=False, on_change=clear_export_cache)

    aggregation = "Mean"
    if plot_type == "Summary bar chart":
        aggregation = st.selectbox("Summary statistic", ["Mean", "Median", "Minimum", "Maximum"], on_change=clear_export_cache)

    max_lag = 50
    if plot_type == "Autocorrelation":
        max_lag = st.number_input("Maximum lag", min_value=2, max_value=10000, value=50, step=1, on_change=clear_export_cache)

    sampling_rate = 0.0
    if plot_type in {"FFT spectrum", "Power spectral density", "Spectrogram"}:
        sampling_rate = st.number_input(
            "Sampling rate override (Hz)", min_value=0.0, value=0.0, step=1.0,
            help="Leave at 0 to infer it from timestamps.", on_change=clear_export_cache,
        )

    st.divider()
    st.subheader("3 · Publication style")
    theme = st.selectbox(
        "Theme",
        list(THEMES),
        on_change=clear_export_cache,
    )
    figure_preset = st.selectbox("Figure size", list(FIGURE_PRESETS), on_change=clear_export_cache)
    title = st.text_input("Figure title", value="", placeholder="Optional", on_change=clear_export_cache)
    x_label = st.text_input("X-axis label", value="", placeholder="Automatic", on_change=clear_export_cache)
    y_label = st.text_input("Y-axis label", value="", placeholder="Automatic", on_change=clear_export_cache)
    legend_title = st.text_input("Legend title", value="", placeholder="Optional", on_change=clear_export_cache)
    legend_columns = st.number_input("Legend columns", min_value=1, max_value=6, value=2, on_change=clear_export_cache)
    legend_labels = {}
    with st.expander("Custom legend names"):
        st.caption("Leave a name blank to use the original file and column label.")
        for series in selected_series:
            custom_name = st.text_input(series, key=f"legend_{series}", on_change=clear_export_cache)
            legend_labels[series] = custom_name.strip() or series

    c1, c2 = st.columns(2)
    with c1:
        show_grid = st.checkbox("Grid", value=True, on_change=clear_export_cache)
        show_legend = st.checkbox("Legend", value=True, on_change=clear_export_cache)
    with c2:
        log_x = st.checkbox("Log X", value=False, on_change=clear_export_cache)
        log_y = st.checkbox("Log Y", value=False, on_change=clear_export_cache)

    line_width = st.slider("Line width", 0.5, 3.0, 1.2, 0.1, on_change=clear_export_cache)
    marker_size = st.slider("Marker size", 1.0, 10.0, 3.5, 0.5, on_change=clear_export_cache)

filtered = data
time_range_label = "All records"
date_axis = pd.api.types.is_datetime64_any_dtype(data[timestamp_column])
numeric_axis = pd.api.types.is_numeric_dtype(data[timestamp_column])
range_mode = st.selectbox("Time / sample range", ["All records", "Exact range", "Slider"] if date_axis else ["All records", "Exact range"])
if range_mode == "Exact range" and (date_axis or numeric_axis):
    left, right = st.columns(2)
    range_key = hashlib.sha256(repr((source_signature, alignment)).encode()).hexdigest()
    with left:
        start_text = st.text_input("Range start", str(data[timestamp_column].min()), key=f"start_{range_key}",
                                   help="Use a full date/time for timestamps, or a number for numeric time/sample indices.")
    with right:
        end_text = st.text_input("Range end", str(data[timestamp_column].max()), key=f"end_{range_key}")
    try:
        start = pd.Timestamp(start_text) if date_axis else float(start_text)
        end = pd.Timestamp(end_text) if date_axis else float(end_text)
        if pd.isna(start) or pd.isna(end) or start > end:
            raise ValueError("Range start must be at or before range end.")
        filtered = data.loc[data[timestamp_column].between(start, end, inclusive="both")]
        time_range_label = f"{start} → {end}"
    except (ValueError, TypeError) as exc:
        st.error(f"Invalid range: {exc}")
        st.stop()
elif range_mode == "Exact range":
    st.info("Use Sample index alignment to filter data whose first column is text.")
elif range_mode == "Slider" and date_axis and data[timestamp_column].notna().sum() > 1:
    valid_times = data[timestamp_column].dropna()
    t_min, t_max = valid_times.min(), valid_times.max()
    if t_min < t_max:
        selected_range = st.slider(
            "Timeframe",
            min_value=t_min.to_pydatetime(),
            max_value=t_max.to_pydatetime(),
            value=(t_min.to_pydatetime(), t_max.to_pydatetime()),
            format="YYYY-MM-DD HH:mm:ss",
            on_change=clear_export_cache,
        )
        filtered = filter_rows_by_time(data, timestamp_column, selected_range[0], selected_range[1])
        time_range_label = f"{selected_range[0]:%Y-%m-%d %H:%M:%S} → {selected_range[1]:%Y-%m-%d %H:%M:%S}"

annotations = []
if plot_type != "Pair plot":
    with st.expander("Reference lines and shaded bands"):
        st.caption(
            "Add rows for horizontal/vertical lines or faded bands. Start is the line position or band start; "
            "End is used only for bands. Horizontal values use Y-axis units; vertical values use X-axis units "
            "(full date/time for timestamp plots). Optional labels appear in the legend below the graph."
        )
        reference_rows = st.data_editor(
            pd.DataFrame(columns=["Kind", "Start", "End", "Label", "Color", "Opacity"]),
            num_rows="dynamic", key="reference_annotations", hide_index=True, width="stretch",
            column_config={
                "Kind": st.column_config.SelectboxColumn("Kind", options=["Horizontal line", "Vertical line", "Horizontal band", "Vertical band"], required=True, default="Horizontal line"),
                "Start": st.column_config.TextColumn("Start", required=True),
                "End": st.column_config.TextColumn("End"),
                "Label": st.column_config.TextColumn("Legend label"),
                "Color": st.column_config.TextColumn("Color", default="#64748B", help="A color name or hex value, e.g. #2563EB."),
                "Opacity": st.column_config.NumberColumn("Band opacity", min_value=0.0, max_value=1.0, default=0.15, step=0.05),
            },
        )
        for row in reference_rows.to_dict("records"):
            item = {key: None if pd.isna(value) else value for key, value in row.items()}
            if not item["Kind"] or not item["Start"] or (item["Kind"].endswith("band") and not item["End"]):
                st.warning("Complete the kind, start, and (for bands) end before plotting.")
                st.stop()
            item["Opacity"] = 0.15 if item["Opacity"] is None else item["Opacity"]
            annotations.append(item)

st.markdown(
    f'<div class="metric-strip"><span class="metric-chip">{len(filtered):,} visible rows</span>'
    f'<span class="metric-chip">{len(data.columns)} columns</span>'
    f'<span class="metric-chip">Timestamp: {timestamp_column}</span>'
    f'<span class="metric-chip">{time_range_label}</span></div>',
    unsafe_allow_html=True,
)

with data_tab:
    with st.container(border=True):
        top_a, top_b = st.columns([1, 1])
        with top_a:
            column_query = st.text_input("Search columns", placeholder="e.g. velocity or current")
        available_columns = filter_columns(data.columns.tolist(), column_query)
        with top_b:
            visible_columns = st.multiselect(
                "Columns in table",
                available_columns,
                default=available_columns[: min(8, len(available_columns))],
            )
        row_query = st.text_input("Search displayed rows", placeholder="Search text or numeric values")
        table = filtered.loc[:, visible_columns] if visible_columns else filtered.iloc[:, 0:0]
        table = search_table(table, row_query)
        st.dataframe(table, width="stretch", height=470, hide_index=True)
        st.caption(f"Showing {len(table):,} matching rows. {parse_note}")

with plot_tab:
    if not all_numeric:
        st.error("No numeric data columns were found. Check that measurement columns contain numbers.")
        st.stop()
    if not selected_series:
        st.info("Choose at least one numeric data column from the sidebar.")
        st.stop()

    config = PlotConfig(
        plot_type=plot_type,
        timestamp_column=timestamp_column,
        columns=selected_series,
        x_column=x_column,
        title=title,
        x_label=x_label,
        y_label=y_label,
        legend_title=legend_title,
        legend_labels=legend_labels,
        legend_columns=int(legend_columns),
        annotations=annotations,
        theme=theme,
        figure_preset=figure_preset,
        show_grid=show_grid,
        show_legend=show_legend,
        log_x=log_x,
        log_y=log_y,
        line_width=line_width,
        marker_size=marker_size,
        normalize=normalize,
        aggregation=aggregation,
        max_lag=int(max_lag),
        sampling_rate=float(sampling_rate),
    )

    try:
        figure = create_figure(filtered, config)
    except ValueError as exc:
        st.warning(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"This figure could not be generated: {exc}")
        st.stop()

    figure_col, export_col = st.columns([4.2, 1.3], gap="large")
    with figure_col:
        with st.container(border=True):
            st.pyplot(figure, width="stretch")

    export_signature = hashlib.sha256(
        repr((source_signature, alignment, time_range_label, config)).encode()
    ).hexdigest()

    with export_col:
        with st.container(border=True):
            st.subheader("Export")
            st.caption("Raster files are rendered at 1200 DPI. SVG remains resolution-independent.")
            if st.button("Prepare publication files", type="primary", width="stretch"):
                with st.spinner("Rendering high-resolution files…"):
                    st.session_state.exports = {
                        "svg": export_figure(figure, "svg", dpi=1200),
                        "png": export_figure(figure, "png", dpi=1200),
                        "jpg": export_figure(figure, "jpg", dpi=1200),
                    }
                    st.session_state.export_key = export_signature

            if st.session_state.get("export_key") == export_signature:
                exports = st.session_state.exports
                stem = "publication_figure"
                st.download_button("Download SVG", exports["svg"], f"{stem}.svg", "image/svg+xml", width="stretch")
                st.download_button("Download PNG · 1200 DPI", exports["png"], f"{stem}.png", "image/png", width="stretch")
                st.download_button("Download JPG · 1200 DPI", exports["jpg"], f"{stem}.jpg", "image/jpeg", width="stretch")
                st.success("Files are ready.")
            else:
                st.caption("Prepare files after the figure looks right.")

            st.divider()
            width, height = FIGURE_PRESETS[figure_preset]
            st.markdown(f"**Canvas**  \n{width:.2f} × {height:.2f} in")
            st.markdown("**Raster output**  \n1200 DPI")

    plt.close(figure)
