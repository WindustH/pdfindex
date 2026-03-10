"""Command-line interface for PDF bookmarks."""

import argparse
import os

from pdf_bookmarks.processor import PDFBookmarkProcessor
from pdf_bookmarks.utils import Log


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add bookmarks to a PDF ebook based on its table of contents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdf-bookmarks input.pdf output.pdf
  pdf-bookmarks /path/to/ebook.pdf /path/to/ebook_with_bookmarks.pdf
  pdf-bookmarks input.pdf output.pdf --resume
  pdf-bookmarks input.pdf output.pdf --force

Requirements:
  - pdftk must be installed and accessible in PATH
  - Environment variables must be set: API_KEY, BASE_URL, VISION_MODEL

Progress & Resume:
  Progress is automatically saved to input.pdf.tmp.json
  If interrupted, use --resume to continue from where it left off
  If there was an error, --resume will retry from the failed step
  Use --force to ignore saved progress and start fresh
        """,
    )
    parser.add_argument("input_path", type=str, help="Path to the input PDF file")
    parser.add_argument(
        "output_path", type=str, help="Path for output PDF with bookmarks"
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume from previous progress (retry from failed step if there was an error)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force restart, ignoring any saved progress"
    )
    return parser


def main() -> int:
    parser = create_argument_parser()
    args = parser.parse_args()

    if not os.path.exists(args.input_path):
        Log.error(f"Input file '{args.input_path}' does not exist.")
        return 1

    output_dir = os.path.dirname(args.output_path)
    if output_dir and not os.path.exists(output_dir):
        Log.error(f"Output directory '{output_dir}' does not exist.")
        return 1

    processor = PDFBookmarkProcessor()
    success = processor.process_pdf(
        args.input_path,
        args.output_path,
        resume=args.resume,
        force_restart=args.force
    )
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
