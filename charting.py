"""
Charting utilities for GemDesk
Generates charts from Gemini analysis and exports to PNG
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import json
import tempfile
import os


def parse_chart_json(json_str):
    """Parse chart data from Gemini JSON response"""
    try:
        # Try to find JSON in the response (might have markdown code blocks)
        if '```json' in json_str:
            start = json_str.find('```json') + 7
            end = json_str.find('```', start)
            json_str = json_str[start:end].strip()
        elif '```' in json_str:
            start = json_str.find('```') + 3
            end = json_str.find('```', start)
            json_str = json_str[start:end].strip()
        
        data = json.loads(json_str)
        return data
    except Exception as e:
        raise Exception(f"Failed to parse chart JSON: {e}")


def generate_chart(chart_data):
    """
    Generate chart from data dictionary
    
    Expected format:
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
        chart_type = chart_data.get('chart_type', 'bar').lower()
        title = chart_data.get('title', 'Chart')
        x_label = chart_data.get('x_label', '')
        y_label = chart_data.get('y_label', '')
        data = chart_data.get('data', {})
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
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
        
        plt.tight_layout()
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(temp_file.name, dpi=150, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
        
    except Exception as e:
        plt.close()
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
