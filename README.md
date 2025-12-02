# fusionn-font

CLI tool to subset fonts based on ASS subtitle file usage. Automatically matches fonts by family name and optionally embeds them directly into the ASS file.

## Features

- 🔍 **Analyze** ASS files to see which fonts are needed
- ✂️ **Subset** fonts to include only characters actually used (often 90%+ size reduction)
- 📦 **Embed** subsetted fonts directly into ASS files
- 🔄 **Auto-match** fonts by family name from a directory

## Installation

### Via pip

```bash
pip install fusionn-font
```

### Via binary

Download pre-built binaries from [Releases](https://github.com/user/fusionn-font/releases):

- `fusionn-font-linux-amd64` - Linux
- `fusionn-font-darwin-arm64` - macOS (Apple Silicon)
- `fusionn-font-darwin-amd64` - macOS (Intel)
- `fusionn-font-windows-amd64.exe` - Windows

### From source

```bash
git clone https://github.com/user/fusionn-font.git
cd fusionn-font
uv venv && source .venv/bin/activate
uv pip install -e .
```

## Usage

### 1. Analyze ASS file

See what fonts are needed and how many characters each uses:

```bash
fusionn-font analyze subtitle.ass
```

Output:
```
📄 Analyzing: subtitle.ass

🔤 Font: WenQuanYi Micro Hei
   Characters used: 1153
   Sample: 一丁三上下不世丢个中...
```

### 2. Subset fonts

Point to a directory containing your fonts. The tool automatically matches fonts by family name:

```bash
fusionn-font subset subtitle.ass -d ./fonts/
```

Output:
```
🔍 Scanning fonts in: fonts
   Found 1 font file(s), 2 name mapping(s):
   • "WenQuanYi Micro Hei" → WenQuanYi Micro Hei.ttf
   • "文泉驛微米黑" → WenQuanYi Micro Hei.ttf

🔤 WenQuanYi Micro Hei
   Source: fonts/WenQuanYi Micro Hei.ttf
   Original glyphs: 49531
   Characters needed: 1153
   Subsetted glyphs: 2273
   Size: 4,625,768 → 261,868 bytes (94.3% smaller)
```

### 3. Embed fonts into ASS

Subset fonts and embed them directly into the ASS file's `[Fonts]` section:

```bash
fusionn-font subset subtitle.ass -d ./fonts/ --embed
```

Creates `subtitle.embedded.ass` with fonts embedded - no external font files needed!

### Options

```
fusionn-font subset [OPTIONS] ASS_FILE

Options:
  -d, --fonts-dir DIRECTORY  Directory containing font files (required)
  -o, --output-dir PATH      Output directory for subsetted fonts
  --embed                    Embed fonts directly into ASS file
  --output-ass PATH          Custom output path for embedded ASS
  --dry-run                  Preview without creating files
  --help                     Show help
```

### Font info

Inspect a font file:

```bash
fusionn-font info ./font.ttf
```

## How it works

1. Parses ASS file to extract font names from `[V4+ Styles]` and `{\fn}` override tags
2. Scans your fonts directory and reads font family names from each file
3. Matches fonts automatically by family name, full name, or filename
4. Uses `fonttools` to subset fonts, keeping only glyphs for characters used
5. Optionally embeds fonts using ASS's UUEncode format in `[Fonts]` section

## Building standalone binary

```bash
pip install pyinstaller
pyinstaller --onefile --name fusionn-font fusionn_font/__main__.py
# Binary: dist/fusionn-font
```

## License

MIT
