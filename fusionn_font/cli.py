"""CLI interface for fusionn-font."""

import sys
from pathlib import Path

import click

from fusionn_font.ass_parser import ASSParser
from fusionn_font.ass_writer import embed_fonts_in_ass, get_embedded_fonts_info
from fusionn_font.font_subsetter import subset_font, get_font_info, scan_fonts_dir


HELP_TEXT = """
Font subsetting tool for ASS subtitle files.

Extracts fonts used in ASS files and creates subsetted font files
containing only the characters actually used. Optionally embeds
fonts directly into the ASS file.

\b
WORKFLOW:
  1. analyze  - See which fonts your ASS file needs
  2. subset   - Auto-match fonts and create subsets

\b
QUICK START:
  fusionn-font analyze sub.ass
  fusionn-font subset sub.ass -d ./fonts/
  fusionn-font subset sub.ass -d ./fonts/ --embed
"""


@click.group(help=HELP_TEXT)
@click.version_option(version="0.1.0", package_name="fusionn-font")
def main():
    pass


@main.command()
@click.argument("ass_file", type=click.Path(exists=True, path_type=Path))
def analyze(ass_file: Path):
    """Analyze an ASS file and show font usage.

    \b
    Shows:
      - Font names used in styles and override tags
      - Number of unique characters per font
      - Sample of characters used

    \b
    EXAMPLE:
      fusionn-font analyze subtitle.ass
    """
    parser = ASSParser(ass_file)
    usage = parser.parse()

    click.echo(f"\n📄 Analyzing: {ass_file.name}\n")
    click.echo("=" * 50)

    if not usage:
        click.echo("No fonts found in the file.")
        return

    for fontname, font_usage in sorted(usage.items()):
        char_count = len(font_usage.chars)
        click.echo(f"\n🔤 Font: {fontname}")
        click.echo(f"   Characters used: {char_count}")

        # Show sample of characters (first 50)
        if font_usage.chars:
            sample = "".join(sorted(font_usage.chars)[:50])
            if len(font_usage.chars) > 50:
                sample += "..."
            click.echo(f"   Sample: {sample}")


@main.command()
@click.argument("ass_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-d", "--fonts-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing font files (TTF, OTF, etc.)",
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for subsetted fonts (default: same as ASS file)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without creating files",
)
@click.option(
    "--embed",
    is_flag=True,
    help="Embed subsetted fonts directly into the ASS file",
)
@click.option(
    "--output-ass",
    type=click.Path(path_type=Path),
    default=None,
    help="Output ASS file path when using --embed (default: {name}.embedded.ass)",
)
def subset(
    ass_file: Path,
    fonts_dir: Path,
    output_dir: Path | None,
    dry_run: bool,
    embed: bool,
    output_ass: Path | None,
):
    """Subset fonts based on ASS file character usage.

    Scans the fonts directory, matches fonts by family name with those
    used in the ASS file, and creates subsetted versions.

    \b
    MODES:
      (default)  Create standalone .subset.ttf files
      --embed    Embed fonts into ASS file [Fonts] section

    \b
    EXAMPLES:
      fusionn-font subset sub.ass -d ./fonts/
      fusionn-font subset sub.ass -d ./fonts/ --embed
      fusionn-font subset sub.ass -d ./fonts/ --embed -o ./output/

    \b
    NOTES:
      - Fonts are matched by family name automatically
      - Use 'analyze' to see which fonts the ASS file needs
    """
    import tempfile

    # Parse ASS file
    parser = ASSParser(ass_file)
    usage = parser.parse()

    if not usage:
        click.echo("No fonts found in the ASS file.", err=True)
        sys.exit(1)

    # Scan fonts directory
    click.echo(f"\n🔍 Scanning fonts in: {fonts_dir}")
    font_map = scan_fonts_dir(fonts_dir)

    if not font_map:
        click.echo(f"No font files found in {fonts_dir}", err=True)
        sys.exit(1)

    # Count unique files and show mappings
    unique_files = set(font_map.values())
    click.echo(f"   Found {len(unique_files)} font file(s), {len(font_map)} name mapping(s):")
    for name, path in sorted(font_map.items()):
        click.echo(f"   • \"{name}\" → {path.name}")
    click.echo()

    # Set output directory (for standalone font files)
    if output_dir is None:
        output_dir = ass_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use temp dir for intermediate files if embedding
    if embed and not dry_run:
        temp_dir = Path(tempfile.mkdtemp(prefix="fusionn_"))
        work_dir = temp_dir
    else:
        work_dir = output_dir

    click.echo(f"\n📄 Processing: {ass_file.name}\n")

    # Track processed fonts for embedding
    processed = 0
    subsetted_fonts: dict[str, Path] = {}

    for fontname, chars_usage in usage.items():
        if fontname not in font_map:
            click.echo(f"⏭️  Skipping '{fontname}' (no font file provided)")
            continue

        font_path = font_map[fontname]
        chars = chars_usage.chars

        if not chars:
            click.echo(f"⏭️  Skipping '{fontname}' (no characters used)")
            continue

        # Get font info
        try:
            info = get_font_info(font_path)
        except Exception as e:
            click.echo(f"❌ Error reading '{font_path}': {e}", err=True)
            continue

        # Output filename: sanitize font name
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in fontname)
        subset_path = work_dir / f"{safe_name}.subset.ttf"

        click.echo(f"🔤 {fontname}")
        click.echo(f"   Source: {font_path}")
        click.echo(f"   Original glyphs: {info['glyph_count']}")
        click.echo(f"   Characters needed: {len(chars)}")

        if dry_run:
            if embed:
                click.echo(f"   Would embed in ASS file")
            else:
                click.echo(f"   Would create: {subset_path}")
        else:
            try:
                result = subset_font(font_path, chars, subset_path)
                subsetted_fonts[fontname] = result

                # Get new glyph count
                new_info = get_font_info(result)
                click.echo(f"   Subsetted glyphs: {new_info['glyph_count']}")

                # Show size reduction
                orig_size = font_path.stat().st_size
                new_size = result.stat().st_size
                reduction = (1 - new_size / orig_size) * 100
                click.echo(f"   Size: {orig_size:,} → {new_size:,} bytes ({reduction:.1f}% smaller)")

                if not embed:
                    # Copy to final location if not embedding
                    final_path = output_dir / f"{safe_name}.subset.ttf"
                    if work_dir != output_dir:
                        import shutil
                        shutil.copy2(result, final_path)
                        result = final_path
                    click.echo(f"   Output: {result}")

            except Exception as e:
                click.echo(f"   ❌ Error: {e}", err=True)
                continue

        processed += 1
        click.echo()

    if processed == 0:
        click.echo("No fonts were processed.", err=True)
        sys.exit(1)

    # Embed fonts if requested
    if embed and not dry_run and subsetted_fonts:
        click.echo("📦 Embedding fonts into ASS file...")

        if output_ass is None:
            output_ass = ass_file.with_suffix(".embedded.ass")

        try:
            result_ass = embed_fonts_in_ass(ass_file, subsetted_fonts, output_ass)
            ass_size = result_ass.stat().st_size
            click.echo(f"   Output: {result_ass}")
            click.echo(f"   Size: {ass_size:,} bytes")
        except Exception as e:
            click.echo(f"   ❌ Error embedding fonts: {e}", err=True)
            sys.exit(1)

        # Cleanup temp dir
        if embed:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    click.echo(f"\n✅ Done! Processed {processed} font(s).")


@main.command()
@click.argument("font_file", type=click.Path(exists=True, path_type=Path))
def info(font_file: Path):
    """Show information about a font file.

    \b
    Displays:
      - Font family name
      - Style/subfamily
      - Full name
      - Total glyph count

    \b
    EXAMPLE:
      fusionn-font info ./NotoSansCJK.ttf
    """
    try:
        font_info = get_font_info(font_file)
    except Exception as e:
        click.echo(f"Error reading font: {e}", err=True)
        sys.exit(1)

    click.echo(f"\n📁 {font_file.name}\n")
    click.echo(f"   Family: {font_info['family'] or 'Unknown'}")
    click.echo(f"   Style: {font_info['subfamily'] or 'Unknown'}")
    click.echo(f"   Full name: {font_info['full_name'] or 'Unknown'}")
    click.echo(f"   Glyphs: {font_info['glyph_count']}")


if __name__ == "__main__":
    main()

