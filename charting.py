"""
Charting utilities for GemDesk
Generates charts from Gemini analysis and exports to PNG
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
from matplotlib.figure import Figure
import json
import base64
from io import BytesIO


def generate_chart(chart_data):
    """
    Generate chart from data dictionary via Gemini Function Calling
    
    Expected format from function_call.args:
    {
        "chart_type": "line|bar|pie|scatter",
        "title": "Chart Title",
        "x_label": "X Axis Label" (optional),
        "y_label": "Y Axis Label" (optional),
        "data": {
            "labels": [...],  # For bar/line/pie
            "values": [...],  # Single series
            # OR
            "x": [...],       # For scatter/line
            "y": [...],
            # OR for multiple series:
            "series": [
                {"name": "Series 1", "values": [...]},
                {"name": "Series 2", "values": [...]}
            ]
        }
    }
    """
    try:
        # Validate required fields
        if not isinstance(chart_data, dict):
            raise ValueError("Chart data must be a dictionary")
        
        if 'chart_type' not in chart_data:
            raise ValueError("Missing required field: chart_type")
        
        if 'data' not in chart_data:
            raise ValueError("Missing required field: data")
        
        chart_type = chart_data.get('chart_type', 'bar').lower()
        
        # Validate chart type
        valid_types = {'line', 'bar', 'pie', 'scatter'}
        if chart_type not in valid_types:
            raise ValueError(f"Invalid chart_type: {chart_type}. Must be one of {valid_types}")
        
        title = chart_data.get('title', 'Chart')
        x_label = chart_data.get('x_label', '')
        y_label = chart_data.get('y_label', '')
        data = chart_data.get('data', {})
        
        # Create figure using OO interface (thread-safe)
        fig = Figure(figsize=(10, 6))
        ax = fig.subplots()
        
        if chart_type == 'bar':
            labels = data.get('labels', [])
            values = data.get('values', [])
            
            if 'series' in data:
                # Multiple series bar chart
                series_data = data['series']
                x = range(len(labels))
                width = 0.8 / len(series_data)
                
                for i, series in enumerate(series_data):
                    offset = (i - len(series_data)/2) * width + width/2
                    ax.bar([xi + offset for xi in x], series['values'], 
                          width, label=series['name'])
                ax.set_xticks(x)
                ax.set_xticklabels(labels)
                ax.legend()
            else:
                # Single series
                ax.bar(labels, values)
            
        elif chart_type == 'line':
            if 'series' in data:
                # Multiple series
                for series in data['series']:
                    if 'x' in series:
                        ax.plot(series['x'], series['y'], marker='o', label=series['name'])
                    else:
                        ax.plot(series['values'], marker='o', label=series['name'])
                ax.legend()
            elif 'x' in data and 'y' in data:
                ax.plot(data['x'], data['y'], marker='o')
            else:
                labels = data.get('labels', [])
                values = data.get('values', [])
                ax.plot(labels, values, marker='o')
            
        elif chart_type == 'pie':
            labels = data.get('labels', [])
            values = data.get('values', [])
            ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            
        elif chart_type == 'scatter':
            if 'series' in data:
                for series in data['series']:
                    ax.scatter(series['x'], series['y'], label=series['name'], alpha=0.6, s=50)
                ax.legend()
            else:
                x = data.get('x', [])
                y = data.get('y', [])
                ax.scatter(x, y, alpha=0.6, s=50)
        
        # Set labels and title
        ax.set_title(title, fontsize=14, fontweight='bold')
        if x_label:
            ax.set_xlabel(x_label)
        if y_label:
            ax.set_ylabel(y_label)
        
        # Grid for readability
        if chart_type not in ['pie']:
            ax.grid(True, alpha=0.3)
        
        fig.tight_layout()
        
        # Save to base64 instead of temp file
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode()
        
        return img_str
        
    except Exception as e:
        raise Exception(f"Failed to generate chart: {e}")


def get_chart_tool_declaration():
    """Return the tool declaration for Gemini function calling"""
    return {
        "name": "generate_chart",
        "description": "Generate a chart/graph to visualize data. Use this when the user asks to plot, chart, graph, or visualize data.",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["line", "bar", "pie", "scatter"],
                    "description": "Type of chart to generate"
                },
                "title": {
                    "type": "string",
                    "description": "Chart title"
                },
                "x_label": {
                    "type": "string",
                    "description": "X-axis label (optional)"
                },
                "y_label": {
                    "type": "string",
                    "description": "Y-axis label (optional)"
                },
                "data": {
                    "type": "object",
                    "description": "Chart data with labels and values",
                    "properties": {
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Data labels (for bar/line/pie)"
                        },
                        "values": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Data values (for single series)"
                        },
                        "x": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "X coordinates (for scatter/line)"
                        },
                        "y": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Y coordinates (for scatter/line)"
                        },
                        "series": {
                            "type": "array",
                            "description": "Multiple data series",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "values": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "x": {
                                        "type": "array",
                                        "items": {"type": "number"},
                                        "description": "X coordinates for this series (scatter/line)"
                                    },
                                    "y": {
                                        "type": "array",
                                        "items": {"type": "number"},
                                        "description": "Y coordinates for this series (scatter/line)"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "required": ["chart_type", "title", "data"]
        }
    }
