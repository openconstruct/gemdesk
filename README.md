# GemDesk - Multi-file AI Chat with 1M Token Context

Desktop AI assistant powered by Gemini 3 Flash. Upload up to 50 files (PDFs, images, videos, documents, code) and chat with 1M token context window.

## Quick Start

### Prerequisites
- Python 3.8 or higher ([Download here](https://www.python.org/downloads/))
- Gemini API key ([Get one free](https://aistudio.google.com/app/apikey))

### Installation

#### Windows

**1. Download or clone this repository**
- Click "Code" → "Download ZIP" and extract, OR
- If you have git: `git clone https://github.com/yourusername/gemdesk.git`

**2. Open Command Prompt in the gemdesk folder**
- Open the folder in File Explorer
- Type `cmd` in the address bar and press Enter

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

If that doesn't work, try:
```bash
python -m pip install -r requirements.txt
```

**4. Create .env file**
- Create a new text file called `.env` (no .txt extension)
- Add this line: `GEMINI_API_KEY=your_actual_api_key`
- Save it in the same folder as `gem.py`

**5. Run**
```bash
python gem.py
```

The app will open in your default browser!

---

#### Mac/Linux

**1. Clone or download this repository**
```bash
git clone https://github.com/yourusername/gemdesk.git
cd gemdesk
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

On some systems you may need `pip3`:
```bash
pip3 install -r requirements.txt
```

**3. Create .env file**
```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

Or create `.env` file manually with:
```
GEMINI_API_KEY=your_actual_api_key
```

**4. Run**
```bash
python gem.py
```

Or on some systems:
```bash
python3 gem.py
```

---

#### Chromebook (Linux container)

**1. Enable Linux on your Chromebook**
- Settings → Advanced → Developers → Linux development environment

**2. Open Terminal and clone repository**
```bash
git clone https://github.com/yourusername/gemdesk.git
cd gemdesk
```

**3. Install dependencies with specific Flet version**

**IMPORTANT:** Chromebooks need Flet 0.24.1 specifically (newer versions have display issues):
```bash
pip install -r requirements.txt
```

If you have issues, manually install:
```bash
pip install flet==0.24.1 python-dotenv google-genai requests beautifulsoup4 pandas openpyxl python-pptx odfpy reportlab
```

**4. Create .env file**
```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

**5. Run**
```bash
python gem.py
```

---

## Troubleshooting

### "Module not found" errors
Try reinstalling:
```bash
pip install --upgrade -r requirements.txt
```

### Chromebook: Flet display issues
Make sure you're on Flet 0.24.1:
```bash
pip uninstall flet
pip install flet==0.24.1
```

### Windows: "pip is not recognized"
Use this instead:
```bash
python -m pip install -r requirements.txt
```

### API key not found
Make sure `.env` file:
- Is in the same folder as `gem.py`
- Has no file extension (not `.env.txt`)
- Contains: `GEMINI_API_KEY=your_actual_api_key`

### Windows: Can't create .env file
Windows hides extensions by default:
1. Open Notepad
2. Type: `GEMINI_API_KEY=your_actual_api_key`
3. File → Save As
4. Filename: `.env` (include the quotes)
5. Save as type: All Files
6. Save in the gemdesk folder

---

## Features

- **1M token context** - Massive context window for extensive analysis
- **50 file limit** - Upload documents, images, videos, code
- **100+ file formats** - PDFs, Office docs, code files, images, videos
- **URL scraping** - Add web pages to context
- **Dark/light mode** - Toggle theme
- **Export chat** - Save conversations as PDF
- **Organized file shelf** - Auto-categorized by type with collapsible folders

## Supported File Types

- **Documents**: PDF, DOCX, RTF, HTML, TXT, MD, ODT
- **Spreadsheets**: XLSX, ODS, CSV
- **Presentations**: PPTX, ODP
- **Images**: JPG, PNG, GIF, WEBP, HEIC, SVG
- **Videos**: MP4, MOV, AVI, WEBM, FLV
- **Audio**: MP3, WAV, FLAC, AAC, OGG
- **Code**: Python, JavaScript, Java, C/C++, Go, Rust, and 80+ more languages
- **Config**: YAML, TOML, JSON, XML, INI

---

## Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| Windows 10/11 | ✅ Fully supported | Any Flet version |
| macOS | ✅ Fully supported | Any Flet version |
| Linux (Ubuntu/Debian) | ✅ Fully supported | Flet 0.24.1 recommended |
| Chromebook (Linux) | ✅ Tested working | **Requires Flet 0.24.1** |

---

## License

MIT
