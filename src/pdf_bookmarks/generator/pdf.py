"""PDF writing with pdftk."""

import os
import subprocess

from pdf_bookmarks.utils import Log


class PDFWriter:
    """Handles PDF writing with bookmarks using pdftk."""

    def __init__(self, temp_bookmark_file: str = "bookmarks.txt"):
        self.temp_bookmark_file = temp_bookmark_file

    def add_bookmarks_to_pdf(
        self, bookmark_text: str, input_path: str, output_path: str
    ):
        """Add bookmarks to PDF using pdftk."""
        self._verify_pdftk_installation()

        Log.step("Adding bookmarks to PDF...")

        with open(self.temp_bookmark_file, "w", encoding="utf-8") as f:
            f.write(bookmark_text.strip())

        try:
            subprocess.run(
                [
                    "pdftk",
                    input_path,
                    "update_info",
                    self.temp_bookmark_file,
                    "output",
                    output_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            Log.success(f"Created PDF with bookmarks: {output_path}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pdftk failed: {e.stderr}") from e
        finally:
            if os.path.exists(self.temp_bookmark_file):
                os.remove(self.temp_bookmark_file)

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
