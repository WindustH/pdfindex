"""PDF Bookmarks - Add bookmarks to PDF ebooks based on table of contents."""

__version__ = "0.1.0"

from pdf_bookmarks.config import Config
from pdf_bookmarks.processor import PDFBookmarkProcessor

__all__ = ["Config", "PDFBookmarkProcessor", "__version__"]
