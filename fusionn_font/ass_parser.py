"""ASS subtitle file parser - extracts fonts and characters used."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Style:
    """Represents a style definition from ASS file."""
    name: str
    fontname: str
    fontsize: float
    # Add other fields if needed later


@dataclass
class FontUsage:
    """Tracks which characters are used for each font."""
    fontname: str
    chars: set[str] = field(default_factory=set)

    def add_text(self, text: str) -> None:
        """Add characters from text to the usage set."""
        self.chars.update(text)


class ASSParser:
    """Parser for ASS/SSA subtitle files."""

    # Regex to extract style definitions
    # Format: Style: Name,Fontname,Fontsize,PrimaryColour,...
    STYLE_PATTERN = re.compile(
        r"^Style:\s*([^,]+),([^,]+),([^,]+)",
        re.MULTILINE
    )

    # Regex to extract dialogue events
    # Format: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
    DIALOGUE_PATTERN = re.compile(
        r"^Dialogue:\s*[^,]*,[^,]*,[^,]*,([^,]*),(?:[^,]*,){4}(.*)$",
        re.MULTILINE
    )

    # Regex to find font override tags like {\fnFontName}
    FONT_OVERRIDE_PATTERN = re.compile(r"\\fn([^\\}]+)")

    # Regex to strip all ASS tags {...}
    TAG_PATTERN = re.compile(r"\{[^}]*\}")

    # Regex to strip drawing commands (between {\p1}...{\p0} or similar)
    DRAWING_START = re.compile(r"\\p[1-9]")
    DRAWING_END = re.compile(r"\\p0")

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.styles: dict[str, Style] = {}
        self.font_usage: dict[str, FontUsage] = {}

    def parse(self) -> dict[str, FontUsage]:
        """Parse the ASS file and return font usage information."""
        content = self.filepath.read_text(encoding="utf-8-sig")

        self._parse_styles(content)
        self._parse_dialogues(content)

        return self.font_usage

    def _parse_styles(self, content: str) -> None:
        """Extract style definitions from ASS content."""
        for match in self.STYLE_PATTERN.finditer(content):
            name = match.group(1).strip()
            fontname = match.group(2).strip()
            fontsize = float(match.group(3).strip())

            self.styles[name] = Style(
                name=name,
                fontname=fontname,
                fontsize=fontsize
            )

            # Initialize font usage tracking
            if fontname not in self.font_usage:
                self.font_usage[fontname] = FontUsage(fontname=fontname)

    def _parse_dialogues(self, content: str) -> None:
        """Extract dialogue events and track character usage per font."""
        for match in self.DIALOGUE_PATTERN.finditer(content):
            style_name = match.group(1).strip()
            text = match.group(2)

            # Get base font from style
            base_font = None
            if style_name in self.styles:
                base_font = self.styles[style_name].fontname

            self._process_dialogue_text(text, base_font)

    def _process_dialogue_text(self, text: str, base_font: str | None) -> None:
        """Process dialogue text, handling font override tags."""
        # Split text by tags to process font changes
        current_font = base_font
        pos = 0

        # Find all tag blocks
        for tag_match in self.TAG_PATTERN.finditer(text):
            # Text before this tag uses current font
            before_text = text[pos:tag_match.start()]
            if current_font and before_text:
                self._add_chars_to_font(current_font, before_text)

            # Check for font override in this tag block
            tag_content = tag_match.group(0)

            # Check if entering drawing mode (skip drawing commands)
            if self.DRAWING_START.search(tag_content):
                # Find the end of drawing mode
                remaining = text[tag_match.end():]
                drawing_end = self.DRAWING_END.search(remaining)
                if drawing_end:
                    # Skip to after {\p0}
                    pos = tag_match.end() + drawing_end.end()
                    continue

            font_override = self.FONT_OVERRIDE_PATTERN.search(tag_content)
            if font_override:
                new_font = font_override.group(1).strip()
                if new_font:
                    current_font = new_font
                    # Ensure this font is tracked
                    if current_font not in self.font_usage:
                        self.font_usage[current_font] = FontUsage(fontname=current_font)

            pos = tag_match.end()

        # Text after last tag
        remaining_text = text[pos:]
        if current_font and remaining_text:
            self._add_chars_to_font(current_font, remaining_text)

    def _add_chars_to_font(self, fontname: str, text: str) -> None:
        """Add characters from text to font usage, filtering special chars."""
        if fontname not in self.font_usage:
            self.font_usage[fontname] = FontUsage(fontname=fontname)

        # Filter out newlines and other control characters
        # Keep actual displayable characters
        filtered = "".join(
            c for c in text
            if c.isprintable() or c in "\n\r"
        )
        # Remove \N (ASS newline) and \n \h
        filtered = filtered.replace("\\N", "").replace("\\n", "").replace("\\h", " ")

        self.font_usage[fontname].add_text(filtered)


def get_font_usage(ass_path: str | Path) -> dict[str, set[str]]:
    """
    Convenience function to get font usage from an ASS file.

    Returns:
        Dict mapping font names to sets of characters used.
    """
    parser = ASSParser(ass_path)
    usage = parser.parse()
    return {name: fu.chars for name, fu in usage.items()}

