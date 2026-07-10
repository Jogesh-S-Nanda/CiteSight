import os
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, render_template, request

from utils.search import read_pdf_files, search_pdfs


BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "ui" / "templates"),
    static_folder=str(BASE_DIR / "ui" / "static"),
    static_url_path="/ui/static",
)

pdf_index: list[dict] = []
index_folder = ""
index_lock = Lock()


@app.get("/")
def home():
    default_folder = os.getenv(
        "CITESIGHT_PDF_FOLDER", str(Path.home() / "Documents")
    )
    return render_template("index.html", default_folder=default_folder)


@app.post("/api/index")
def build_index():
    global pdf_index, index_folder

    payload = request.get_json(silent=True) or {}
    folder = str(payload.get("folder", "")).strip()
    if not folder:
        return jsonify({"error": "Enter a folder path to index."}), 400

    try:
        records = read_pdf_files(folder)
    except (FileNotFoundError, NotADirectoryError) as error:
        return jsonify({"error": str(error)}), 400
    except PermissionError:
        return jsonify({"error": "Permission denied while reading this folder."}), 403
    except Exception:
        app.logger.exception("Unable to index PDF folder")
        return jsonify({"error": "The folder could not be indexed."}), 500

    with index_lock:
        pdf_index = records
        index_folder = str(Path(folder).expanduser().resolve())

    return jsonify(
        {
            "message": f"Indexed {len(records)} PDF file(s).",
            "count": len(records),
            "folder": index_folder,
        }
    )


@app.get("/api/search")
def search_index():
    with index_lock:
        records = list(pdf_index)
        folder = index_folder

    if not folder:
        return jsonify({"error": "Index a PDF folder before searching."}), 400

    results = search_pdfs(
        records,
        query=request.args.get("query", ""),
        file_name=request.args.get("file_name"),
        title=request.args.get("title"),
        path=request.args.get("path"),
    )

    return jsonify(
        {
            "count": len(results),
            "indexed_count": len(records),
            "folder": folder,
            "results": results,
        }
    )


@app.get("/api/status")
def status():
    with index_lock:
        return jsonify(
            {
                "indexed": bool(index_folder),
                "count": len(pdf_index),
                "folder": index_folder,
            }
        )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)