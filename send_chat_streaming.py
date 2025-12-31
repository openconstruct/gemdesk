# Streaming send_chat function for gem.py
# Replace the existing send_chat function with this

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
    
    # Add streaming response container
    ai_bg = ft.Colors.GREY_900 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200
    
    # Create response container with initial thinking state
    response_text = ft.Markdown(
        "⏳ Thinking...",
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        code_theme="atom-one-dark"
    )
    
    response_container = ft.Container(
        content=response_text,
        bgcolor=ai_bg,
        padding=15,
        border_radius=ft.border_radius.only(top_left=15, top_right=15, bottom_right=15),
        alignment=ft.alignment.center_left,
        margin=ft.margin.only(right=50, bottom=10)
    )
    
    chat_list.controls.append(response_container)
    page.update()

    try:
        # Build messages
        messages = []
        
        # System prompt (use preset if active, otherwise default)
        if preset_prompt:
            messages.append(types.Content(role="user", parts=[types.Part(text=preset_prompt)]))
            messages.append(types.Content(role="model", parts=[types.Part(text="Understood. I will analyze according to the specified mode.")]))
        else:
            messages.append(types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)]))
            messages.append(types.Content(role="model", parts=[types.Part(text="Understood. I will provide expert analysis with specific references to page numbers, timestamps (in MM:SS format with seconds), and data locations as appropriate.")]))
        
        # Conversational context (text only)
        messages.extend(conversation_history)
        
        # Add current query
        messages.append(types.Content(role="user", parts=[types.Part(text=user_query)]))

        # Generate response with streaming
        if current_cache_name:
            from google.genai.types import GenerateContentConfig, ThinkingConfig, Tool
            config = GenerateContentConfig(
                cached_content=current_cache_name,
                thinking_config=ThinkingConfig(thinking_level=thinking_level),
                tools=[Tool(function_declarations=[get_chart_tool_declaration()])]
            )
            stream = client.models.generate_content_stream(
                model=MODEL_ID,
                contents=messages,
                config=config
            )
        else:
            # No cache - send files directly
            if uploaded_files:
                file_parts = [
                    types.Part.from_uri(file_uri=f["uri"], mime_type=f["mime"])
                    for f in uploaded_files
                ]
                messages[-1] = types.Content(role="user", parts=file_parts + [types.Part(text=user_query)])
            
            from google.genai.types import GenerateContentConfig, ThinkingConfig, Tool
            config = GenerateContentConfig(
                thinking_config=ThinkingConfig(thinking_level=thinking_level),
                tools=[Tool(function_declarations=[get_chart_tool_declaration()])]
            )
            stream = client.models.generate_content_stream(
                model=MODEL_ID,
                contents=messages,
                config=config
            )
        
        # Stream response
        full_text = ""
        function_call = None
        
        for chunk in stream:
            # Check for function calls
            for part in chunk.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                elif hasattr(part, 'text') and part.text:
                    full_text += part.text
                    response_text.value = full_text
                    page.update()
        
        # Handle chart generation if tool was called
        if function_call and function_call.name == "generate_chart":
            try:
                response_text.value = full_text + "\n\n⏳ Generating chart..."
                page.update()
                
                chart_data = dict(function_call.args)
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
                
                full_text = f"📊 **Chart Generated: {chart_data.get('title', 'Chart')}**\n\n" + full_text
                response_text.value = full_text
                
            except Exception as chart_err:
                full_text = f"❌ Chart generation failed: {chart_err}\n\n" + full_text
                response_text.value = full_text
                print(f"Chart generation error: {chart_err}")
        
        page.update()
        
        # Store conversation history
        conversation_history.append(types.Content(role="user", parts=[types.Part(text=user_query)]))
        conversation_history.append(types.Content(role="model", parts=[types.Part(text=full_text)]))
        
        # Reset preset after use
        if preset_prompt:
            active_preset = None
            thinking_level = original_thinking
        
        update_context_meter()
        
    except Exception as err:
        response_text.value = f"❌ Error: {err}"
        print(f"Chat error: {err}")
        page.update()
