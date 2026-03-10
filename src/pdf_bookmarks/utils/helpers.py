"""Utility helper functions."""

import re


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


def clean_llm_response(response: str) -> str:
    """Remove common LLM response artifacts."""
    cleaned = response.strip()
    artifacts = [
        "```",
        "```plaintext",
        "```text",
    ]
    for artifact in artifacts:
        cleaned = cleaned.replace(artifact, "")
    return cleaned.strip()
