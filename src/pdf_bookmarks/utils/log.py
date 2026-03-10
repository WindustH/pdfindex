"""Unified logging with colors and consistent formatting."""

from pdf_bookmarks.utils.colors import Colors


class Log:
    """Unified logging with colors and consistent formatting."""

    @staticmethod
    def info(msg: str) -> None:
        """General information (blue)."""
        print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")

    @staticmethod
    def success(msg: str) -> None:
        """Success message (green)."""
        print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

    @staticmethod
    def step(msg: str) -> None:
        """Processing step (cyan)."""
        print(f"{Colors.CYAN}▶{Colors.RESET} {msg}")

    @staticmethod
    def warn(msg: str) -> None:
        """Warning message (yellow)."""
        print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")

    @staticmethod
    def error(msg: str) -> None:
        """Error message (red)."""
        print(f"{Colors.RED}✗{Colors.RESET} {msg}")

    @staticmethod
    def detail(msg: str, indent: int = 2) -> None:
        """Detailed/sub-information (gray, indented)."""
        prefix = " " * indent
        print(f"{Colors.GRAY}{prefix}{msg}{Colors.RESET}")

    @staticmethod
    def separator(char: str = "─", width: int = 50) -> None:
        """Print a separator line."""
        print(f"{Colors.DIM}{char * width}{Colors.RESET}")

    @staticmethod
    def header(msg: str) -> None:
        """Section header (bold cyan with separator)."""
        Log.separator()
        print(f"{Colors.BOLD}{Colors.CYAN}{msg}{Colors.RESET}")
        Log.separator()
