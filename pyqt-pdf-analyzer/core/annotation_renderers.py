from typing import Dict

from PIL import ImageDraw, ImageFont
from core.annotation_system import AnnotationRenderer, Annotation, AnnotationType

class KeywordRenderer(AnnotationRenderer):
    """Renders keyword annotations as highlighted pills."""
    
    def get_render_priority(self) -> int:
        """Keywords render on top (higher priority)."""
        return 100
    
    def render_annotation(self, annotation: Annotation, draw_context: ImageDraw.Draw, bounds: Dict[str, int]):
        """Render keyword as highlighted pill."""
        x0, y0, x1, y1 = bounds['x0'], bounds['y0'], bounds['x1'], bounds['y1']
        color = annotation.color
        
        # Semi-transparent highlight
        highlight_color = self._hex_to_rgba(color, alpha=80)
        draw_context.rectangle([x0, y0, x1, y1], fill=highlight_color, outline=color, width=2)
        
        # Category label pill
        try:
            font = ImageFont.load_default()
            label = f" {annotation.category} "
            bbox_size = draw_context.textbbox((0, 0), label, font=font)
            text_width = bbox_size[2] - bbox_size[0]
            text_height = bbox_size[3] - bbox_size[1]
            
            label_x = x0
            label_y = max(0, y0 - text_height - 6)
            label_bg = [label_x, label_y, label_x + text_width + 4, label_y + text_height + 4]
            draw_context.rounded_rectangle(label_bg, radius=8, fill=color)
            draw_context.text((label_x + 2, label_y + 2), label, fill="white", font=font)
        except Exception:
            # Fallback: do nothing if text rendering fails
            pass
    
    def _hex_to_rgba(self, hex_color: str, alpha: int = 255) -> tuple:
        """Convert hex color to RGBA tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r, g, b, alpha)
        return (128, 128, 128, alpha)

class URLRenderer(AnnotationRenderer):
    """Renders URL annotations as status borders with indicators."""
    
    def get_render_priority(self) -> int:
        """URLs render in background (lower priority)."""
        return 50
    
    def render_annotation(self, annotation: Annotation, draw_context: ImageDraw.Draw, bounds: Dict[str, int]):
        """Render URL as status border with indicator dot."""
        x0, y0, x1, y1 = bounds['x0'], bounds['y0'], bounds['x1'], bounds['y1']
        color = annotation.color
        
        # Status border
        draw_context.rectangle([x0-2, y0-2, x1+2, y1+2], outline=color, width=3)
        
        # Status indicator dot
        dot_size = 8
        dot_x = x1 - dot_size - 2
        dot_y = y0 + 2
        draw_context.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size], 
                             fill=color, outline="white", width=1)
