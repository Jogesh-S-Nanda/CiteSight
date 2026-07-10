import os
from pathlib import Path
from typing import Optional
from pypdf import PdfReader


def extract_pdf_title(pdf_path: Path) -> str:
    """
    Extracts the title of a PDF document from its metadata or content. The function first attempts to fetch the
    title from the PDF metadata. If no valid metadata title is found, it extracts and returns the first meaningful
    line of text from the first page of the PDF. If all attempts fail, the file stem is returned as a fallback title.

    :param pdf_path: Path to the PDF file from which the title will be extracted.
    :type pdf_path: Path
    :return: is The extracted PDF title or the file stem as a fallback.
    :rtype: Str
    """
    try:
        reader = PdfReader(str(pdf_path))

        # Try PDF metadata
        if reader.metadata and reader.metadata.title:
            title = reader.metadata.title.strip()
            if title:
                return title

        # Try the first meaningful line of the first page
        if reader.pages:
            text = reader.pages[0].extract_text() or ""

            for line in text.splitlines():
                line = " ".join(line.split()).strip()

                if len(line) >= 4:
                    return line[:300]

    except Exception:
        pass

    return pdf_path.stem


def read_pdf_files(folder_path: str) -> list[dict]:
    """
    Reads all PDF files in the specified folder and its subdirectories, extracts relevant
    information such as the file name, absolute path, relative path, and title, and returns
    them as a sorted list of dictionaries.

    :param folder_path: The path to the folder containing PDF files to read.
    :type folder_path: Str
    :raises FileNotFoundError: Raised if the specified folder path does not exist.
    :raises NotADirectoryError: Raised if the specified folder path is not a directory.
    :return: A list of dictionaries containing the following keys for each PDF file:
        - file_name: The name of the PDF file (str).
        - path: The absolute path to the PDF file (str).
        - relative_path: The relative path from the given folder to the PDF file (str).
        - title: The extracted title of the PDF file (str).
    :rtype: List[dict]
    """
    root_folder = Path(folder_path).expanduser().resolve()

    if not root_folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {root_folder}")

    if not root_folder.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {root_folder}")

    pdf_records = []

    for pdf_path in root_folder.rglob("*"):
        if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
            continue

        pdf_records.append(
            {
                "file_name": pdf_path.name,
                "path": str(pdf_path.resolve()),
                "relative_path": str(pdf_path.relative_to(root_folder)),
                "title": extract_pdf_title(pdf_path),
            }
        )

    return sorted(
        pdf_records,
        key=lambda record: record["relative_path"].lower()
    )



def search_pdfs(
    pdf_records: list[dict],
    query: str = "",
    file_name: Optional[str] = None,
    title: Optional[str] = None,
    path: Optional[str] = None,
    ) -> list[dict]:
    """
    Search through a list of PDF records to find matches based on specified query criteria.
    This function filters records based on case-insensitive search criteria for
    query terms, file names, titles, and file paths.

    :param pdf_records:
        A list of dictionaries, where each dictionary represents a PDF record.
        Each record must include `file_name`, `title`, `relative_path`, and
        other relevant metadata.

    :param query:
        A string representing a case-insensitive search term. The term is
        matched across combined metadata fields of the PDF records. If empty,
        this parameter is ignored.

    :param file_name:
        An optional case-insensitive search term specifically limited to match
        within the `file_name` field of the PDF records.

    :param title:
        An optional case-insensitive search term specifically limited to match
        within the `title` field of the PDF records.

    :param path:
        An optional case-insensitive search term specifically limited to match
        within the `relative_path` field of the PDF records.

    :return:
        A list of dictionaries representing the PDF records that matched all
        specified search criteria. The list could be empty if no matches are
        found.
    """
    query = query.strip().casefold()
    file_name = file_name.strip().casefold() if file_name else None
    title = title.strip().casefold() if title else None
    path = path.strip().casefold() if path else None

    results = []

    for record in pdf_records:
        searchable_text = " ".join(
            [
                record["file_name"],
                record["title"],
                record["relative_path"],
            ]
        ).casefold()

        if query and query not in searchable_text:
            continue

        if file_name and file_name not in record["file_name"].casefold():
            continue

        if title and title not in record["title"].casefold():
            continue

        if path and path not in record["path"].casefold():
            continue

        results.append(record)

    return results





def main() -> None:
    """
    Main function to handle PDF folder processing and search functionality.

    The program retrieves a folder path for PDF files from the environment variable
    `CITESIGHT_PDF_FOLDER`. If the folder path is invalid or not a directory, the
    user is prompted to provide a valid folder path manually. The program scans the
    PDF files within the specified folder, builds an index, and permits searching
    for files based on a query term. The search results, if any, are displayed to
    the user.

    :raises FileNotFoundError: When the provided folder does not exist.
    :raises NotADirectoryError: When the provided folder path is not a directory.
    :return: None
    """
    pdf_folder = os.getenv(
        "CITESIGHT_PDF_FOLDER",
        str(Path.home() / "Documents"),
    )

    if not Path(pdf_folder).is_dir():
        pdf_folder = input(
            f"PDF folder not found: {pdf_folder}\n"
            "Enter the path to your PDF folder: "
        ).strip()

    try:
        pdf_index = read_pdf_files(pdf_folder)
    except (FileNotFoundError, NotADirectoryError) as error:
        print(f"Error: {error}")
        return

    print(f"\nFound {len(pdf_index)} PDF files.")

    for record in pdf_index:
        print(
            f"\nTitle: {record['title']}\n"
            f"File:  {record['file_name']}\n"
            f"Path:  {record['path']}"
        )

    query = input("\nEnter a search term: ").strip()

    if query:
        results = search_pdfs(pdf_index, query=query)

        print(f"\nFound {len(results)} matching PDF file(s).")

        for record in results:
            print(
                f"\nTitle: {record['title']}\n"
                f"File:  {record['file_name']}\n"
                f"Path:  {record['path']}"
            )


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()