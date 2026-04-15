"""
PDF / document text extractor for the Prep Studio upload endpoint.

Fixes the PrepView.vue `file.text()` bug where browser-side reading of PDFs
returns binary garbage. The HTTP upload path (FormData → Flask FileStorage)
needs in-memory bytes extraction; the on-disk path (re-reading already-
uploaded sources) is handled by scripts/mirofish-prep/analyze_documents.py.
"""

import io
from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


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
        ImportError: If no PDF library is available for a PDF input.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format '{ext}'. MiroFish accepts: PDF, MD, TXT."
        )

    if ext == ".pdf":
        return _extract_pdf_bytes(data)

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf_bytes(data: bytes) -> str:
    """Extract text from PDF bytes (in-memory upload)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=io.BytesIO(data), filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except ImportError:
        pass

    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        raise ImportError(
            "PDF extraction requires PyMuPDF or pdfplumber. "
            "Install with: pip install pymupdf"
        )
