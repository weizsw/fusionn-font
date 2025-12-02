"""Font subsetting using fonttools."""

import logging
from pathlib import Path
from fontTools.subset import Subsetter, Options
from fontTools.ttLib import TTFont

# Suppress fonttools warnings about unknown tables (FFTM, etc.)
logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

# Common font file extensions
FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}


def scan_fonts_dir(fonts_dir: Path) -> dict[str, Path]:
    """
    Scan a directory for font files and return a mapping of font names to paths.
    
    Args:
        fonts_dir: Directory to scan for font files
        
    Returns:
        Dict mapping font family names to font file paths
    """
    font_map: dict[str, Path] = {}
    
    if not fonts_dir.is_dir():
        return font_map
    
    for font_path in fonts_dir.iterdir():
        if font_path.suffix.lower() not in FONT_EXTENSIONS:
            continue
        
        if not font_path.is_file():
            continue
        
        try:
            info = get_font_info(font_path)
            
            # Map by family name
            if info.get("family"):
                font_map[info["family"]] = font_path
            
            # Also map by full name (sometimes ASS uses this)
            if info.get("full_name") and info["full_name"] != info.get("family"):
                font_map[info["full_name"]] = font_path
                
            # Also map by filename without extension (fallback)
            font_map[font_path.stem] = font_path
            
        except Exception:
            # Skip unreadable fonts
            continue
    
    return font_map


def subset_font(
    font_path: str | Path,
    chars: set[str],
    output_path: str | Path | None = None,
) -> Path:
    """
    Subset a font to only include the specified characters.

    Args:
        font_path: Path to the source font file (TTF/OTF)
        chars: Set of characters to include in the subset
        output_path: Optional output path. If None, creates {name}.subset.ttf

    Returns:
        Path to the subsetted font file
    """
    font_path = Path(font_path)

    if output_path is None:
        output_path = font_path.with_suffix(f".subset{font_path.suffix}")
    else:
        output_path = Path(output_path)

    # Load the font
    font = TTFont(font_path)

    # Configure subsetter options
    options = Options()
    options.layout_features = ["*"]  # Keep all OpenType features
    options.name_IDs = ["*"]  # Keep all name records
    options.name_legacy = True
    options.name_languages = ["*"]
    options.glyph_names = True
    options.notdef_outline = True
    options.recommended_glyphs = True  # Keep .notdef, space, etc.

    # Create subsetter
    subsetter = Subsetter(options=options)

    # Build unicode set from characters
    unicodes = {ord(c) for c in chars if ord(c) > 0}

    # Always include basic ASCII space if we have any chars
    if unicodes:
        unicodes.add(0x20)  # space
        unicodes.add(0xFEFF)  # BOM (sometimes needed)

    subsetter.populate(unicodes=unicodes)

    # Subset the font
    subsetter.subset(font)

    # Save the subsetted font
    font.save(output_path)
    font.close()

    return output_path


def get_font_info(font_path: str | Path) -> dict:
    """
    Get basic information about a font file.

    Returns:
        Dict with font info (family, style, etc.)
    """
    font_path = Path(font_path)
    font = TTFont(font_path)

    info = {
        "path": str(font_path),
        "family": None,
        "subfamily": None,
        "full_name": None,
        "glyph_count": len(font.getGlyphOrder()),
    }

    # Extract name table info
    if "name" in font:
        name_table = font["name"]
        for record in name_table.names:
            name_id = record.nameID
            try:
                value = record.toUnicode()
            except Exception:
                continue

            if name_id == 1:  # Family
                info["family"] = value
            elif name_id == 2:  # Subfamily
                info["subfamily"] = value
            elif name_id == 4:  # Full name
                info["full_name"] = value

    font.close()
    return info

