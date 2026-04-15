"""
PDF / document text extractor for the Prep Studio upload endpoint.

Fixes the PrepView.vue `file.text()` bug where browser-side reading of PDFs
returns binary garbage. Server-side extraction via this module handles PDF,
MD, and TXT files correctly.

Mirrors the logic in scripts/mirofish-prep/analyze_documents.py:extract_text()
so both paths produce the same output.
"""

from pathlib import Path
from typing import Union


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


def extract_text(file_path: Union[str, Path]) -> str:
    """
    Extract plain text from a file on disk.

    Args:
        file_path: Path to a PDF, MD, or TXT file.

    Returns:
        Extracted text as a UTF-8 string.

    Raises:
        ValueError: If the file format is not supported.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format '{ext}'. MiroFish accepts: PDF, MD, TXT."
        )

    if ext == ".pdf":
        return _extract_pdf(path)
    else:
        return _extract_text_file(path)


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """
    Extract plain text from an in-memory file upload (werkzeug FileStorage).

    Args:
        data: Raw file bytes.
        filename: Original filename (used for extension detection).

    Returns:
        Extracted text as a UTF-8 string.

    Raises:
        ValueError: If the file format is not supported.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format '{ext}'. MiroFish accepts: PDF, MD, TXT."
        )

    if ext == ".pdf":
        return _extract_pdf_bytes(data)
    else:
        # Text files: try UTF-8 first, fall back to latin-1
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    """Extract text from a PDF file on disk."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except ImportError:
        pass

    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        raise ImportError(
            "PDF extraction requires PyMuPDF or pdfplumber. "
            "Install with: pip install pymupdf"
        )


def _extract_pdf_bytes(data: bytes) -> str:
    """Extract text from PDF bytes (in-memory upload)."""
    try:
        import fitz  # PyMuPDF
        import io
        doc = fitz.open(stream=io.BytesIO(data), filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except ImportError:
        pass

    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        raise ImportError(
            "PDF extraction requires PyMuPDF or pdfplumber. "
            "Install with: pip install pymupdf"
        )


def _extract_text_file(path: Path) -> str:
    """Extract text from a plain-text file (MD, TXT)."""
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")
