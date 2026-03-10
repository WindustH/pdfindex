"""Bookmark generation and offset calculation."""

import re
from typing import List, Dict, Any
from PIL import Image
from pypdf import PdfReader

from pdf_bookmarks.core.image import PDFImageProcessor
from pdf_bookmarks.core.llm import VisionLLMClient
from pdf_bookmarks.utils import Log


class BookmarkGenerator:
    """Handles bookmark generation and offset calculation."""

    def __init__(self, vision_client: VisionLLMClient):
        self.vision_client = vision_client

    def calculate_page_offset_with_progress(
        self, pdf_path: str, toc_pages: List[Image.Image], content_start_index: int,
        state: "ProgressState", progress_manager: "ProgressManager"
    ) -> Dict[str, Any]:
        """Calculate the offset with progress tracking. Returns dict with offset and details."""
        if not toc_pages:
            raise ValueError("No TOC pages provided")

        Log.step("Calculating page offset...")

        # Get first entry from first TOC page
        first_toc_page = toc_pages[0]
        result = self.vision_client.extract_first_arabic_toc_entry(first_toc_page)
        if result is None:
            raise RuntimeError("No Arabic-numbered entry found on the first TOC page.")

        page_str, item_text = result
        first_page_num = int(page_str)
        state.first_entry_title = item_text
        state.first_entry_toc_page = first_page_num
        progress_manager.save(state)

        Log.info(f"First TOC entry: '{item_text}' (TOC page {first_page_num})")

        # Search from content_start_index, max 10 pages
        state.offset_search_start_page = content_start_index + 1
        state.offset_search_end_page = min(content_start_index + 11, len(PdfReader(pdf_path).pages) + 1)
        progress_manager.save(state)

        Log.detail(f"Searching from page {state.offset_search_start_page} (max 10 pages)...")

        actual_page_num = self._find_content_page_with_limit_progress(
            pdf_path, item_text, content_start_index, state.offset_search_end_page,
            state, progress_manager
        )

        if actual_page_num == 0:
            raise RuntimeError(
                f"Could not locate '{item_text}' within 10 pages after TOC. "
                "The TOC page number may be incorrect or content may be elsewhere."
            )

        offset = actual_page_num - first_page_num
        state.first_entry_actual_page = actual_page_num
        progress_manager.save(state)

        Log.success(f"Initial offset calculated: {offset} (TOC says {first_page_num}, actual is {actual_page_num})")

        return {
            "offset": offset,
            "first_entry_title": item_text,
            "first_toc_page": first_page_num,
            "actual_page": actual_page_num
        }

    def _find_content_page_with_limit_progress(
        self, pdf_path: str, target_text: str, start_index: int, max_index: int,
        state: "ProgressState", progress_manager: "ProgressManager"
    ) -> int:
        """Find the page containing specific content, with a page limit and progress tracking."""
        Log.detail(f"Searching for content: '{target_text}'...")

        end_index = min(max_index, len(PdfReader(pdf_path).pages))
        for page_index in range(start_index, end_index):
            state.offset_search_current_page = page_index + 1
            progress_manager.save(state)

            Log.detail(f"  Checking page {page_index + 1}...")
            page_image = PDFImageProcessor.extract_page_as_image(pdf_path, page_index)
            if self.vision_client.page_contains_content(page_image, target_text):
                return page_index + 1  # 1-based

        return 0

    @staticmethod
    def apply_page_offset(bookmark_text: str, offset: int) -> str:
        """Apply page number offset to bookmark text."""

        def replace_page_number(match):
            original_page = int(match.group(1))
            new_page = original_page + offset
            return f"BookmarkPageNumber: {new_page}"

        return re.sub(r"BookmarkPageNumber: (\d+)", replace_page_number, bookmark_text)
