#!/usr/bin/env python3
import argparse
import base64
import io
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import fitz  # PyMuPDF
from openai import OpenAI
from PIL import Image
from pypdf import PdfReader


# Configuration
@dataclass
class Config:
    api_key: str = os.getenv("PDFINDEX_API_KEY", "")
    base_url: str = os.getenv("PDFINDEX_BASE_URL", "")
    vision_model: str = os.getenv("PDFINDEX_VISION_MODEL", "")
    temp_bookmark_file: str = "bookmarks.txt"


def is_roman_numeral(s: str) -> bool:
    """Check if a string is a valid Roman numeral."""
    roman_regex = (
        r"^(?=[MDCLXVI])M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
    )
    return bool(re.fullmatch(roman_regex, s.upper()))


def is_arabic_number(s: str) -> bool:
    """Check if string is a positive integer in Arabic numerals."""
    return (
        s.isdigit() and s[0] != "0" or s == "0"
    )  # allow '0' but no leading zeros like '01'


class PDFImageProcessor:
    """Handles PDF page to image conversion and image processing."""

    @staticmethod
    def extract_page_as_image(
        pdf_path: str, page_index: int, max_pixel: int = 2000
    ) -> Image.Image:
        """Extract a specific page from PDF as an image, with max width or height <= max_pixel."""
        doc = fitz.open(pdf_path)
        try:
            page = doc.load_page(page_index)
            get_pixmap = getattr(page, "get_pixmap")
            pix = get_pixmap()

            width, height = pix.width, pix.height
            scale = min(max_pixel / max(width, height), 1.0)
            if scale < 1.0:
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat)

            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            return image
        finally:
            doc.close()

    @staticmethod
    def convert_to_base64_webp(image: Image.Image) -> str:
        """Convert PIL image to base64-encoded WebP format."""
        buffer = io.BytesIO()
        image.save(buffer, format="webp", quality=80)
        encoded_bytes = base64.b64encode(buffer.getvalue())
        return encoded_bytes.decode("utf-8")


class VisionLLMClient:
    """Handles all interactions with the vision language model."""

    def __init__(self, config: Config):
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.model = config.vision_model

    def _send_vision_request(self, images: List[str], prompt: str) -> str:
        """Send a request to the vision LLM with images and prompt."""
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]

        for base64_image in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/webp;base64,{base64_image}",
                        "detail": "high",
                    },
                }
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            stream=False,
        )
        return response.choices[0].message.content or ""

    def is_index_page(self, page_image: Image.Image) -> bool:
        """Determine if a page is an index/table of contents page."""
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        prompt = (
            "This page is from a book. Determine if it is a table of contents or index. "
            "A table of contents typically has many listed section titles (often hierarchical) "
            "with page numbers aligned on the right. The layout is usually structured and dense with entries. "
            "Answer ONLY 'yes' or 'no'."
        )
        response = self._send_vision_request([base64_image], prompt)
        return "yes" in response.lower()

    def extract_first_arabic_index_entry(
        self, page_image: Image.Image
    ) -> Optional[Tuple[str, str]]:
        """Extract the first index entry that has an Arabic numeral page number (e.g., 1, 5)."""
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        prompt = (
            "From this table of contents page, find the very first entry whose page number is an Arabic numeral "
            "(like 1, 3, 15 — NOT i, ii, iii, v, x, etc.). "
            "Return EXACTLY in the format: 'page_number, entry_text'. "
            "If no such entry exists on this page, return 'none, none'."
        )
        response = self._send_vision_request([base64_image], prompt)
        cleaned = self._clean_llm_response(response)

        try:
            page_str, item_text = cleaned.split(",", 1)
            page_str = page_str.strip()
            item_text = item_text.strip()
            if page_str.lower() == "none" or item_text.lower() == "none":
                return None
            # Validate: must be positive integer string
            if page_str.isdigit() and int(page_str) >= 1:
                return page_str, item_text
            else:
                return None
        except Exception:
            return None

    def page_contains_content(self, page_image: Image.Image, target_text: str) -> bool:
        """Check if a page contains actual section content (not just header/footer or reference)."""
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        prompt = (
            f"Does this page contain the main body content of the section titled '{target_text}'? "
            "Ignore headers, footers, or references. Only say 'yes' if this is the actual start of that section. "
            "Answer ONLY 'yes' or 'no'."
        )
        response = self._send_vision_request([base64_image], prompt)
        return "yes" in response.lower()

    def generate_pdftk_bookmarks(self, index_pages: List[Image.Image]) -> str:
        """Convert index pages to pdftk bookmark format, excluding entries with Roman numeral page numbers."""
        base64_images = [
            PDFImageProcessor.convert_to_base64_webp(page) for page in index_pages
        ]

        prompt = """
You are given one or more images of a book's table of contents.

Your task: Generate a list of bookmarks in the EXACT pdftk format below.

Rules:
- ONLY include entries that correspond to Arabic-numbered pages (e.g., 1, 2, 15).
- EXCLUDE any entry whose page number is a Roman numeral (e.g., i, ii, iii, vi, xii).
- For each valid entry, output:
BookmarkBegin
BookmarkTitle: [Exact title from the index]
BookmarkLevel: [1 for top-level, 2 for subsection, etc.]
BookmarkPageNumber: [Original page number as Arabic integer]

Example:
BookmarkBegin
BookmarkTitle: Chapter 1: Introduction
BookmarkLevel: 1
BookmarkPageNumber: 5
BookmarkBegin
BookmarkTitle: 1.1 Background
BookmarkLevel: 2
BookmarkPageNumber: 7

Do NOT add any explanation, headers, or extra text. Output ONLY the bookmark entries.
        """.strip()

        return self._send_vision_request(base64_images, prompt)

    @staticmethod
    def _clean_llm_response(response: str) -> str:
        """Remove common LLM response artifacts."""
        cleaned = response.strip()
        artifacts = [
            "<|begin_of_box|>",
            "<|end_of_box|>",
            "```",
            "```plaintext",
            "```text",
        ]
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, "")
        return cleaned.strip()


class IndexPageDetector:
    """Handles detection and processing of index pages in a PDF."""

    def __init__(self, vision_client: VisionLLMClient):
        self.vision_client = vision_client

    def find_index_pages(self, pdf_path: str) -> Tuple[List[Image.Image], int]:
        """
        Find all consecutive index pages in a PDF.

        Returns:
            Tuple of (list of index page images, index of first non-index page)
        """
        print("Scanning for index pages...")

        pdf_reader = PdfReader(pdf_path)
        index_pages = []
        first_index_found = False
        content_start_index = 0

        for page_index in range(len(pdf_reader.pages)):
            page_image = PDFImageProcessor.extract_page_as_image(pdf_path, page_index)

            if self.vision_client.is_index_page(page_image):
                first_index_found = True
                index_pages.append(page_image)
                print(f"Found index page at position {page_index + 1}")
            elif first_index_found:
                content_start_index = page_index
                break

        return index_pages, content_start_index


class BookmarkGenerator:
    """Handles bookmark generation and PDF modification."""

    def __init__(self, vision_client: VisionLLMClient, config: Config):
        self.vision_client = vision_client
        self.config = config

    def calculate_page_offset(
        self, pdf_path: str, index_pages: List[Image.Image], content_start_index: int
    ) -> int:
        """Calculate the offset using the first Arabic-numeral index entry."""
        if not index_pages:
            raise ValueError("No index pages provided")

        print("Looking for first Arabic-numbered entry to calculate page offset...")

        # Search through all index pages in order
        for idx, page_img in enumerate(index_pages):
            result = self.vision_client.extract_first_arabic_index_entry(page_img)
            if result is not None:
                page_str, item_text = result
                print(
                    f"Found Arabic entry on index page {idx + 1}: '{item_text}' (page {page_str})"
                )
                first_page_num = int(page_str)

                # Now find this content in actual PDF
                pdf_reader = PdfReader(pdf_path)
                actual_page_num = self._find_content_page(
                    pdf_path, item_text, content_start_index, len(pdf_reader.pages)
                )

                if actual_page_num == 0:
                    raise RuntimeError(
                        f"Could not locate content for '{item_text}' in the PDF"
                    )

                offset = actual_page_num - first_page_num
                print(f"Page offset calculated: {offset}")
                return offset

        raise RuntimeError(
            "No index entry with Arabic page number found. "
            "Cannot determine page offset. Please ensure the table of contents includes numbered chapters."
        )

    def _find_content_page(
        self, pdf_path: str, target_text: str, start_index: int, total_pages: int
    ) -> int:
        """Find the page containing specific content."""
        print(f"Searching for content: '{target_text}'...")

        for page_index in range(start_index, total_pages):
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

    def add_bookmarks_to_pdf(
        self, bookmark_text: str, input_path: str, output_path: str
    ):
        """Add bookmarks to PDF using pdftk."""
        self._verify_pdftk_installation()

        print("Adding bookmarks to PDF...")

        with open(self.config.temp_bookmark_file, "w", encoding="utf-8") as f:
            f.write(bookmark_text.strip())

        try:
            subprocess.run(
                [
                    "pdftk",
                    input_path,
                    "update_info",
                    self.config.temp_bookmark_file,
                    "output",
                    output_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"Successfully created PDF with bookmarks: {output_path}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pdftk failed: {e.stderr}") from e
        finally:
            if os.path.exists(self.config.temp_bookmark_file):
                os.remove(self.config.temp_bookmark_file)

    @staticmethod
    def _verify_pdftk_installation():
        try:
            subprocess.run(
                ["pdftk", "--version"], check=True, capture_output=True, text=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                "pdftk is not installed or not accessible. "
                "Please install pdftk to use this tool."
            ) from e


class PDFBookmarkProcessor:
    """Main class orchestrating the PDF bookmark addition process."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.vision_client = VisionLLMClient(self.config)
        self.index_detector = IndexPageDetector(self.vision_client)
        self.bookmark_generator = BookmarkGenerator(self.vision_client, self.config)

    def process_pdf(self, input_path: str, output_path: str):
        """Process a PDF to add bookmarks based on its index pages."""
        try:
            index_pages, content_start_index = self.index_detector.find_index_pages(
                input_path
            )

            if not index_pages:
                print("No index pages found in the PDF.")
                return False

            print(f"Found {len(index_pages)} index page(s)")

            offset = self.bookmark_generator.calculate_page_offset(
                input_path, index_pages, content_start_index
            )

            print("Generating bookmark structure...")
            bookmark_text = self.vision_client.generate_pdftk_bookmarks(index_pages)

            if not bookmark_text.strip():
                print("No valid (Arabic-numbered) bookmark entries found. Exiting.")
                return False

            bookmark_text = self.bookmark_generator.apply_page_offset(
                bookmark_text, offset
            )

            self.bookmark_generator.add_bookmarks_to_pdf(
                bookmark_text, input_path, output_path
            )

            print("PDF bookmark processing completed successfully!")
            return True

        except Exception as e:
            print(f"Error processing PDF: {e}")
            return False


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add bookmarks to a PDF ebook based on its index pages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py input.pdf output.pdf
  python main.py /path/to/ebook.pdf /path/to/ebook_with_bookmarks.pdf

Requirements:
  - pdftk must be installed and accessible in PATH
  - Environment variables must be set: API_KEY, BASE_URL, VISION_MODEL
        """,
    )
    parser.add_argument("input_path", type=str, help="Path to the input PDF file")
    parser.add_argument(
        "output_path", type=str, help="Path for output PDF with bookmarks"
    )
    return parser


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    if not os.path.exists(args.input_path):
        print(f"Error: Input file '{args.input_path}' does not exist.")
        return 1

    output_dir = os.path.dirname(args.output_path)
    if output_dir and not os.path.exists(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist.")
        return 1

    processor = PDFBookmarkProcessor()
    success = processor.process_pdf(args.input_path, args.output_path)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
