# GemDesk

**Multi-file AI assistant powered by Gemini 3 Flash with 1M token context**

GemDesk is a desktop application that enables deep analysis across multiple files simultaneously using Google's Gemini 3 Flash model. Upload up to 50 files, ask questions, generate reports, find contradictions, and visualize data - all with intelligent context caching and adaptive thinking modes.

![GemDesk Interface](https://via.placeholder.com/800x500?text=GemDesk+Screenshot)

## ✨ Key Features

### 🗂️ Multi-File Analysis
- **1M token context window** - Analyze massive amounts of data simultaneously
- **50 file limit** - Upload documents, spreadsheets, images, videos, and more
- **100+ file formats supported** - PDFs, Office docs, images, videos, code files
- **Smart conversion** - DOCX → PDF with images, XLSX → CSV, and more
- **Context caching** - Files cached separately for faster responses

### 🤖 Advanced AI Capabilities
- **Adaptive thinking modes** - Adjust reasoning depth (minimal/low/medium/high)
- **Specialized analysis presets** via slash commands:
  - `/report` - Executive summaries and cohesive reports
  - `/synthesize` - Pattern identification and novel insights
  - `/error-check` - Contradiction and inconsistency detection
- **Automatic chart generation** - Just ask! "Plot sales over time" generates visualizations
- **Function calling** - Gemini intelligently uses tools when appropriate

### 📊 Visualization & Export
- **Smart charting** - Bar, line, pie, and scatter plots generated on demand
- **Export conversations** - Save chats as formatted PDFs
- **Export charts** - Save visualizations as high-quality PNGs
- **Markdown rendering** - Code highlighting, tables, and formatting

### 🎨 User Experience
- **Dark/light themes** - Toggle between modes
- **Organized file shelf** - Auto-categorized by type with collapsible folders
- **Real-time token metering** - Track context usage
- **URL scraping** - Add web pages and direct file downloads
- **Thumbnail previews** - Visual preview for images, PDFs, and videos

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Gemini API key ([Get one free](https://aistudio.google.com/app/apikey))

### Installation

#### 1. Clone the repository
```bash
git clone https://github.com/yourusername/gemdesk.git
cd gemdesk
```

#### 2. Install dependencies
```bash
pip install -r requirements.txt
```

#### 3. Set up API key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```

#### 4. Run
```bash
python gem.py
```

The app will open in your default browser!

---

## 📖 Usage Guide

### Basic Workflow

1. **Upload files** - Click "Add Files" or paste URLs
2. **Ask questions** - Type naturally or use slash commands
3. **Get insights** - Receive analysis with citations
4. **Visualize data** - Ask for charts when needed
5. **Export results** - Save conversations and charts

### Slash Commands

**Analysis Presets:**
- `/report` - Generate executive summary with key findings
- `/synthesize` - Identify patterns and generate novel insights
- `/error-check` - Find contradictions across sources

**Example:**
```
/report focus on Q4 financial performance
```

**Help:**
- `/help` - Show all available commands

### Charting

No buttons needed! Just ask naturally:
- "Plot the sales data over time"
- "Show me customer acquisition vs revenue"
- "Create a pie chart of market share"

Gemini will automatically analyze your files and generate appropriate visualizations.

### Thinking Modes

Adjust reasoning depth via the dropdown:
- **Minimal** - Fast, basic reasoning
- **Low** - Light thinking
- **Medium** - Balanced (default for reports)
- **High** - Deep reasoning (default for synthesis/error-checking)

---

## 📁 Supported File Types

### Documents
- **PDF** - Native support
- **DOCX** - Converted to PDF (preserves inline images)
- **TXT, MD, RTF, HTML** - Plain text formats
- **ODT** - OpenDocument Text

### Spreadsheets
- **XLSX** - Converted to CSV (all sheets)
- **ODS** - OpenDocument Spreadsheet
- **CSV** - Native support

### Presentations
- **PPTX** - Native support (Gemini 3)
- **ODP** - OpenDocument Presentation (converted to text)

### Media
- **Images** - JPG, PNG, GIF, WEBP, HEIC, SVG
- **Videos** - MP4, MOV, AVI, WEBM, FLV
- **Audio** - MP3, WAV, FLAC, AAC, OGG

### Code
80+ programming languages supported including:
- Python, JavaScript, TypeScript, Java, C/C++, Go, Rust
- HTML, CSS, PHP, Ruby, Swift, Kotlin, Scala
- And many more...

---

## 🏗️ Architecture

### Context Caching Strategy
Files are cached separately from conversation history for optimal performance:
- All uploaded files → Single cache (1 hour TTL)
- Conversation history → Sent as text only
- Cache updates automatically when files added/removed

**Benefits:**
- Faster responses (files not resent with every message)
- Lower token costs
- Efficient multi-turn conversations

### File Processing Pipeline
```
User Upload
    ↓
Type Detection
    ↓
Conversion (if needed)
    - DOCX → PDF (with images)
    - XLSX → CSV (all sheets)
    - ODT/ODP → Text
    ↓
Upload to Gemini
    ↓
Token Counting
    ↓
Add to Cache
```

### Tool Integration
Gemini uses function calling to generate charts:
1. User requests visualization
2. Gemini analyzes data in files
3. Calls `generate_chart` tool with parameters
4. Chart rendered with matplotlib
5. Displayed in popup dialog

---

## 🛠️ Configuration

### Environment Variables
- `GEMINI_API_KEY` - Your Gemini API key (required)

### Model Configuration
Edit `gem.py` to customize:
```python
MODEL_ID = "gemini-3-flash-preview"  # Model to use
MAX_CONTEXT_TOKENS = 1000000         # Context window size
MAX_FILES = 50                        # File upload limit
```

---

## 📊 Performance

### Token Usage
- **1M token context** - Analyze extensive documents
- **Context meter** - Real-time usage tracking
- **Smart caching** - Reduce redundant processing

### File Limits
- **Max files:** 50 (configurable)
- **Max file size:** Limited by Gemini API
- **Max context:** 1M tokens total

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional file format support
- More chart types
- Enhanced error handling
- Performance optimizations
- UI/UX improvements

### Development Setup
```bash
# Clone repository
git clone https://github.com/yourusername/gemdesk.git
cd gemdesk

# Install dev dependencies
pip install -r requirements.txt

# Run with debug logging
python gem.py
```

---

## 🐛 Troubleshooting

### Common Issues

**"GEMINI_API_KEY not found"**
- Create `.env` file with your API key
- Ensure file is in project root directory

**"Module not found" errors**
- Run: `pip install --upgrade -r requirements.txt`

**File upload fails**
- Check file size (must be under API limits)
- Verify file format is supported
- Check internet connection

**Charts not generating**
- Ensure matplotlib is installed: `pip install matplotlib`
- Verify chart request is clear (e.g., "plot X over time")

**Context cache errors**
- Files are automatically re-uploaded if cache expires
- Try removing and re-adding problematic files

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

- **Google Gemini** - Powerful multimodal AI capabilities
- **Flet** - Beautiful Python UI framework
- **matplotlib** - Chart generation
- **python-docx & reportlab** - Document processing

---

## 🔗 Links

- [Gemini API Documentation](https://ai.google.dev/)
- [Flet Documentation](https://flet.dev/)
- [Report Issues](https://github.com/yourusername/gemdesk/issues)

---

## 📈 Roadmap

- [ ] Web deployment support
- [ ] Drag & drop file upload
- [ ] Google Search grounding integration
- [ ] Persistent chat history
- [ ] Multi-tab conversations
- [ ] Voice input support
- [ ] Collaborative features

---

**Built for the Gemini API Developer Competition 2025**

*Showcasing advanced multimodal analysis with intelligent context management and adaptive reasoning*
