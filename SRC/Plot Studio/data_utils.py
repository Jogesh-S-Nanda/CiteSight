from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

import pandas as pd


EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}
DELIMITED_EXTENSIONS = {".csv", ".tsv", ".txt"}


def combine_selected_data(sources, alignment="First column"):
    """Align selected source columns without interpolation or duplicate-key expansion.

    Sources are (unique label, dataframe, x column, selected columns) tuples.
    Repeated x values pair by occurrence; unmatched samples remain missing.
    """
    parts = []
    kinds = set()
    for label, frame, x_column, columns in sources:
        if not columns:
            continue
        part = frame.loc[:, columns].copy()
        part.columns = [f"{label} · {column}" for column in columns]
        if alignment == "Sample index":
            part.index = pd.RangeIndex(len(part), name="Sample")
        else:
            x = frame[x_column].reset_index(drop=True)
            kinds.add("datetime" if pd.api.types.is_datetime64_any_dtype(x)
                      else "numeric" if pd.api.types.is_numeric_dtype(x) else "text")
            if x.isna().any():
                raise ValueError("Some first-column values are missing. Choose Sample index or correct those values.")
            occurrence = x.groupby(x, sort=False).cumcount()
            part.index = pd.MultiIndex.from_arrays([x, occurrence], names=["Time / X", "Occurrence"])
        parts.append(part)
    if not parts:
        raise ValueError("Select at least one data column from the uploaded files.")
    if len(kinds) > 1:
        raise ValueError("The selected files have incompatible first-column types. Choose Sample index to compare by row position.")
    combined = pd.concat(parts, axis=1).sort_index()
    if isinstance(combined.index, pd.MultiIndex):
        combined.index = combined.index.get_level_values(0)
    x_name = combined.index.name
    return combined.reset_index(), x_name


def excel_sheet_names(file_bytes: bytes, filename: str) -> list[str]:
    """Return worksheet names for a supported Excel upload."""
    extension = Path(filename).suffix.casefold()
    if extension not in EXCEL_EXTENSIONS:
        return []
    engine = "xlrd" if extension == ".xls" else "openpyxl"
    return pd.ExcelFile(io.BytesIO(file_bytes), engine=engine).sheet_names


def parse_uploaded_data(
    file_bytes: bytes,
    filename: str,
    sheet_name: str | int = 0,
) -> tuple[pd.DataFrame, str, str]:
    """Read Excel, CSV, or tab-delimited data and normalize its columns."""
    extension = Path(filename).suffix.casefold()
    if extension in EXCEL_EXTENSIONS:
        engine = "xlrd" if extension == ".xls" else "openpyxl"
        frame = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, engine=engine)
    elif extension == ".csv":
        frame = pd.read_csv(io.BytesIO(file_bytes), sep=",")
    elif extension in {".tsv", ".txt"}:
        frame = pd.read_csv(io.BytesIO(file_bytes), sep="\t")
    else:
        supported = ", ".join(sorted(EXCEL_EXTENSIONS | DELIMITED_EXTENSIONS))
        raise ValueError(f"Unsupported file type {extension or '(none)'}. Expected one of: {supported}.")

    return _normalize_uploaded_frame(frame)


def parse_uploaded_workbook(file_bytes: bytes, sheet_name: str | int = 0) -> tuple[pd.DataFrame, str, str]:
    """Read an XLSX worksheet; retained for compatibility with existing callers."""
    return parse_uploaded_data(file_bytes, "workbook.xlsx", sheet_name)


def _normalize_uploaded_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    """Normalize headers, timestamps, and numeric columns in an uploaded table."""
    if frame.shape[1] == 0:
        raise ValueError("The selected file or worksheet contains no columns.")

    frame = frame.copy()
    frame.columns = _deduplicate_columns([str(column).strip() or "Unnamed" for column in frame.columns])
    timestamp_column = frame.columns[0]

    raw = frame[timestamp_column]
    parsed = _parse_timestamps(raw)
    parse_ratio = float(parsed.notna().mean()) if len(frame) else 0.0

    if parse_ratio >= 0.6:
        frame[timestamp_column] = parsed
        frame = frame.sort_values(timestamp_column, kind="stable", na_position="last").reset_index(drop=True)
        note = f"Parsed {parse_ratio:.0%} of the first column as timestamps."
    else:
        note = "The first column was kept as-is because fewer than 60% of values parsed as timestamps."

    for column in frame.columns[1:]:
        if frame[column].dtype == object:
            converted = pd.to_numeric(frame[column], errors="coerce")
            if converted.notna().sum() >= max(1, int(frame[column].notna().sum() * 0.8)):
                frame[column] = converted

    return frame, timestamp_column, note


def _parse_timestamps(values: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(values):
        return pd.to_datetime(values, errors="coerce")
    if pd.api.types.is_numeric_dtype(values):
        valid = pd.to_numeric(values, errors="coerce").dropna()
        if valid.empty:
            return pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
        magnitude = float(valid.abs().median())
        if 20_000 <= magnitude <= 100_000:
            return pd.to_datetime(values, unit="D", origin="1899-12-30", errors="coerce")
        if magnitude >= 100_000_000_000_000_000:
            return pd.to_datetime(values, unit="ns", errors="coerce")
        if magnitude >= 100_000_000_000_000:
            return pd.to_datetime(values, unit="us", errors="coerce")
        if magnitude >= 100_000_000_000:
            return pd.to_datetime(values, unit="ms", errors="coerce")
        if magnitude >= 100_000_000:
            return pd.to_datetime(values, unit="s", errors="coerce")
        return pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    return pd.to_datetime(values, errors="coerce")


def _deduplicate_columns(columns: Iterable[str]) -> list[str]:
    counts: dict[str, int] = {}
    output: list[str] = []
    for name in columns:
        count = counts.get(name, 0)
        output.append(name if count == 0 else f"{name}_{count + 1}")
        counts[name] = count + 1
    return output


def filter_columns(columns: list[str], query: str) -> list[str]:
    query = query.strip().casefold()
    return columns if not query else [column for column in columns if query in column.casefold()]


def search_table(frame: pd.DataFrame, query: str) -> pd.DataFrame:
    query = query.strip().casefold()
    if not query or frame.empty or frame.shape[1] == 0:
        return frame
    text = frame.astype(str).apply(lambda column: column.str.casefold())
    mask = text.apply(lambda column: column.str.contains(query, regex=False, na=False)).any(axis=1)
    return frame.loc[mask]


def filter_rows_by_time(
    frame: pd.DataFrame,
    timestamp_column: str,
    start: object,
    end: object,
) -> pd.DataFrame:
    timestamps = frame[timestamp_column]
    if not pd.api.types.is_datetime64_any_dtype(timestamps):
        return frame
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    return frame.loc[timestamps.between(start_ts, end_ts, inclusive="both")]
