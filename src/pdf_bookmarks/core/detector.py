"""TOC (Table of Contents) page detection in PDF files."""

from typing import List, Tuple, Optional
from PIL import Image
from pypdf import PdfReader

from pdf_bookmarks.core.image import PDFImageProcessor
from pdf_bookmarks.core.llm import VisionLLMClient
from pdf_bookmarks.utils import Log
from pdf_bookmarks.progress import ProgressState, ProgressManager


class TOCPageDetector:
    """Handles detection and processing of TOC pages in a PDF."""

    def __init__(self, vision_client: VisionLLMClient):
        self.vision_client = vision_client

    def extract_toc_pages_direct(
        self, pdf_path: str, toc_start_index: int, toc_count: int
    ) -> List[Image.Image]:
        """
        Directly extract TOC pages when we already know their positions.

        Args:
            pdf_path: Path to the PDF file
            toc_start_index: The starting index (0-based) of the first TOC page
            toc_count: Number of TOC pages to extract

        Returns:
            List of TOC page images
        """
        pdf_reader = PdfReader(pdf_path)
        toc_pages = []

        for i in range(toc_count):
            page_index = toc_start_index + i
            if page_index >= len(pdf_reader.pages):
                break
            page_image = PDFImageProcessor.extract_page_as_image(pdf_path, page_index)
            toc_pages.append(page_image)
            Log.detail(f"Extracted TOC page {i + 1}/{toc_count} (PDF page {page_index + 1})")

        return toc_pages

    def find_toc_pages(
        self, pdf_path: str, state: Optional[ProgressState] = None, progress_manager: Optional[ProgressManager] = None
    ) -> Tuple[List[Image.Image], int]:
        """
        Find all consecutive TOC pages in a PDF.

        When resuming (state.toc_scan_current_page > 0), starts scanning from that page.

        Returns:
            Tuple of (list of TOC page images, index of first non-TOC page)
        """
        pdf_reader = PdfReader(pdf_path)
        toc_pages = []
        first_toc_found = False
        content_start_index = 0

        # Track initial TOC count for accumulation
        initial_toc_count = 0
        if state is not None:
            initial_toc_count = state.toc_pages_count

        # Determine starting page
        start_page = 0
        if state is not None and state.toc_scan_current_page > 0:
            start_page = state.toc_scan_current_page - 1  # Convert to 0-indexed
            Log.step(f"Resuming TOC scan from page {state.toc_scan_current_page}...")
            # When resuming, check if we've already found TOC pages before
            # If toc_start_index is set, we've found at least one TOC page
            first_toc_found = state.toc_start_index >= 0
        else:
            Log.step("Scanning for TOC pages...")

        for page_index in range(start_page, len(pdf_reader.pages)):
            # Update progress
            if state is not None and progress_manager is not None:
                state.toc_scan_current_page = page_index + 1
                progress_manager.save(state)

            page_image = PDFImageProcessor.extract_page_as_image(pdf_path, page_index)

            if self.vision_client.is_toc_page(page_image):
                first_toc_found = True
                toc_pages.append(page_image)
                Log.detail(f"✓ Page {page_index + 1}: TOC page")
                # Update state with TOC info
                if state is not None:
                    # Set toc_start_index on first TOC page found
                    if state.toc_start_index == -1:
                        state.toc_start_index = page_index
                    # Update toc_pages_count with accumulation
                    state.toc_pages_count = initial_toc_count + len(toc_pages)
                    if progress_manager is not None:
                        progress_manager.save(state)
            else:
                if first_toc_found:
                    # Found first non-TOC page after TOC pages
                    Log.detail(f"✗ Page {page_index + 1}: end of TOC (content start)")
                    content_start_index = page_index
                    # Update state
                    if state is not None:
                        if state.content_start_index == 0:
                            state.content_start_index = content_start_index
                        # Calculate correct TOC pages count based on start and end positions
                        if state.toc_start_index >= 0 and content_start_index > state.toc_start_index:
                            state.toc_pages_count = content_start_index - state.toc_start_index
                        else:
                            # Fallback to current count
                            state.toc_pages_count = len(toc_pages)
                        if progress_manager is not None:
                            progress_manager.save(state)
                    break
                else:
                    # Haven't found any TOC page yet
                    Log.detail(f"✗ Page {page_index + 1}: not a TOC page")

        return toc_pages, content_start_index
