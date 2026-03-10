"""PDF page to image conversion and image processing."""

import base64
import io
from PIL import Image
import fitz  # PyMuPDF


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
