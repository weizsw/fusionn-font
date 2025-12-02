"""ASS file writer with embedded font support."""

import re
from pathlib import Path


def ass_uuencode(data: bytes) -> str:
    """
    Encode binary data using ASS's UUEncode variant.
    
    ASS uses a modified UUEncode where:
    - Each group of 3 bytes becomes 4 characters
    - Characters are offset by 33 (ASCII '!')
    - Lines are max 80 characters
    """
    result = []
    
    for i in range(0, len(data), 3):
        chunk = data[i:i+3]
        
        # Pad to 3 bytes if needed
        if len(chunk) < 3:
            chunk = chunk + b'\x00' * (3 - len(chunk))
        
        # Convert 3 bytes to 4 6-bit values
        b1, b2, b3 = chunk
        
        c1 = b1 >> 2
        c2 = ((b1 & 0x03) << 4) | (b2 >> 4)
        c3 = ((b2 & 0x0F) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        
        # Offset by 33 to get printable ASCII
        result.append(chr(c1 + 33))
        result.append(chr(c2 + 33))
        result.append(chr(c3 + 33))
        result.append(chr(c4 + 33))
    
    # Join and split into 80-char lines
    encoded = ''.join(result)
    lines = [encoded[i:i+80] for i in range(0, len(encoded), 80)]
    
    return '\n'.join(lines)


def create_font_section(fonts: dict[str, Path]) -> str:
    """
    Create the [Fonts] section for an ASS file.
    
    Args:
        fonts: Dict mapping font names to font file paths
        
    Returns:
        String containing the [Fonts] section
    """
    if not fonts:
        return ""
    
    lines = ["", "[Fonts]"]
    
    for fontname, font_path in fonts.items():
        # Read font file
        font_data = font_path.read_bytes()
        
        # Use a safe filename (the actual embedded name)
        # ASS typically uses the original filename
        safe_name = font_path.name
        
        # Add font entry
        lines.append(f"fontname: {safe_name}")
        lines.append(ass_uuencode(font_data))
        lines.append("")  # Blank line between fonts
    
    return '\n'.join(lines)


def embed_fonts_in_ass(
    ass_path: Path,
    fonts: dict[str, Path],
    output_path: Path | None = None,
) -> Path:
    """
    Embed fonts into an ASS file.
    
    Args:
        ass_path: Path to the source ASS file
        fonts: Dict mapping font names to font file paths to embed
        output_path: Output path (default: {name}.embedded.ass)
        
    Returns:
        Path to the output file
    """
    if output_path is None:
        output_path = ass_path.with_suffix('.embedded.ass')
    
    # Read original ASS content
    content = ass_path.read_text(encoding='utf-8-sig')
    
    # Remove existing [Fonts] section if present
    # The section ends at the next [...] or end of file
    content = re.sub(
        r'\n?\[Fonts\].*?(?=\n\[|\Z)',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Create new fonts section
    fonts_section = create_font_section(fonts)
    
    # Find where to insert fonts section
    # Typically after [Events] section, but before any existing [Fonts]
    # We'll append at the end
    
    # Ensure content ends with newline
    if not content.endswith('\n'):
        content += '\n'
    
    # Append fonts section
    final_content = content + fonts_section
    
    # Write output
    output_path.write_text(final_content, encoding='utf-8')
    
    return output_path


def get_embedded_fonts_info(ass_path: Path) -> list[dict]:
    """
    Get information about fonts already embedded in an ASS file.
    
    Returns:
        List of dicts with font info
    """
    content = ass_path.read_text(encoding='utf-8-sig')
    
    fonts = []
    
    # Find [Fonts] section
    fonts_match = re.search(
        r'\[Fonts\](.*?)(?=\n\[|\Z)',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    if not fonts_match:
        return fonts
    
    fonts_section = fonts_match.group(1)
    
    # Find all fontname entries
    for match in re.finditer(r'fontname:\s*(.+)', fonts_section, re.IGNORECASE):
        fontname = match.group(1).strip()
        
        # Count the data lines following this entry
        # (rough size estimate)
        start = match.end()
        next_font = re.search(r'fontname:', fonts_section[start:], re.IGNORECASE)
        if next_font:
            data_section = fonts_section[start:start + next_font.start()]
        else:
            data_section = fonts_section[start:]
        
        # Estimate size: 4 chars = 3 bytes
        data_chars = len(re.sub(r'\s', '', data_section))
        estimated_size = (data_chars * 3) // 4
        
        fonts.append({
            'name': fontname,
            'estimated_size': estimated_size,
        })
    
    return fonts

