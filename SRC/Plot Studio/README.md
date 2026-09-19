# IEEE Plot Studio

A local Streamlit application for comparing measurements from multiple Excel, CSV, and tab-delimited files in publication-ready figures.

## Features

- Upload multiple `.xlsx`, `.xlsm`, `.xls`, `.csv`, `.tsv`, or tab-delimited `.txt` files together; choose a worksheet separately for each workbook.
- Select multiple measurement columns from each file and plot all selected series together, with source filenames in the legend.
- Parse the first column as time, inspect data in a table, search column names and row values, and select visible columns.
- Filter the active dataset with an interactive timestamp range.
- Customize individual legend names and the legend title; legends sit below the graph with configurable columns.
- Set exact inclusive time/sample limits or use the timestamp slider.
- Add horizontal/vertical reference lines and translucent horizontal/vertical bands, with colors and optional legend labels.
- Configure titles, axis labels, grid, log axes, line width, and marker size.
- Use IEEE single-column or double-column figure dimensions with IEEE styles or the new Modern Research theme.
- Export SVG plus 1200-DPI PNG and JPG files.

### Included plots

1. Time series
2. Box plot
3. Comparison plot, with optional z-score normalization
4. Scatter plot
5. Histogram
6. Violin plot
7. Summary bar chart
8. Correlation heatmap
9. Pair plot
10. Autocorrelation
11. FFT spectrum
12. Power spectral density
13. Spectrogram

## Compare columns from different files

1. Upload your files in **Load data**. You can mix Excel, CSV, and tab-delimited files.
2. Under **Select columns to plot**, choose a worksheet for each Excel workbook.
3. Use each file's **Columns to plot** selector to choose one or more numeric measurement columns. Leave a file's selection empty to exclude it. No measurement columns are selected automatically.
4. Choose **Align files by**:
   - **First column** matches timestamps or X values exactly. All samples are retained; missing matches remain empty. Repeated X values pair by occurrence, without multiplying rows. Files must have compatible first-column types and no missing X values.
   - **Sample index** compares rows starting at zero, useful for separate experiments recorded at different times. Rows follow each file's parsed order (chronological when timestamps were recognized).
5. Choose **Time series** or **Comparison plot** in the sidebar. The **Figure studio** tab updates automatically to plot only your selected columns. Comparison plots optionally normalize each series using its own z-score.
6. Adjust the timeframe and publication style, then prepare the export files.

For example, select `velocity` from `experiment_A.csv` and `velocity` plus `current` from `experiment_B.xlsx`. The figure contains three labeled series. Selecting fewer columns immediately removes the deselected series from the plot and export.

The **Data inspector** shows the combined selection. Its table visibility and search controls change only the table; use **Columns to plot** to change the figure.

No interpolation is applied. Scatter plots using a measurement as X and correlation plots compare only matching samples; files with no common X values have no paired observations. Spectral plots infer sampling rates separately for each series, unless you supply an override. Spectrograms display the first selected series, and pair plots display at most five series.

## Legend, time limits, and annotations

### Rename columns for every plot

Open **Data inspector → Rename columns for all plots**. Edit the **Plot name** cells beside the original column names, then click **Apply column names**. You can also rename the time/sample column. Names must be non-empty and unique, including the time column; invalid edits leave the previous names in use.

Applied names appear in the data table, scatter X selector, automatic axis labels, category labels, correlation and pair plots, legends, and exported figures. Original uploaded files and source-column selectors remain unchanged, so you can still trace each series to its source. Names are retained during the current session for the same uploaded files and worksheets, including when you deselect and reselect a column. Restore a name by copying its **Original column** value back into **Plot name** and applying.

The sidebar's **Custom legend names** and manual axis labels remain optional display overrides. Leave these blank to use the renamed table columns automatically.

In the sidebar, open **Custom legend names** and enter a label for each selected series (for example, `Proposed controller` and `Baseline`). Blank names retain the file/column label. **Legend columns** controls the number of columns below the graph, and **Legend** toggles its visibility. These settings also apply to exports. Plots that identify series by category axes instead of a legend retain those category labels.

Under **Time / sample range**, choose **Exact range** to enter inclusive start and end limits. For timestamp data, enter full dates/times such as `2026-01-01 10:00:00.250`; for numeric time or sample alignment, enter numeric limits. **Slider** is also available for timestamp data. **All records** restores the full dataset. This range filters the source data for every plot type; it does not set frequency limits on spectral plots.

Open **Reference lines and shaded bands** and add rows to the table:

| Kind | Start | End |
| --- | --- | --- |
| Horizontal line | Y value, such as `0.5` | Unused |
| Vertical line | X value or full timestamp | Unused |
| Horizontal band | Lower Y bound | Upper Y bound |
| Vertical band | Lower X bound or timestamp | Upper X bound or timestamp |

Set a color name or hex code and optionally a legend label. **Band opacity** ranges from 0 (invisible) to 1 (opaque), with a faded default of 0.15. Remove a row to remove its annotation. Coordinates refer to displayed axis units: normalized amplitudes for normalized comparison plots, frequencies for spectral plots, and elapsed seconds for spectrograms. Annotations are not offered for the multi-axis pair plot.

Choose **Modern Research** for sans-serif typography, a blue/coral/teal/violet palette, subtle gridlines, and a white publication background. IEEE Classic, IEEE Grayscale, Q1 Clean, and High Contrast remain available. Figure size is independent of the theme.

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`.

The browser app opens locally. Uploaded workbooks stay in the running Streamlit session and are not written to disk by this project.

## Workbook format

The first row should contain column names. The first column should contain timestamps, followed by any number of measurement columns. At least 60% of first-column values must parse as dates/times for timeframe filtering to activate. Measurement columns are treated as numeric when at least 80% of their non-empty cells can be converted to numbers.

For spectral plots, the sampling rate is inferred from the median timestamp interval. You can override it in the sidebar when timestamps are unavailable or irregular.

## Publication note

The presets target common IEEE figure widths and small, consistent typography. Final compliance still depends on the destination journal or conference template, so check its current artwork and font requirements before submission.
