"""
File operation handlers for GemDesk
Handles file uploads, URL processing, and MIME type detection
"""

import os
import time
import mimetypes
from google.genai import types
from conversions import (
    convert_docx_to_pdf, convert_xlsx_to_csv, convert_ods_to_csv,
    convert_odp_to_text, convert_odt_to_text, download_file_from_url,
    is_direct_file_url, scrape_url, generate_thumbnail
)


def get_mime_type(filename):
    """Get MIME type from filename"""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type
    
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        # Documents
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
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
        # OpenDocument
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',
        '.odt': 'application/vnd.oasis.opendocument.text',
        # Code & Config (80+ languages)
        '.py': 'text/plain', '.js': 'text/plain', '.ts': 'text/plain',
        '.jsx': 'text/plain', '.tsx': 'text/plain', '.java': 'text/plain',
        '.c': 'text/plain', '.cpp': 'text/plain', '.h': 'text/plain',
        '.hpp': 'text/plain', '.cs': 'text/plain', '.go': 'text/plain',
        '.rs': 'text/plain', '.swift': 'text/plain', '.kt': 'text/plain',
        '.scala': 'text/plain', '.rb': 'text/plain', '.php': 'text/plain',
        '.yaml': 'text/plain', '.yml': 'text/plain', '.toml': 'text/plain',
        '.ini': 'text/plain', '.cfg': 'text/plain', '.conf': 'text/plain',
        '.sh': 'text/plain', '.bash': 'text/plain', '.sql': 'text/plain',
        '.r': 'text/plain', '.jl': 'text/plain', '.ipynb': 'text/plain',
    }
    return mime_map.get(ext, 'application/octet-stream')


def process_file_upload(file_path, file_name, client, model_id, uploaded_files, 
                        status_text, page, override_mime=None):
    """
    Process a single file upload with format conversion if needed
    
    Returns: dict with file info or raises exception
    """
    file_to_upload = file_path
    original_name = file_name
    
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
    
    # Upload to Gemini
    with open(file_to_upload, 'rb') as file_handle:
        file_ref = client.files.upload(file=file_handle, config={'mime_type': mime_type})
    
    # Clean up converted file
    if file_to_upload != file_path:
        os.unlink(file_to_upload)
    
    # Wait for processing
    while file_ref.state.name == "PROCESSING":
        status_text.value = f"Processing {file_name}..."
        page.update()
        time.sleep(1)
        file_ref = client.files.get(name=file_ref.name)
    
    if file_ref.state.name == "FAILED":
        raise Exception(f"Failed to process {file_name}")
    
    # Count tokens
    status_text.value = f"Counting tokens..."
    page.update()
    
    file_token_count = client.models.count_tokens(
        model=model_id,
        contents=[types.Content(role="user", parts=[
            types.Part.from_uri(file_uri=file_ref.uri, mime_type=file_ref.mime_type)
        ])]
    )
    
    return {
        "name": original_name,
        "uri": file_ref.uri,
        "mime": file_ref.mime_type,
        "tokens": file_token_count.total_tokens,
        "thumbnail": generate_thumbnail(file_path, mime_type)
    }


def handle_file_upload(e, uploaded_files, max_files, client, model_id,
                       status_text, loading_ring, upload_btn, page,
                       rebuild_shelf_fn, update_cache_fn, update_meter_fn):
    """Handle file picker upload event"""
    if not e.files:
        return
    
    if len(uploaded_files) + len(e.files) > max_files:
        status_text.value = f"Error: Maximum {max_files} files"
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
            file_info = process_file_upload(
                f.path, f.name, client, model_id, uploaded_files,
                status_text, page
            )
            uploaded_files.append(file_info)
        
        status_text.value = "Ready."
        rebuild_shelf_fn()
        update_cache_fn()
        update_meter_fn()
        
    except Exception as err:
        print(f"Upload error: {err}")
        status_text.value = f"Error: {err}"
    finally:
        loading_ring.visible = False
        upload_btn.disabled = False
        page.update()


def handle_url_add(url_input, uploaded_files, max_files, client, model_id,
                   status_text, loading_ring, url_btn, page,
                   rebuild_shelf_fn, update_cache_fn, update_meter_fn):
    """Handle URL input and download/scrape"""
    url = url_input.value.strip()
    if not url:
        return
    
    url_input.value = ""
    
    if len(uploaded_files) >= max_files:
        status_text.value = f"Error: Maximum {max_files} files"
        status_text.color = ft.Colors.RED
        page.update()
        time.sleep(2)
        status_text.color = ft.Colors.GREY_500
        return
    
    loading_ring.visible = True
    url_btn.disabled = True
    page.update()
    
    try:
        # Check if it's a direct file URL
        if is_direct_file_url(url):
            status_text.value = f"Downloading file from {url}..."
            page.update()
            
            temp_file_path = download_file_from_url(url)
            
            from urllib.parse import urlparse
            url_path = urlparse(url).path
            filename = url_path.split('/')[-1] if url_path else 'downloaded_file'
            
            mime_type = get_mime_type(temp_file_path)
            
            file_info = process_file_upload(
                temp_file_path, filename, client, model_id, uploaded_files,
                status_text, page, mime_type
            )
            uploaded_files.append(file_info)
            os.unlink(temp_file_path)
            
            status_text.value = "Ready."
            rebuild_shelf_fn()
            update_cache_fn()
            update_meter_fn()
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
                model=model_id,
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
            
            rebuild_shelf_fn()
            status_text.value = "Ready."
            update_cache_fn()
            update_meter_fn()
        
    except Exception as err:
        print(f"URL error: {err}")
        status_text.value = f"Error: {err}"
    finally:
        loading_ring.visible = False
        url_btn.disabled = False
        page.update()
