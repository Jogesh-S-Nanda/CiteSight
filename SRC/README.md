# CiteSight PDF Search

A local web interface for recursively indexing and searching PDF metadata.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000> and enter the absolute path of the folder containing PDFs.

You may provide the default folder through an environment variable:

```bash
export CITESIGHT_PDF_FOLDER="/home/user/Documents/Research"
python app.py
```

## Structure

```text
.
├── app.py
├── requirements.txt
├── ui
│   ├── static
│   │   ├── css/styles.css
│   │   └── js/app.js
│   └── templates/index.html
└── utils
    └── search.py
```