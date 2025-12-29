"""
File conversion utilities for GemDesk
Handles conversion of various file formats to text/CSV for Gemini processing
"""

import tempfile
import requests
import os
import base64
from bs4 import BeautifulSoup


def convert_xlsx_to_csv(xlsx_path):
    """Convert Excel file to CSV"""
    try:
        import pandas as pd
        excel_file = pd.ExcelFile(xlsx_path)
        csv_content = ""
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
            csv_content += f"# Sheet: {sheet_name}\n"
            csv_content += df.to_csv(index=False)
            csv_content += "\n\n"
        temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_csv.write(csv_content)
        temp_csv.close()
        return temp_csv.name
    except ImportError:
        raise Exception("pandas and openpyxl required. Install: pip install pandas openpyxl")


def convert_ods_to_csv(ods_path):
    """Convert ODS (OpenDocument Spreadsheet) to CSV"""
    try:
        import pandas as pd
        excel_file = pd.read_excel(ods_path, engine='odf', sheet_name=None)
        csv_content = ""
        for sheet_name, df in excel_file.items():
            csv_content += f"# Sheet: {sheet_name}\n"
            csv_content += df.to_csv(index=False)
            csv_content += "\n\n"
        temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_csv.write(csv_content)
        temp_csv.close()
        return temp_csv.name
    except ImportError:
        raise Exception("pandas and odfpy required. Install: pip install pandas odfpy")


def convert_pptx_to_text(pptx_path):
    """Convert PowerPoint to text"""
    try:
        from pptx import Presentation
        prs = Presentation(pptx_path)
        text_content = ""
        for i, slide in enumerate(prs.slides, 1):
            text_content += f"=== SLIDE {i} ===\n"
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text_content += shape.text + "\n"
            text_content += "\n"
        temp_txt = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_txt.write(text_content)
        temp_txt.close()
        return temp_txt.name
    except ImportError:
        raise Exception("python-pptx required. Install: pip install python-pptx")


def convert_odp_to_text(odp_path):
    """Convert ODP (OpenDocument Presentation) to text"""
    try:
        from odf import text as odf_text
        from odf.opendocument import load
        
        doc = load(odp_path)
        text_content = ""
        
        for paragraph in doc.getElementsByType(odf_text.P):
            if paragraph.firstChild:
                text_content += str(paragraph.firstChild) + "\n"
        
        temp_txt = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_txt.write(text_content)
        temp_txt.close()
        return temp_txt.name
    except ImportError:
        raise Exception("odfpy required. Install: pip install odfpy")


def convert_odt_to_text(odt_path):
    """Convert ODT (OpenDocument Text) to text"""
    try:
        from odf import text as odf_text
        from odf.opendocument import load
        
        doc = load(odt_path)
        text_content = ""
        
        for paragraph in doc.getElementsByType(odf_text.P):
            if paragraph.firstChild:
                text_content += str(paragraph.firstChild) + "\n"
        
        temp_txt = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_txt.write(text_content)
        temp_txt.close()
        return temp_txt.name
    except ImportError:
        raise Exception("odfpy required. Install: pip install odfpy")


def download_file_from_url(url):
    """Download a file directly from URL (PDFs, images, videos, etc.)"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Get file extension from URL or content-type
        import mimetypes
        content_type = response.headers.get('content-type', '')
        
        # Try to get extension from URL first
        from urllib.parse import urlparse
        path = urlparse(url).path
        ext = path[path.rfind('.'):] if '.' in path.split('/')[-1] else ''
        
        # If no extension in URL, try to guess from content-type
        if not ext:
            ext = mimetypes.guess_extension(content_type.split(';')[0]) or '.bin'
        
        # Download to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        raise Exception(f"Failed to download file from URL: {str(e)}")


def is_direct_file_url(url):
    """Check if URL points to a direct file (not HTML page)"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        content_type = response.headers.get('content-type', '').lower()
        
        # Check if it's a file type we support
        file_types = [
            'application/pdf',
            'image/',
            'video/',
            'audio/',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats',
            'application/vnd.oasis.opendocument',
            'application/msword',
            'text/plain',
            'text/csv',
        ]
        
        for file_type in file_types:
            if file_type in content_type:
                return True
        
        # Also check URL extension
        url_lower = url.lower()
        file_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', 
                          '.avi', '.mp3', '.wav', '.xlsx', '.docx', '.pptx', '.csv', '.txt']
        return any(url_lower.endswith(ext) for ext in file_extensions)
    except:
        return False


def scrape_url(url):
    """Scrape text content from a URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        temp_txt = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_txt.write(f"URL: {url}\n\n{text}")
        temp_txt.close()
        return temp_txt.name
    except Exception as e:
        raise Exception(f"Failed to scrape URL: {str(e)}")


def generate_thumbnail(file_path, mime_type, size=(100, 100)):
    """Generate thumbnail for image, PDF, or video files"""
    try:
        from PIL import Image
        import io
        
        if 'image' in mime_type:
            # Images - direct thumbnail
            img = Image.open(file_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
            
        elif 'pdf' in mime_type:
            # PDFs - extract first page
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))  # 50% scale
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                doc.close()
                
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode()
            except ImportError:
                return None  # PyMuPDF not installed
                
        elif 'video' in mime_type:
            # Videos - extract frame 100 (skip black intro frames)
            try:
                import cv2
                cap = cv2.VideoCapture(file_path)
                
                # Try to get frame 100, fallback to frame 30 if video is shorter
                cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
                ret, frame = cap.read()
                
                # If frame 100 fails, try frame 30
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
                    ret, frame = cap.read()
                
                cap.release()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    return base64.b64encode(buffered.getvalue()).decode()
                return None
            except ImportError:
                return None  # opencv not installed
        
        return None  # Unsupported type
        
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
        return None
