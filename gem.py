import flet as ft
import os
import time
import mimetypes
import tempfile
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from dotenv import load_dotenv
from conversions import (
    convert_xlsx_to_csv, convert_ods_to_csv, convert_docx_to_pdf,
    convert_pptx_to_text, convert_odp_to_text, convert_odt_to_text,
    scrape_url, download_file_from_url, is_direct_file_url, generate_thumbnail
)
from charting import generate_chart, parse_chart_json, get_chart_tool_declaration
from presets import get_preset, get_preset_indicator

# Flet version compatibility - older versions use lowercase
if not hasattr(ft, 'Colors'):
    ft.Colors = ft.colors
if not hasattr(ft, 'Icons'):
    ft.Icons = ft.icons

# Load environment variables
load_dotenv()

# --- 🚀 GEMINI 3 CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise Exception("GEMINI_API_KEY not found in environment variables. Create a .env file with GEMINI_API_KEY=your_key")

MODEL_ID = "gemini-3-flash-preview" 

# System prompt for expert analysis
SYSTEM_PROMPT = """You are an expert analyst assistant running on Gemini 3 Flash with advanced multimodal capabilities.

When analyzing files:
- For text/PDF documents: Always reference page numbers when available
- For images/charts/diagrams: Use your vision capabilities to describe visual elements, trends, patterns
- For video content: Provide timestamps in MM:SS format (minutes:seconds) for specific moments or events
- For audio content: Provide timestamps in MM:SS format (minutes:seconds) for key points
- For spreadsheets/data: Reference cell locations or row/column numbers, identify trends in charts
- For presentations: Describe slide layouts, visual elements, charts, and diagrams
- Provide clear, detailed analysis that synthesizes information across all provided files
- When comparing multiple files, explicitly note connections and discrepancies
- Use your native vision understanding to analyze charts, graphs, images, and visual data"""

client = genai.Client(api_key=API_KEY)

MAX_CONTEXT_TOKENS = 1000000
MAX_FILES = 50

def main(page: ft.Page):
    page.title = "GemDesk"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.bgcolor = ft.Colors.BLACK

    uploaded_files = []
    conversation_history = []
    current_cache_name = None  # Track context cache
    thinking_level = "high"  # Default: high thinking
    active_preset = None  # Track active preset command
    
    # Folder collapse state
    folders_collapsed = {
        "documents": False,
        "images": False,
        "videos": False,
        "audio": False,
        "links": False,
        "other": False
    }
    
    def update_shelf_cache():
        """Create or update context cache for all files on shelf"""
        nonlocal current_cache_name
        
        # Delete old cache
        if current_cache_name:
            try:
                client.caches.delete(name=current_cache_name)
                print(f"Deleted old cache: {current_cache_name}")
            except Exception as e:
                print(f"Cache deletion error: {e}")
            current_cache_name = None
        
        # If no files, no cache needed
        if not uploaded_files:
            return
        
        # Create cache with all files
        try:
            file_parts = [
                types.Part.from_uri(file_uri=f["uri"], mime_type=f["mime"]) 
                for f in uploaded_files
            ]
            
            cache = client.caches.create(
                model=MODEL_ID,
                contents=[types.Content(role="user", parts=file_parts)],
                ttl="3600s"  # 1 hour
            )
            current_cache_name = cache.name
            print(f"Cache created: {cache.name}")
            status_text.value = f"Cache created ({len(uploaded_files)} files)"
            page.update()
        except Exception as e:
            print(f"Cache creation error: {e}")
            status_text.value = f"Cache error: {e}"
            page.update()
    
    def export_chat(e):
        """Export chat history as PDF"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.units import inch
            from datetime import datetime
            import tempfile
            
            temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
            doc = SimpleDocTemplate(temp_file.name, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph(f"<b>GemDesk Chat Export</b>", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            meta = Paragraph(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
            story.append(meta)
            story.append(Spacer(1, 0.1*inch))
            
            # Files
            if uploaded_files:
                files_title = Paragraph("<b>Files in Context:</b>", styles['Heading2'])
                story.append(files_title)
                for f in uploaded_files:
                    file_line = Paragraph(f"• {f['name']} ({f['tokens']:,} tokens)", styles['Normal'])
                    story.append(file_line)
                story.append(Spacer(1, 0.3*inch))
            
            # Conversation
            conv_title = Paragraph("<b>Conversation:</b>", styles['Heading2'])
            story.append(conv_title)
            story.append(Spacer(1, 0.2*inch))
            
            for msg in conversation_history:
                if msg.role == "user":
                    text_parts = [p.text for p in msg.parts if hasattr(p, 'text') and p.text]
                    if text_parts:
                        user_msg = Paragraph(f"<b>You:</b> {text_parts[0]}", styles['Normal'])
                        story.append(user_msg)
                        story.append(Spacer(1, 0.1*inch))
                elif msg.role == "model":
                    text_parts = [p.text for p in msg.parts if hasattr(p, 'text')]
                    if text_parts:
                        # Clean markdown for PDF
                        clean_text = text_parts[0].replace('**', '').replace('*', '').replace('#', '')
                        ai_msg = Paragraph(f"<b>Assistant:</b> {clean_text}", styles['Normal'])
                        story.append(ai_msg)
                        story.append(Spacer(1, 0.2*inch))
            
            doc.build(story)
            temp_file.close()
            
            status_text.value = f"Exported to {temp_file.name}"
            print(f"Chat exported to: {temp_file.name}")
            page.update()
            
        except ImportError:
            status_text.value = "Error: Install reportlab (pip install reportlab)"
            page.update()
        except Exception as err:
            status_text.value = f"Export error: {err}"
            print(f"Export error: {err}")
            page.update()
    
    def change_thinking_level(e):
        """Change thinking level"""
        nonlocal thinking_level
        thinking_level = thinking_dropdown.value
        status_text.value = f"Thinking mode: {thinking_level}"
        page.update()
    
    def toggle_theme(e):
        """Toggle between light and dark mode"""
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = ft.Colors.GREY_100
            theme_btn.icon = ft.Icons.DARK_MODE
            # Update sidebar colors
            sidebar.bgcolor = ft.Colors.WHITE
            chat_container.bgcolor = ft.Colors.GREY_50
        else:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = ft.Colors.BLACK
            theme_btn.icon = ft.Icons.LIGHT_MODE
            # Restore dark colors
            sidebar.bgcolor = ft.Colors.GREY_900
            chat_container.bgcolor = None
        page.update()
    
    def update_context_meter():
        try:
            messages = [
                types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)]),
                types.Content(role="model", parts=[types.Part(text="Understood. I will provide expert analysis with specific references to page numbers, timestamps (in MM:SS format with seconds), and data locations as appropriate.")])
            ]
            messages.extend(conversation_history)
            
            # Add datastream (files) to token count - they're sent with every message
            if uploaded_files:
                datastream_parts = []
                for f in uploaded_files:
                    datastream_parts.append(types.Part.from_uri(file_uri=f["uri"], mime_type=f["mime"]))
                messages.append(types.Content(role="user", parts=datastream_parts))
            
            token_response = client.models.count_tokens(model=MODEL_ID, contents=messages)
            total_tokens = token_response.total_tokens
            percentage = min((total_tokens / MAX_CONTEXT_TOKENS) * 100, 100)
            
            context_meter.value = percentage / 100
            context_label.value = f"{total_tokens:,} / {MAX_CONTEXT_TOKENS:,} tokens ({percentage:.1f}%)"
            
            if percentage < 50:
                context_meter.color = ft.Colors.GREEN
            elif percentage < 80:
                context_meter.color = ft.Colors.YELLOW
            else:
                context_meter.color = ft.Colors.RED
            
            page.update()
        except Exception as err:
            print(f"Token counting error: {err}")
            context_label.value = f"{len(uploaded_files)} files loaded"
            page.update()
    
    def get_mime_type(filename):
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type
        
        ext = os.path.splitext(filename)[1].lower()
        mime_map = {
            # Documents
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.rtf': 'application/rtf',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.csv': 'text/csv',
            # Images
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.heic': 'image/heic',
            '.heif': 'image/heif',
            '.svg': 'image/svg+xml',
            # Video
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mpeg': 'video/mpeg',
            '.mpg': 'video/mpeg',
            '.flv': 'video/x-flv',
            '.webm': 'video/webm',
            '.wmv': 'video/wmv',
            '.3gp': 'video/3gpp',
            # Audio
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.aiff': 'audio/aiff',
            '.aif': 'audio/aiff',
            '.aac': 'audio/aac',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            # OpenDocument formats
            '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
            '.odp': 'application/vnd.oasis.opendocument.presentation',
            '.odt': 'application/vnd.oasis.opendocument.text',
            # Config/data formats
            '.yaml': 'text/plain',
            '.yml': 'text/plain',
            '.toml': 'text/plain',
            '.ini': 'text/plain',
            '.cfg': 'text/plain',
            '.conf': 'text/plain',
            '.config': 'text/plain',
            '.log': 'text/plain',
            # Shell scripts
            '.sh': 'text/plain',
            '.bash': 'text/plain',
            '.zsh': 'text/plain',
            '.fish': 'text/plain',
            '.bat': 'text/plain',
            '.cmd': 'text/plain',
            '.ps1': 'text/plain',
            # Web languages
            '.py': 'text/plain',
            '.js': 'text/plain',
            '.ts': 'text/plain',
            '.jsx': 'text/plain',
            '.tsx': 'text/plain',
            '.css': 'text/plain',
            '.scss': 'text/plain',
            '.sass': 'text/plain',
            '.less': 'text/plain',
            '.php': 'text/plain',
            '.rb': 'text/plain',
            '.pl': 'text/plain',
            '.lua': 'text/plain',
            # Compiled languages
            '.java': 'text/plain',
            '.c': 'text/plain',
            '.cc': 'text/plain',
            '.cpp': 'text/plain',
            '.cxx': 'text/plain',
            '.h': 'text/plain',
            '.hpp': 'text/plain',
            '.hxx': 'text/plain',
            '.cs': 'text/plain',
            '.go': 'text/plain',
            '.rs': 'text/plain',
            '.swift': 'text/plain',
            '.kt': 'text/plain',
            '.kts': 'text/plain',
            '.scala': 'text/plain',
            '.m': 'text/plain',
            '.mm': 'text/plain',
            # Legacy/niche languages
            '.bas': 'text/plain',
            '.vb': 'text/plain',
            '.vbs': 'text/plain',
            '.asm': 'text/plain',
            '.s': 'text/plain',
            '.f': 'text/plain',
            '.f90': 'text/plain',
            '.pas': 'text/plain',
            '.ada': 'text/plain',
            '.cob': 'text/plain',
            '.for': 'text/plain',
            # Functional languages
            '.hs': 'text/plain',
            '.ml': 'text/plain',
            '.fs': 'text/plain',
            '.clj': 'text/plain',
            '.lisp': 'text/plain',
            '.scm': 'text/plain',
            '.erl': 'text/plain',
            '.ex': 'text/plain',
            '.exs': 'text/plain',
            # Data science
            '.r': 'text/plain',
            '.jl': 'text/plain',
            '.ipynb': 'text/plain',
            '.sql': 'text/plain',
            # Markup/templates
            '.vue': 'text/plain',
            '.svelte': 'text/plain',
            '.ejs': 'text/plain',
            '.hbs': 'text/plain',
            '.jade': 'text/plain',
            '.pug': 'text/plain',
            # Build/project files
            '.gradle': 'text/plain',
            '.make': 'text/plain',
            '.cmake': 'text/plain',
            '.dockerfile': 'text/plain',
            '.dockerignore': 'text/plain',
            '.gitignore': 'text/plain',
            '.gitattributes': 'text/plain',
            '.editorconfig': 'text/plain',
            '.env': 'text/plain',
            # Documentation
            '.rst': 'text/plain',
            '.asciidoc': 'text/plain',
            '.adoc': 'text/plain',
            '.textile': 'text/plain',
        }
        return mime_map.get(ext, 'application/octet-stream')
    
    def remove_file(file_index):
        """Remove file from shelf and update UI"""
        if 0 <= file_index < len(uploaded_files):
            removed = uploaded_files.pop(file_index)
            print(f"Removed: {removed['name']}")
            rebuild_shelf()
            update_shelf_cache()  # Refresh cache
            update_context_meter()
            page.update()
    
    def get_file_category(name, mime):
        """Categorize file for folders"""
        if name.startswith('🔗'):
            return "links"
        elif name.startswith('🎤'):
            return "audio"
        elif "image" in mime:
            return "images"
        elif "video" in mime:
            return "videos"
        elif "audio" in mime:
            return "audio"
        elif "pdf" in mime or name.endswith('.xlsx') or name.endswith('.pptx') or 'text' in mime:
            return "documents"
        else:
            return "other"
    
    def toggle_folder(category):
        """Toggle folder collapse state"""
        folders_collapsed[category] = not folders_collapsed[category]
        rebuild_shelf()
        page.update()
    
    def rebuild_shelf():
        """Rebuild shelf with folders"""
        shelf_list.controls.clear()
        
        # Group files by category
        categorized = {
            "documents": [],
            "images": [],
            "videos": [],
            "audio": [],
            "links": [],
            "other": []
        }
        
        for idx, f in enumerate(uploaded_files):
            category = get_file_category(f['name'], f['mime'])
            categorized[category].append((idx, f))
        
        # Display folders
        folder_names = {
            "documents": ("Documents", ft.Icons.DESCRIPTION),
            "images": ("Images", ft.Icons.IMAGE),
            "videos": ("Videos", ft.Icons.VIDEO_LIBRARY),
            "audio": ("Audio", ft.Icons.AUDIOTRACK),
            "links": ("Links", ft.Icons.LINK),
            "other": ("Other", ft.Icons.FOLDER)
        }
        
        for category, (label, icon) in folder_names.items():
            files_in_cat = categorized[category]
            if not files_in_cat:
                continue
            
            # Folder header
            collapse_icon = ft.Icons.EXPAND_MORE if not folders_collapsed[category] else ft.Icons.CHEVRON_RIGHT
            shelf_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icon, size=16, color=ft.Colors.GREY_400),
                        ft.Text(f"{label} ({len(files_in_cat)})", size=12, weight="bold", color=ft.Colors.GREY_400),
                        ft.IconButton(
                            icon=collapse_icon,
                            icon_size=16,
                            on_click=lambda e, cat=category: toggle_folder(cat)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=5,
                    margin=ft.margin.only(top=5, bottom=2)
                )
            )
            
            # Files in folder (if not collapsed)
            if not folders_collapsed[category]:
                for idx, f in files_in_cat:
                    add_shelf_item(f['name'], f['mime'], f['tokens'], idx)
    
    def process_file_upload(file_path, file_name, override_mime=None):
        """Common file processing logic"""
        file_to_upload = file_path
        original_name = file_name
        
        print(f"DEBUG process_file_upload: file_path={file_path}, file_name={file_name}, override_mime={override_mime}")
        
        # Convert unsupported formats
        if file_name.lower().endswith('.docx'):
            status_text.value = f"Converting {file_name} to PDF..."
            page.update()
            file_to_upload = convert_docx_to_pdf(file_path)
            mime_type = 'application/pdf'
        elif file_name.lower().endswith('.xlsx'):
            status_text.value = f"Converting {file_name}..."
            page.update()
            file_to_upload = convert_xlsx_to_csv(file_path)
            mime_type = 'text/csv'
        elif file_name.lower().endswith('.ods'):
            status_text.value = f"Converting {file_name}..."
            page.update()
            file_to_upload = convert_ods_to_csv(file_path)
            mime_type = 'text/csv'
        elif file_name.lower().endswith('.odp'):
            status_text.value = f"Converting {file_name}..."
            page.update()
            file_to_upload = convert_odp_to_text(file_path)
            mime_type = 'text/plain'
        elif file_name.lower().endswith('.odt'):
            status_text.value = f"Converting {file_name}..."
            page.update()
            file_to_upload = convert_odt_to_text(file_path)
            mime_type = 'text/plain'
        else:
            mime_type = override_mime if override_mime else get_mime_type(file_name)
        
        print(f"DEBUG: Final mime_type before upload: {mime_type}")
        
        with open(file_to_upload, 'rb') as file_handle:
            file_ref = client.files.upload(file=file_handle, config={'mime_type': mime_type})
        
        if file_to_upload != file_path:
            os.unlink(file_to_upload)
        
        while file_ref.state.name == "PROCESSING":
            status_text.value = f"Processing {file_name}..."
            page.update()
            time.sleep(1)
            file_ref = client.files.get(name=file_ref.name)
        
        if file_ref.state.name == "FAILED":
            raise Exception(f"Failed to process {file_name}")

        status_text.value = f"Counting tokens..."
        page.update()
        
        file_token_count = client.models.count_tokens(
            model=MODEL_ID,
            contents=[types.Content(role="user", parts=[
                types.Part.from_uri(file_uri=file_ref.uri, mime_type=file_ref.mime_type)
            ])]
        )

        uploaded_files.append({
            "name": original_name,
            "uri": file_ref.uri,
            "mime": file_ref.mime_type,
            "tokens": file_token_count.total_tokens,
            "thumbnail": generate_thumbnail(file_path, mime_type)
        })
        
        rebuild_shelf()
        update_shelf_cache()  # Refresh cache after adding file
    
    def upload_file(e):
        # Handle both FilePickerResultEvent and FilePickerUploadEvent for version compatibility
        if not e.files:
            return
        
        if len(uploaded_files) + len(e.files) > MAX_FILES:
            status_text.value = f"Error: Maximum {MAX_FILES} files"
            status_text.color = ft.Colors.RED
            page.update()
            time.sleep(2)
            status_text.color = ft.Colors.GREY_500
            status_text.value = "Ready."
            page.update()
            return
        
        loading_ring.visible = True
        upload_btn.disabled = True
        status_text.value = "Processing..."
        page.update()

        try:
            for f in e.files:
                process_file_upload(f.path, f.name)
            
            status_text.value = "Ready."
            update_context_meter()
            
        except Exception as err:
            print(f"Upload error: {err}")
            status_text.value = f"Error: {err}"
        finally:
            loading_ring.visible = False
            upload_btn.disabled = False
            page.update()
    
    def add_url(e):
        url = url_input.value.strip()
        if not url:
            return
        
        url_input.value = ""
        
        if len(uploaded_files) >= MAX_FILES:
            status_text.value = f"Error: Maximum {MAX_FILES} files"
            status_text.color = ft.Colors.RED
            page.update()
            time.sleep(2)
            status_text.color = ft.Colors.GREY_500
            return
        
        loading_ring.visible = True
        url_btn.disabled = True
        page.update()
        
        try:
            # Check if it's a direct file URL (PDF, image, video, etc.)
            if is_direct_file_url(url):
                status_text.value = f"Downloading file from {url}..."
                page.update()
                
                # Download file
                temp_file_path = download_file_from_url(url)
                print(f"DEBUG: Downloaded to: {temp_file_path}")
                
                # Get filename from URL
                from urllib.parse import urlparse
                url_path = urlparse(url).path
                filename = url_path.split('/')[-1] if url_path else 'downloaded_file'
                print(f"DEBUG: Filename from URL: {filename}")
                
                # Get MIME type from actual file extension (after download)
                mime_type = get_mime_type(temp_file_path)
                print(f"DEBUG: MIME type detected: {mime_type}")
                
                # Process like a normal file upload but with explicit MIME
                process_file_upload(temp_file_path, filename, mime_type)
                os.unlink(temp_file_path)
                
                status_text.value = "Ready."
                update_context_meter()
            else:
                # Scrape as HTML page
                status_text.value = f"Scraping {url}..."
                page.update()
                
                temp_file = scrape_url(url)
                
                with open(temp_file, 'rb') as file_handle:
                    file_ref = client.files.upload(file=file_handle, config={'mime_type': 'text/plain'})
                
                os.unlink(temp_file)
                
                while file_ref.state.name == "PROCESSING":
                    time.sleep(1)
                    file_ref = client.files.get(name=file_ref.name)
                
                if file_ref.state.name == "FAILED":
                    raise Exception("Failed to process URL content")
                
                file_token_count = client.models.count_tokens(
                    model=MODEL_ID,
                    contents=[types.Content(role="user", parts=[
                        types.Part.from_uri(file_uri=file_ref.uri, mime_type=file_ref.mime_type)
                    ])]
                )
                
                uploaded_files.append({
                    "name": f"🔗 {url[:30]}...",
                    "uri": file_ref.uri,
                    "mime": file_ref.mime_type,
                    "tokens": file_token_count.total_tokens
                })
                
                rebuild_shelf()
                status_text.value = "Ready."
                update_context_meter()
            
        except Exception as err:
            print(f"URL error: {err}")
            status_text.value = f"Error: {err}"
        finally:
            loading_ring.visible = False
            url_btn.disabled = False
            page.update()

    def send_chat(e):
        nonlocal active_preset, thinking_level
        
        if not chat_input.value:
            return
        
        user_query = chat_input.value
        chat_input.value = ""
        
        # Check for slash commands
        preset_prompt = None
        preset_thinking = None
        
        if user_query.startswith('/'):
            # Handle /help command
            if user_query.split()[0] in ['/help', '/commands']:
                help_text = """**Available Commands:**

**`/report`** - Generate executive summary and cohesive report
**`/synthesize`** - Identify patterns and generate novel insights  
**`/error-check`** - Find contradictions and inconsistencies

Example: `/report` or `/synthesize focus on financial data`

**Charting:**
Just ask! Say "plot sales over time" or "chart customer acquisition vs revenue"
Gemini will automatically generate charts when you ask for visualizations.

Other features:
- **Thinking dropdown** - Adjust reasoning depth (minimal/low/medium/high)"""
                
                chat_list.controls.append(
                    ft.Container(
                        content=ft.Markdown(help_text),
                        bgcolor=ft.Colors.BLUE_GREY_900 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_100,
                        padding=15,
                        border_radius=10,
                        margin=ft.margin.only(bottom=10)
                    )
                )
                page.update()
                return
            
            preset_prompt, preset_thinking = get_preset(user_query.split()[0])
            
            if preset_prompt:
                # Slash command found - set active preset
                active_preset = user_query.split()[0]
                
                # Override thinking level for this query
                original_thinking = thinking_level
                thinking_level = preset_thinking
                
                # Show preset indicator
                preset_label = get_preset_indicator(active_preset)
                if preset_label:
                    chat_list.controls.append(
                        ft.Container(
                            content=ft.Text(preset_label, size=12, weight="bold", color=ft.Colors.BLUE_400),
                            padding=5,
                            margin=ft.margin.only(bottom=5)
                        )
                    )
                
                # Extract actual query after command (if any)
                parts = user_query.split(maxsplit=1)
                if len(parts) > 1:
                    user_query = parts[1]
                else:
                    user_query = "Analyze the uploaded files according to the specified mode."
            else:
                # Unknown command
                chat_list.controls.append(
                    ft.Container(
                        content=ft.Text(f"Unknown command: {user_query.split()[0]}", 
                                       color=ft.Colors.RED_400, size=14),
                        padding=10,
                        margin=ft.margin.only(bottom=10)
                    )
                )
                page.update()
                return
        
        # User bubble colors based on theme
        user_bg = ft.Colors.BLUE_GREY_900 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_100
        user_text = ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLACK
        
        chat_list.controls.append(
            ft.Container(
                content=ft.Text(user_query, color=user_text, size=16),
                bgcolor=user_bg,
                padding=15,
                border_radius=ft.border_radius.only(top_left=15, top_right=15, bottom_left=15),
                alignment=ft.alignment.center_right,
                margin=ft.margin.only(left=50, bottom=10)
            )
        )
        
        # Add thinking indicator
        ai_bg = ft.Colors.GREY_900 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200
        thinking_container = ft.Container(
            content=ft.Row([
                ft.ProgressRing(width=20, height=20, stroke_width=2),
                ft.Text("Thinking...", size=14, italic=True, color=ft.Colors.GREY_400)
            ], spacing=10),
            bgcolor=ai_bg,
            padding=15,
            border_radius=ft.border_radius.only(top_left=15, top_right=15, bottom_right=15),
            alignment=ft.alignment.center_left,
            margin=ft.margin.only(right=50, bottom=10)
        )
        chat_list.controls.append(thinking_container)
        page.update()

        try:
            # Build messages
            messages = []
            
            # System prompt
            messages.append(types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)]))
            messages.append(types.Content(role="model", parts=[types.Part(text="Understood. I will provide expert analysis with specific references to page numbers, timestamps (in MM:SS format with seconds), and data locations as appropriate.")]))
            
            # Conversational context (text only)
            messages.extend(conversation_history)
            
            # Add current query
            messages.append(types.Content(role="user", parts=[types.Part(text=user_query)]))

            # Generate response - use cache if available
            if current_cache_name:
                # Use cached files
                from google.genai.types import GenerateContentConfig, ThinkingConfig, Tool
                config = GenerateContentConfig(
                    cached_content=current_cache_name,
                    thinking_config=ThinkingConfig(thinking_level=thinking_level),
                    tools=[Tool(function_declarations=[get_chart_tool_declaration()])]
                )
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=messages,
                    config=config
                )
                print(f"Used cache: {current_cache_name}")
            else:
                # No cache - send files directly (fallback)
                if uploaded_files:
                    # Add files to the current query
                    file_parts = [
                        types.Part.from_uri(file_uri=f["uri"], mime_type=f["mime"])
                        for f in uploaded_files
                    ]
                    # Replace last message with files + query
                    messages[-1] = types.Content(role="user", parts=file_parts + [types.Part(text=user_query)])
                
                from google.genai.types import GenerateContentConfig, ThinkingConfig, Tool
                config = GenerateContentConfig(
                    thinking_config=ThinkingConfig(thinking_level=thinking_level),
                    tools=[Tool(function_declarations=[get_chart_tool_declaration()])]
                )
                response = client.models.generate_content(
                    model=MODEL_ID, 
                    contents=messages,
                    config=config
                )
                print("No cache - sent files directly")
            
            # Remove thinking indicator
            chat_list.controls.remove(thinking_container)
            
            # Check if response contains function call
            function_call = None
            text_response = ""
            
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                elif hasattr(part, 'text') and part.text:
                    text_response += part.text
            
            # Handle chart generation if tool was called
            if function_call and function_call.name == "generate_chart":
                try:
                    # Extract chart parameters
                    chart_data = dict(function_call.args)
                    
                    # Generate chart
                    status_text.value = "Generating chart..."
                    page.update()
                    
                    chart_path = generate_chart(chart_data)
                    
                    # Show chart in dialog
                    def close_dialog(e):
                        chart_dialog.open = False
                        page.update()
                    
                    def export_chart(e):
                        import shutil
                        export_path = f"./gemdesk_chart_{int(time.time())}.png"
                        shutil.copy(chart_path, export_path)
                        status_text.value = f"Chart exported to {export_path}"
                        page.update()
                    
                    chart_dialog = ft.AlertDialog(
                        title=ft.Text(chart_data.get('title', 'Generated Chart')),
                        content=ft.Image(src=chart_path, width=800, height=600, fit=ft.ImageFit.CONTAIN),
                        actions=[
                            ft.TextButton("Export PNG", on_click=export_chart),
                            ft.TextButton("Close", on_click=close_dialog)
                        ]
                    )
                    
                    page.dialog = chart_dialog
                    chart_dialog.open = True
                    
                    # Add a message about chart generation
                    text_response = f"📊 **Chart Generated: {chart_data.get('title', 'Chart')}**\n\n" + text_response
                    
                    status_text.value = "Ready."
                    
                except Exception as chart_err:
                    text_response = f"❌ Chart generation failed: {chart_err}\n\n" + text_response
                    print(f"Chart generation error: {chart_err}")
            
            # Store conversation history
            conversation_history.append(types.Content(role="user", parts=[types.Part(text=user_query)]))
            conversation_history.append(types.Content(role="model", parts=[types.Part(text=text_response)]))
            
            # Display response
            chat_list.controls.append(
                ft.Container(
                    content=ft.Markdown(
                        text_response, 
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        code_theme="atom-one-dark"
                    ),
                    bgcolor=ai_bg,
                    padding=15,
                    border_radius=ft.border_radius.only(top_left=15, top_right=15, bottom_right=15),
                    alignment=ft.alignment.center_left,
                    margin=ft.margin.only(right=50, bottom=10)
                )
            )
            
            # Reset preset after use
            if preset_prompt:
                active_preset = None
                thinking_level = original_thinking  # Restore original thinking level
            
            update_context_meter()
        except Exception as err:
            # Remove thinking indicator on error
            if thinking_container in chat_list.controls:
                chat_list.controls.remove(thinking_container)
            print(f"Chat error: {err}")
            chat_list.controls.append(ft.Text(f"API Error: {err}", color=ft.Colors.RED))
        
        page.update()

    file_picker = ft.FilePicker()
    file_picker.on_result = upload_file
    page.overlay.append(file_picker)
    
    def open_file_picker(e):
        file_picker.pick_files(allow_multiple=True)
    
    shelf_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    
    def add_shelf_item(name, mime, tokens, index):
        file_data = uploaded_files[index]
        thumbnail = file_data.get('thumbnail')
        
        icon = ft.icons.INSERT_DRIVE_FILE
        color = ft.Colors.WHITE
        
        if "image" in mime: 
            icon, color = ft.icons.IMAGE, ft.Colors.PINK_400
        elif "video" in mime: 
            icon, color = ft.icons.VIDEO_FILE, ft.Colors.CYAN_400
        elif "pdf" in mime: 
            icon, color = ft.icons.PICTURE_AS_PDF, ft.Colors.RED_400
        elif name.lower().endswith('.xlsx') or 'spreadsheet' in mime or 'csv' in mime:
            icon, color = ft.icons.TABLE_CHART, ft.Colors.GREEN_400
        elif name.lower().endswith('.pptx'):
            icon, color = ft.icons.SLIDESHOW, ft.Colors.ORANGE_400
        elif name.startswith('🔗'):
            icon, color = ft.icons.LINK, ft.Colors.BLUE_400
        elif name.startswith('🎤'):
            icon, color = ft.icons.MIC, ft.Colors.PURPLE_400
        
        # Create thumbnail or icon
        if thumbnail:
            preview = ft.Image(
                src_base64=thumbnail,
                width=60,
                height=60,
                fit=ft.ImageFit.COVER,
                border_radius=5
            )
        else:
            preview = ft.Icon(icon, color=color, size=24)
        
        shelf_list.controls.append(
            ft.Container(
                content=ft.Row([
                    preview,
                    ft.Column([
                        ft.Text(name, size=12, weight="bold", overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                        ft.Text(f"{tokens:,} tokens", size=9, color=ft.Colors.GREY_500)
                    ], spacing=2, expand=True),
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_size=16,
                        icon_color=ft.Colors.RED_400,
                        on_click=lambda e, idx=index: remove_file(idx),
                        tooltip="Remove"
                    )
                ], spacing=10),
                bgcolor=ft.Colors.WHITE10,
                padding=10,
                border_radius=8,
                margin=ft.margin.only(bottom=5)
            )
        )

    # Thinking level dropdown
    thinking_dropdown = ft.Dropdown(
        width=120,
        height=40,
        text_size=12,
        value="high",
        options=[
            ft.dropdown.Option("minimal", "Minimal"),
            ft.dropdown.Option("low", "Low"),
            ft.dropdown.Option("medium", "Medium"),
            ft.dropdown.Option("high", "High")
        ],
        on_change=change_thinking_level,
        label="Thinking",
        tooltip="Thinking depth: minimal (fast) to high (deep reasoning)"
    )
    
    # Theme toggle and export buttons
    theme_btn = ft.IconButton(
        icon=ft.icons.LIGHT_MODE,
        icon_size=20,
        on_click=toggle_theme,
        tooltip="Toggle theme"
    )
    
    export_btn = ft.IconButton(
        icon=ft.icons.DOWNLOAD,
        icon_size=20,
        on_click=export_chat,
        tooltip="Export chat"
    )

    upload_btn = ft.ElevatedButton(
        "Add Files", 
        icon=ft.icons.ADD, 
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=open_file_picker,
        height=50
    )
    
    url_input = ft.TextField(
        hint_text="Paste URL...",
        border_color=ft.Colors.GREY_400,
        bgcolor=ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_800,
        color=ft.Colors.BLACK if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.WHITE,
        border_radius=10,
        content_padding=10,
        text_size=12,
        on_submit=add_url
    )
    
    url_btn = ft.IconButton(
        icon=ft.icons.ADD_LINK,
        icon_size=20,
        on_click=add_url,
        tooltip="Add URL"
    )
    

    status_text = ft.Text("Ready", size=10, color=ft.Colors.GREY_500)
    loading_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
    
    context_meter = ft.ProgressBar(
        width=260,
        height=8,
        value=0,
        color=ft.Colors.GREEN,
        bgcolor=ft.Colors.GREY_800,
        border_radius=4
    )
    context_label = ft.Text("0 / 1,000,000 tokens (0.0%)", size=9, color=ft.Colors.GREY_400)

    chat_list = ft.Column(expand=True, scroll=ft.ScrollMode.ALWAYS, auto_scroll=True)
    chat_input = ft.TextField(
        hint_text=f"Ask {MODEL_ID}...",
        border_color=ft.Colors.GREY_400 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.TRANSPARENT,
        bgcolor=ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_900,
        color=ft.Colors.BLACK if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.WHITE,
        border_radius=30,
        content_padding=20,
        expand=True,
        on_submit=send_chat
    )

    # Named containers for theme switching
    sidebar = ft.Container(
        width=300,
        bgcolor=ft.Colors.GREY_900,
        border_radius=15,
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Text("SHELF", size=20, weight="bold", color=ft.Colors.WHITE),
                ft.Row([export_btn, theme_btn], spacing=0)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            thinking_dropdown,
            ft.Text(f"Max {MAX_FILES} files", size=10, color=ft.Colors.GREY_500),
            ft.Divider(color=ft.Colors.GREY_800),
            upload_btn,
            ft.Row([url_input, url_btn], spacing=5),
            ft.Row([loading_ring, status_text]),
            ft.Divider(color=ft.Colors.GREY_800),
            ft.Column([
                ft.Text("CONTEXT", size=12, weight="bold", color=ft.Colors.GREY_400),
                context_meter,
                context_label,
            ]),
            ft.Divider(color=ft.Colors.GREY_800),
            shelf_list
        ])
    )
    
    chat_container = ft.Container(
        expand=True,
        padding=10,
        content=ft.Column([
            chat_list,
            ft.Row([
                chat_input,
                ft.IconButton(icon=ft.icons.SEND_ROUNDED, icon_size=40, on_click=send_chat)
            ])
        ])
    )
    
    page.add(
        ft.Row(
            controls=[sidebar, chat_container],
            expand=True
        )
    )

ft.app(target=main)
