"""
UI component builders for GemDesk
Handles shelf organization and file display
"""

import flet as ft


def get_file_category(name, mime):
    """Categorize file for folder organization"""
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


def build_shelf_item(file_info, index, remove_file_fn, page):
    """Build a single shelf item UI component"""
    name = file_info['name']
    mime = file_info['mime']
    tokens = file_info['tokens']
    thumbnail = file_info.get('thumbnail')
    
    # Icon and color based on type
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
    
    # Preview (thumbnail or icon)
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
    
    return ft.Container(
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
                on_click=lambda e, idx=index: remove_file_fn(idx),
                tooltip="Remove"
            )
        ], spacing=10),
        bgcolor=ft.Colors.WHITE10,
        padding=10,
        border_radius=8,
        margin=ft.margin.only(bottom=5)
    )


def build_folder_header(category, label, icon, file_count, is_collapsed, toggle_fn):
    """Build folder header with collapse button"""
    collapse_icon = ft.Icons.CHEVRON_RIGHT if is_collapsed else ft.Icons.EXPAND_MORE
    
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=16, color=ft.Colors.GREY_400),
            ft.Text(f"{label} ({file_count})", size=12, weight="bold", color=ft.Colors.GREY_400),
            ft.IconButton(
                icon=collapse_icon,
                icon_size=16,
                on_click=lambda e, cat=category: toggle_fn(cat)
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=5,
        margin=ft.margin.only(top=5, bottom=2)
    )


def build_shelf_ui(uploaded_files, folders_collapsed, remove_file_fn, toggle_folder_fn, page):
    """
    Build complete shelf UI with categorized folders
    
    Returns: list of UI controls
    """
    controls = []
    
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
    
    # Folder definitions
    folder_names = {
        "documents": ("Documents", ft.Icons.DESCRIPTION),
        "images": ("Images", ft.Icons.IMAGE),
        "videos": ("Videos", ft.Icons.VIDEO_LIBRARY),
        "audio": ("Audio", ft.Icons.AUDIOTRACK),
        "links": ("Links", ft.Icons.LINK),
        "other": ("Other", ft.Icons.FOLDER)
    }
    
    # Build folders
    for category, (label, icon) in folder_names.items():
        files_in_cat = categorized[category]
        if not files_in_cat:
            continue
        
        # Add folder header
        controls.append(build_folder_header(
            category, label, icon, len(files_in_cat),
            folders_collapsed.get(category, False),
            toggle_folder_fn
        ))
        
        # Add files if not collapsed
        if not folders_collapsed.get(category, False):
            for idx, f in files_in_cat:
                controls.append(build_shelf_item(f, idx, remove_file_fn, page))
    
    return controls
