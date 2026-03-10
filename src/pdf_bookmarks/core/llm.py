"""Vision LLM client for processing PDF TOC pages."""

import sys
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from openai import OpenAI

from pdf_bookmarks.core.image import PDFImageProcessor
from pdf_bookmarks.utils import Colors, Log, clean_llm_response
from pdf_bookmarks.prompts import (
    TOCDetectionPrompts,
    TOCExtractionPrompts,
    ContentVerificationPrompts,
    BookmarkGenerationPrompts,
    BookmarkRefinementPrompts,
)


class VisionLLMClient:
    """Handles all interactions with the vision language model."""

    def __init__(self, api_key: str, base_url: str, vision_model: str, text_model: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.vision_model = vision_model
        self.text_model = text_model

    def _send_vision_request(self, images: List[str], prompt: str, stream: bool = True, timeout: float = 120) -> str:
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
            model=self.vision_model,
            messages=[{"role": "user", "content": content}],
            stream=stream,
            timeout=timeout,
        )

        if stream:
            return self._process_streaming_response(response)
        else:
            return response.choices[0].message.content or ""

    def _process_streaming_response(self, response) -> str:
        """Process streaming response and display in real-time."""
        full_content = ""
        first_chunk = True

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content

                if first_chunk:
                    sys.stdout.write(f"{Colors.DIM}  Streaming: {Colors.RESET}")
                    first_chunk = False

                sys.stdout.write(content)
                sys.stdout.flush()

        if not first_chunk:
            sys.stdout.write(f"{Colors.RESET}\n")
            sys.stdout.flush()

        return full_content

    def is_toc_page(self, page_image: Image.Image) -> bool:
        """Determine if a page is a table of contents page."""
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        response = self._send_vision_request([base64_image], TOCDetectionPrompts.IS_TOC_PAGE)
        return "yes" in response.lower()

    def extract_first_arabic_toc_entry(
        self, page_image: Image.Image
    ) -> Optional[Tuple[str, str]]:
        """Extract the first TOC entry that has an Arabic numeral page number (e.g., 1, 5)."""
        import re
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        response = self._send_vision_request([base64_image], TOCExtractionPrompts.EXTRACT_FIRST_ARABIC_ENTRY)
        cleaned = clean_llm_response(response)

        try:
            if "," not in cleaned:
                return None

            parts = cleaned.split(",", 1)
            page_str = parts[0].strip()
            item_text = parts[1].strip() if len(parts) > 1 else ""

            # Check for 'none' response
            if page_str.lower() == "none" or item_text.lower() == "none":
                return None

            # Use regex to extract just the digits
            digit_match = re.search(r'\d+', page_str)
            if not digit_match:
                return None

            page_num_str = digit_match.group(0)
            page_num = int(page_num_str)

            if page_num < 1:
                return None

            return page_num_str, item_text

        except Exception:
            return None

    def extract_verification_entries(
        self, page_image: Image.Image, first_entry_page: int
    ) -> List[Tuple[int, str]]:
        """Extract 2-3 entries from TOC page that are distant from the first entry for verification."""
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        prompt = TOCExtractionPrompts.EXTRACT_VERIFICATION_ENTRIES.format(first_entry_page=first_entry_page)
        response = self._send_vision_request([base64_image], prompt, stream=False)
        cleaned = clean_llm_response(response)

        entries = []
        for line in cleaned.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            try:
                if ',' in line:
                    page_str, title = line.split(',', 1)
                    page_str = page_str.strip()
                    title = title.strip()
                    if page_str.isdigit() and int(page_str) >= 1:
                        page_num = int(page_str)
                        # Skip if it's the first entry
                        if page_num != first_entry_page:
                            entries.append((page_num, title))
            except Exception:
                continue

        return entries

    def page_contains_content(self, page_image: Image.Image, target_text: str) -> bool:
        """Check if a page contains actual section content (not just header/footer or reference)."""
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        prompt = ContentVerificationPrompts.PAGE_CONTAINS_CONTENT.format(target_text=target_text)
        response = self._send_vision_request([base64_image], prompt)
        return "yes" in response.lower()

    def verify_offset_match(
        self, page_image: Image.Image, expected_title: str, expected_page: int
    ) -> bool:
        """Verify that this page matches the expected TOC entry for offset validation."""
        base64_image = PDFImageProcessor.convert_to_base64_webp(page_image)
        prompt = ContentVerificationPrompts.VERIFY_OFFSET_MATCH.format(
            expected_title=expected_title,
            expected_page=expected_page
        )
        response = self._send_vision_request([base64_image], prompt, stream=False)
        return "yes" in response.lower()

    def _send_text_request(self, prompt: str, stream: bool = True, timeout: float = 60) -> str:
        """Send a text-only request to the text LLM."""
        response = self.client.chat.completions.create(
            model=self.text_model,
            messages=[{"role": "user", "content": prompt}],
            stream=stream,
            timeout=timeout,
        )

        if stream:
            return self._process_streaming_response(response)
        else:
            return response.choices[0].message.content or ""

    def refine_bookmarks_with_text_model(self, bookmark_text: str) -> str:
        """Use text model to check and fix the generated bookmarks."""
        original_len = len(bookmark_text)
        prompt = BookmarkRefinementPrompts.REFINE_BOOKMARKS.format(bookmark_text=bookmark_text)
        response = self._send_text_request(prompt)
        refined = clean_llm_response(response)
        refined_len = len(refined)

        # Validate character count didn't change too much
        if original_len > 0:
            change_ratio = abs(refined_len - original_len) / original_len
            if change_ratio > 0.1:  # More than 10% change
                raise RuntimeError(
                    f"Refinement output size changed by {change_ratio*100:.1f}% "
                    f"(original: {original_len} chars, refined: {refined_len} chars). "
                    "This suggests the model output is malformed. Please try again or use a different model."
                )

        Log.detail(f"Refinement: {original_len} → {refined_len} chars ({(change_ratio if original_len > 0 else 0)*100:.1f}% change)")
        return refined
