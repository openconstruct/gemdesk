import flet as ft
import os
import time
import threading
from google import genai
from google.genai import types
from dotenv import load_dotenv
import warnings

# Suppress Flet warnings
warnings.filterwarnings('ignore')
os.environ['FLET_FORCE_WEB_VIEW'] = 'false'

from conversions import (
    convert_xlsx_to_csv, convert_ods_to_csv, convert_docx_to_pdf,
    convert_pptx_to_pdf, convert_odp_to_text, convert_odt_to_text,
    scrape_url, download_file_from_url, is_direct_file_url, generate_thumbnail
)
from charting import generate_chart, get_chart_tool_declaration
from presets import get_preset, get_preset_indicator
from file_ops import get_mime_type, process_file_upload, handle_file_upload, handle_url_add
from ui_components import build_shelf_ui, get_file_category
from validation import (
    validate_file_size, validate_file_extension, validate_url, 
    validate_message, validate_api_key, sanitize_filename,
    validate_thinking_level, ValidationError
)

# Flet version compatibility
if not hasattr(ft, 'Colors'):
    ft.Colors = ft.colors
if not hasattr(ft, 'Icons'):
    ft.Icons = ft.icons

load_dotenv()

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise Exception("GEMINI_API_KEY not found in .env")

try:
    validate_api_key(API_KEY)
except ValidationError as e:
    raise Exception(f"Invalid API key: {e}")

MODEL_ID = "gemini-2.0-flash-exp"  # Default model
MAX_CONTEXT_TOKENS = 1000000
MAX_FILES = 50

# Query available models from API
try:
    available_models_list = client.models.list()
    AVAILABLE_MODELS = {}
    for model in available_models_list:
        # Only include generative models that support generateContent
        if 'generateContent' in model.supported_generation_methods:
            # Extract context window from model info
            context_window = getattr(model, 'input_token_limit', 1000000)
            AVAILABLE_MODELS[model.name] = {
                "name": model.display_name or model.name,
                "context": context_window
            }
    
    # If no models found or default not available, use fallback
    if not AVAILABLE_MODELS:
        AVAILABLE_MODELS = {
            "gemini-2.0-flash-exp": {"name": "Gemini 2.0 Flash", "context": 1000000},
            "gemini-3-flash-preview": {"name": "Gemini 3 Flash Preview", "context": 1000000},
            "gemini-3-pro-preview": {"name": "Gemini 3 Pro Preview", "context": 2000000},
        }
    
    # Use first available model as default if specified default doesn't exist
    if MODEL_ID not in AVAILABLE_MODELS:
        MODEL_ID = list(AVAILABLE_MODELS.keys())[0]
        
except Exception as e:
    print(f"Could not fetch models from API: {e}")
    # Fallback to hardcoded models
    AVAILABLE_MODELS = {
        "gemini-2.0-flash-exp": {"name": "Gemini 2.0 Flash", "context": 1000000},
        "gemini-3-flash-preview": {"name": "Gemini 3 Flash Preview", "context": 1000000},
        "gemini-3-pro-preview": {"name": "Gemini 3 Pro Preview", "context": 2000000},
    }

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


class GemDeskState:
    """Centralized state management"""
    def __init__(self):
        self.uploaded_files = []
        self.conversation_history = []
        self.current_cache_name = None
        self.thinking_level = "high"
        self.active_preset = None
        self.google_search_enabled = False
        self.folders_collapsed = {
            "documents": False,
            "images": False,
            "videos": False,
            "audio": False,
            "links": False,
            "other": False
        }
    
    def reset_cache(self):
        """Clear cache reference"""
        self.current_cache_name = None


def main(page: ft.Page):
    page.title = "GemDesk"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.bgcolor = ft.Colors.BLACK

    state = GemDeskState()
    
    def export_chat(e):
        """Export chat history as PDF"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch
            from datetime import datetime
            
            # Create save file picker
            def save_dialog_result(e: ft.FilePickerResultEvent):
                if e.path:
                    try:
                        doc = SimpleDocTemplate(e.path, pagesize=letter)
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
                        if state.uploaded_files:
                            files_title = Paragraph("<b>Files in Context:</b>", styles['Heading2'])
                            story.append(files_title)
                            for f in state.uploaded_files:
                                file_line = Paragraph(f"• {f['name']} ({f['tokens']:,} tokens)", styles['Normal'])
                                story.append(file_line)
                            story.append(Spacer(1, 0.3*inch))
                        
                        # Conversation
                        conv_title = Paragraph("<b>Conversation:</b>", styles['Heading2'])
                        story.append(conv_title)
                        story.append(Spacer(1, 0.2*inch))
                        
                        for msg in state.conversation_history:
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
                        status_text.value = f"Saved to {e.path}"
                        page.update()
                    except Exception as err:
                        status_text.value = f"Export error: {str(err)[:50]}"
                        page.update()
            
            save_picker = ft.FilePicker(on_result=save_dialog_result)
            page.overlay.append(save_picker)
            page.update()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_picker.save_file(
                file_name=f"gemdesk_{timestamp}.pdf",
                allowed_extensions=["pdf"],
                dialog_title="Save Chat Export"
            )
            
        except ImportError:
            status_text.value = "Error: Install reportlab (pip install reportlab)"
            page.update()
        except Exception as err:
            status_text.value = f"Export error: {str(err)[:50]}"
            page.update()
    
    def update_shelf_cache():
        """Only update cache when shelf changes - gracefully handles free tier"""
        if state.current_cache_name:
            try:
                client.caches.delete(name=state.current_cache_name)
            except Exception:
                pass
            state.reset_cache()
        
        if not state.uploaded_files:
            return
        
        # Try to create cache (will fail gracefully on free tier)
        try:
            file_parts = [types.Part.from_uri(file_uri=f["uri"], mime_type=f["mime"]) 
                         for f in state.uploaded_files]
            
            cache = client.caches.create(
                model=MODEL_ID,
                config={
                    "contents": [types.Content(role="user", parts=file_parts)],
                    "ttl": "3600s"
                }
            )
            state.current_cache_name = cache.name
            status_text.value = f"Cached {len(state.uploaded_files)} files"
            page.update()
        except Exception as e:
            # Check if it's a free tier quota error
            error_str = str(e)
            if "RESOURCE_EXHAUSTED" in error_str or "FreeTier" in error_str:
                status_text.value = f"{len(state.uploaded_files)} files (no cache on free tier)"
                state.current_cache_name = None  # Ensure we don't try to use cache
            else:
                status_text.value = f"Cache unavailable: {type(e).__name__}"
                state.current_cache_name = None
            page.update()
    
    def change_thinking_level(e):
        try:
            validated_level = validate_thinking_level(thinking_dropdown.value)
            state.thinking_level = validated_level
            status_text.value = f"Thinking: {state.thinking_level}"
        except ValidationError as err:
            status_text.value = f"Invalid thinking level: {err}"
        page.update()
    
    def change_model(e):
        global MODEL_ID, MAX_CONTEXT_TOKENS
        MODEL_ID = model_dropdown.value
        MAX_CONTEXT_TOKENS = AVAILABLE_MODELS[MODEL_ID]["context"]
        chat_input.hint_text = f"Ask {AVAILABLE_MODELS[MODEL_ID]['name']}..."
        status_text.value = f"Model: {AVAILABLE_MODELS[MODEL_ID]['name']}"
        page.update()
    
    def toggle_google_search(e):
        state.google_search_enabled = search_toggle.value
        status_text.value = f"Search: {'on' if state.google_search_enabled else 'off'}"
        page.update()
    
    def update_context_meter():
        try:
            messages = [
                types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)]),
                types.Content(role="model", parts=[types.Part(text="Understood.")])
            ]
            messages.extend(state.conversation_history)
            
            if state.uploaded_files:
                datastream_parts = [types.Part.from_uri(file_uri=f["uri"], mime_type=f["mime"])
                                   for f in state.uploaded_files]
                messages.append(types.Content(role="user", parts=datastream_parts))
            
            token_response = client.models.count_tokens(model=MODEL_ID, contents=messages)
            total_tokens = token_response.total_tokens
            percentage = min((total_tokens / MAX_CONTEXT_TOKENS) * 100, 100)
            
            context_meter.value = percentage / 100
            context_label.value = f"{total_tokens:,} / {MAX_CONTEXT_TOKENS:,} tokens ({percentage:.1f}%)"
            
            context_meter.color = (ft.Colors.GREEN if percentage < 50 else
                                  ft.Colors.YELLOW if percentage < 80 else
                                  ft.Colors.RED)
            page.update()
        except Exception:
            context_label.value = f"{len(state.uploaded_files)} files"
            page.update()
    
    def remove_file(file_index):
        """Remove file and refresh cache"""
        if 0 <= file_index < len(state.uploaded_files):
            state.uploaded_files.pop(file_index)
            rebuild_shelf()
            update_shelf_cache()
            update_context_meter()
    
    def toggle_folder(category):
        state.folders_collapsed[category] = not state.folders_collapsed[category]
        rebuild_shelf()
        page.update()
    
    def rebuild_shelf():
        shelf_list.controls = build_shelf_ui(state.uploaded_files, state.folders_collapsed,
                                             remove_file, toggle_folder, page)
        page.update()
    
    def upload_file(e):
        handle_file_upload(e, state.uploaded_files, MAX_FILES, client, MODEL_ID,
                          status_text, loading_ring, upload_btn, page,
                          rebuild_shelf, update_shelf_cache, update_context_meter)
    
    def add_url(e):
        handle_url_add(url_input, state.uploaded_files, MAX_FILES, client, MODEL_ID,
                      status_text, loading_ring, url_btn, page,
                      rebuild_shelf, update_shelf_cache, update_context_meter)
    
    def send_chat(e):
        print(f"send_chat called, input value: '{chat_input.value}'")
        if not chat_input.value:
            print("Empty input, returning")
            return
        
        # Validate message
        try:
            user_query = validate_message(chat_input.value)
        except ValidationError as err:
            chat_list.controls.append(
                ft.Container(
                    content=ft.Text(f"Invalid input: {err}", color=ft.Colors.RED_400),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                )
            )
            page.update()
            return
        
        chat_input.value = ""
        print(f"Processing query: '{user_query}'")
        
        # Handle slash commands
        preset_prompt = None
        original_thinking = None
        
        if user_query.startswith('/'):
            if user_query.split()[0] in ['/help', '/commands']:
                help_text = """**Available Commands:**

**`/report`** - Generate executive summary
**`/synthesize`** - Identify patterns and insights  
**`/error-check`** - Find contradictions

**Charting:** Just ask! "plot sales over time"
**Settings:** Thinking dropdown, Google Search toggle"""
                
                chat_list.controls.append(
                    ft.Container(
                        content=ft.Markdown(help_text),
                        bgcolor=ft.Colors.BLUE_GREY_900,
                        padding=15,
                        border_radius=10,
                        margin=ft.margin.only(bottom=10)
                    )
                )
                page.update()
                return
            
            preset_prompt, preset_thinking = get_preset(user_query.split()[0])
            
            if preset_prompt:
                state.active_preset = user_query.split()[0]
                original_thinking = state.thinking_level
                state.thinking_level = preset_thinking
                
                preset_label = get_preset_indicator(state.active_preset)
                if preset_label:
                    chat_list.controls.append(
                        ft.Container(
                            content=ft.Text(preset_label, size=12, weight="bold", color=ft.Colors.BLUE_400),
                            padding=5,
                            margin=ft.margin.only(bottom=5)
                        )
                    )
                
                parts = user_query.split(maxsplit=1)
                user_query = parts[1] if len(parts) > 1 else "Analyze the uploaded files."
            else:
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
        
        # User message - using Text with selectable for copy functionality
        chat_list.controls.append(
            ft.Container(
                content=ft.Text(user_query, size=16, selectable=True),
                bgcolor=ft.Colors.BLUE_GREY_900,
                padding=15,
                border_radius=ft.border_radius.only(top_left=15, top_right=15, bottom_left=15),
                alignment=ft.alignment.center_right,
                margin=ft.margin.only(left=50, bottom=10)
            )
        )
        
        # Streaming response
        response_text = ft.Markdown("⏳ Thinking...",
                                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                                    code_theme="atom-one-dark",
                                    selectable=True)
        
        response_container = ft.Container(
            content=response_text,
            bgcolor=ft.Colors.GREY_900,
            padding=15,
            border_radius=ft.border_radius.only(top_left=15, top_right=15, bottom_right=15),
            alignment=ft.alignment.center_left,
            margin=ft.margin.only(right=50, bottom=10)
        )
        
        chat_list.controls.append(response_container)
        page.update()
        
        # Run API call in thread to avoid blocking UI
        def safe_update():
            """Safely update page, catching disconnection errors"""
            try:
                if page.page:
                    page.update()
            except Exception:
                pass  # Page closed or disconnected
        
        def process_response():
            try:
                messages = []
                
                if preset_prompt:
                    messages.append(types.Content(role="user", parts=[types.Part(text=preset_prompt)]))
                    messages.append(types.Content(role="model", parts=[types.Part(text="Understood.")]))
                else:
                    messages.append(types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)]))
                    messages.append(types.Content(role="model", parts=[types.Part(text="Understood.")]))
                
                messages.extend(state.conversation_history)
                messages.append(types.Content(role="user", parts=[types.Part(text=user_query)]))

                # Build tools
                from google.genai.types import GenerateContentConfig, ThinkingConfig, Tool, GoogleSearch
                tools = [Tool(function_declarations=[get_chart_tool_declaration()])]
                if state.google_search_enabled:
                    tools.append(Tool(google_search=GoogleSearch()))
                
                # Use cache if available
                if state.current_cache_name:
                    config = GenerateContentConfig(
                        cached_content=state.current_cache_name,
                        thinking_config=ThinkingConfig(thinking_level=state.thinking_level),
                        tools=tools
                    )
                    stream = client.models.generate_content_stream(
                        model=MODEL_ID,
                        contents=messages,
                        config=config
                    )
                else:
                    if state.uploaded_files:
                        file_parts = [types.Part.from_uri(file_uri=f["uri"], mime_type=f["mime"])
                                     for f in state.uploaded_files]
                        messages[-1] = types.Content(role="user", parts=file_parts + [types.Part(text=user_query)])
                    
                    config = GenerateContentConfig(
                        thinking_config=ThinkingConfig(thinking_level=state.thinking_level),
                        tools=tools
                    )
                    stream = client.models.generate_content_stream(
                        model=MODEL_ID,
                        contents=messages,
                        config=config
                    )
                
                full_text = ""
                function_call = None
                
                for chunk in stream:
                    for part in chunk.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call = part.function_call
                        elif hasattr(part, 'text') and part.text:
                            full_text += part.text
                            response_text.value = full_text
                            safe_update()
                
                # Handle charts
                if function_call and function_call.name == "generate_chart":
                    try:
                        response_text.value = full_text + "\n\n⏳ Generating chart..."
                        safe_update()
                        
                        chart_data = dict(function_call.args)
                        chart_base64 = generate_chart(chart_data)
                        
                        def close_dialog(e):
                            chart_dialog.open = False
                            safe_update()
                        
                        def export_chart(e):
                            def save_chart_result(e: ft.FilePickerResultEvent):
                                if e.path:
                                    try:
                                        import base64
                                        with open(e.path, 'wb') as f:
                                            f.write(base64.b64decode(chart_base64))
                                        status_text.value = f"Chart saved to {e.path}"
                                        safe_update()
                                    except Exception as err:
                                        status_text.value = f"Export error: {str(err)[:50]}"
                                        safe_update()
                            
                            chart_save_picker = ft.FilePicker(on_result=save_chart_result)
                            page.overlay.append(chart_save_picker)
                            safe_update()
                            
                            chart_save_picker.save_file(
                                file_name=f"gemdesk_chart_{int(time.time())}.png",
                                allowed_extensions=["png"],
                                dialog_title="Save Chart"
                            )
                        
                        chart_dialog = ft.AlertDialog(
                            title=ft.Text(chart_data.get('title', 'Chart')),
                            content=ft.Image(src_base64=chart_base64, width=800, height=600, fit=ft.ImageFit.CONTAIN),
                            actions=[
                                ft.TextButton("Export PNG", on_click=export_chart),
                                ft.TextButton("Close", on_click=close_dialog)
                            ]
                        )
                        
                        page.dialog = chart_dialog
                        chart_dialog.open = True
                        
                        full_text = f"📊 **{chart_data.get('title', 'Chart')}**\n\n" + full_text
                        response_text.value = full_text
                        
                    except Exception as chart_err:
                        full_text = f"❌ Chart error: {str(chart_err)[:100]}\n\n" + full_text
                        response_text.value = full_text
                
                safe_update()
                
                state.conversation_history.append(types.Content(role="user", parts=[types.Part(text=user_query)]))
                state.conversation_history.append(types.Content(role="model", parts=[types.Part(text=full_text)]))
                
                if preset_prompt and original_thinking:
                    state.active_preset = None
                    state.thinking_level = original_thinking
                
                update_context_meter()
                
            except Exception as err:
                response_text.value = f"❌ Error: {str(err)[:200]}"
                safe_update()
        
        # Start thread
        threading.Thread(target=process_response, daemon=True).start()
    
    # UI elements
    file_picker = ft.FilePicker()
    file_picker.on_result = upload_file
    page.overlay.append(file_picker)
    
    def open_file_picker(e):
        file_picker.pick_files(allow_multiple=True)
    
    shelf_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    
    model_dropdown = ft.Dropdown(
        width=200,
        height=40,
        text_size=12,
        value=MODEL_ID,
        options=[
            ft.dropdown.Option(key, AVAILABLE_MODELS[key]["name"])
            for key in AVAILABLE_MODELS.keys()
        ],
        on_change=change_model,
        label="Model",
        tooltip="Select Gemini model"
    )
    
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
        tooltip="Reasoning depth"
    )
    
    search_toggle = ft.Switch(
        label="Google Search",
        value=False,
        on_change=toggle_google_search,
        label_position=ft.LabelPosition.LEFT,
        tooltip="Web search grounding"
    )
    
    export_btn = ft.IconButton(
        icon=ft.icons.DOWNLOAD,
        icon_size=20,
        on_click=export_chat,
        tooltip="Export chat as PDF"
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
        bgcolor=ft.Colors.GREY_800,
        color=ft.Colors.WHITE,
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
        hint_text=f"Ask {AVAILABLE_MODELS[MODEL_ID]['name']}...",
        border_color=ft.Colors.TRANSPARENT,
        bgcolor=ft.Colors.GREY_900,
        color=ft.Colors.WHITE,
        border_radius=30,
        content_padding=20,
        expand=True,
        on_submit=send_chat
    )

    sidebar = ft.Container(
        width=300,
        bgcolor=ft.Colors.GREY_900,
        border_radius=15,
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Text("SHELF", size=20, weight="bold", color=ft.Colors.WHITE),
                export_btn
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            model_dropdown,
            thinking_dropdown,
            search_toggle,
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
