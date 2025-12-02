# fusionn-font

CLI tool to subset fonts based on ASS subtitle file usage.

## Installation

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

Or with pip:
```bash
pip install -e .
```

## Usage

### Analyze ASS file

See what fonts are used and how many characters each needs:

```bash
fusionn-font analyze subtitle.ass
```

### Subset fonts

Point to a folder containing your fonts - the tool will automatically match
fonts by family name:

```bash
fusionn-font subset subtitle.ass -d ./fonts/
```

### Embed fonts into ASS file

Subset fonts and embed them directly into the ASS file:

```bash
fusionn-font subset subtitle.ass -d ./fonts/ --embed
```

This creates `subtitle.embedded.ass` with fonts embedded in the `[Fonts]` section.

### Options

- `-d, --fonts-dir` - Directory containing font files (required)
- `-o, --output-dir` - Output directory for subsetted fonts
- `--embed` - Embed subsetted fonts into the ASS file
- `--output-ass` - Custom output path for embedded ASS file
- `--dry-run` - Show what would be done without creating files

### Font info

Show information about a font file:

```bash
fusionn-font info ./NotoSansCJK-Regular.ttf
```

## Building standalone binary

```bash
uv pip install pyinstaller
pyinstaller --onefile --name fusionn-font fusionn_font/__main__.py
```

The binary will be in `dist/fusionn-font`.
