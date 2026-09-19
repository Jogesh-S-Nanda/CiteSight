# IEEE Plot Studio

A local Streamlit application for comparing measurements from multiple Excel, CSV, and tab-delimited files in publication-ready figures.

## Features

- Upload multiple `.xlsx`, `.xlsm`, `.xls`, `.csv`, `.tsv`, or tab-delimited `.txt` files together; choose a worksheet separately for each workbook.
- Select multiple measurement columns from each file and plot all selected series together, with source filenames in the legend.
- Parse the first column as time, inspect data in a table, search column names and row values, and select visible columns.
- Filter the active dataset with an interactive timestamp range.
- Configure titles, axis labels, legend title, grid, log axes, line width, and marker size.
- Use IEEE single-column or double-column figure dimensions and four restrained publication themes.
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
