from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict, Any, IO, Type, ClassVar
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import os
import json
from src.utils.logger import get_logger

# Get logger
logger = get_logger('ppt')

class PPTElement(BaseModel):
    """Base model for PPT elements"""
    slide_index: int = Field(..., description="Index of the slide (0-based)")
    element_type: str = Field(..., description="Type of element (text/image/shape)")

class TextElement(PPTElement):
    """Model for text elements"""
    text: str = Field(..., description="Text content")
    font_size: Optional[int] = Field(default=18, description="Font size in points")
    font_color: Optional[str] = Field(default="#000000", description="Font color in hex")
    alignment: Optional[str] = Field(default="left", description="Text alignment (left/center/right)")
    bold: Optional[bool] = Field(default=False, description="Whether text is bold")
    italic: Optional[bool] = Field(default=False, description="Whether text is italic")
    x: Optional[float] = Field(default=1.0, description="X position in inches")
    y: Optional[float] = Field(default=1.0, description="Y position in inches")
    width: Optional[float] = Field(default=8.0, description="Width in inches")
    height: Optional[float] = Field(default=1.0, description="Height in inches")

class ImageElement(PPTElement):
    """Model for image elements"""
    image_path: str = Field(..., description="Path to the image file")
    x: Optional[float] = Field(default=1.0, description="X position in inches")
    y: Optional[float] = Field(default=1.0, description="Y position in inches")
    width: Optional[float] = Field(default=4.0, description="Width in inches")
    height: Optional[float] = Field(default=3.0, description="Height in inches")

class ShapeElement(PPTElement):
    """Model for shape elements"""
    shape_type: str = Field(..., description="Type of shape (rectangle/oval/line)")
    fill_color: Optional[str] = Field(default="#FFFFFF", description="Fill color in hex")
    line_color: Optional[str] = Field(default="#000000", description="Line color in hex")
    x: Optional[float] = Field(default=1.0, description="X position in inches")
    y: Optional[float] = Field(default=1.0, description="Y position in inches")
    width: Optional[float] = Field(default=2.0, description="Width in inches")
    height: Optional[float] = Field(default=1.0, description="Height in inches")

class PPTTool(BaseTool):
    """Tool for creating and editing PowerPoint presentations"""
    name: str = "ppt_creation_tool"
    description: str = """Tool for creating and editing PowerPoint presentations.
    Can perform the following operations:
    1. Create new presentation
    2. Open existing presentation
    3. Add/remove slides
    4. Add text with formatting
    5. Add images
    6. Add shapes
    7. Modify background
    8. Save presentation
    
    Input should be a JSON string containing:
    {
        "operation": "create/open/add_slide/add_text/add_image/add_shape/save",
        "parameters": {
            "file_path": "path/to/presentation.pptx",  // Required for most operations
            // Other operation-specific parameters
        }
    }
    """
    args_schema: Type[BaseModel] = None
    
    def __init__(self):
        super().__init__()
        self._presentation: Optional[Presentation] = None
        self._current_file: Optional[str] = None
    
    @property
    def presentation(self) -> Optional[Presentation]:
        return self._presentation
    
    @presentation.setter
    def presentation(self, value: Optional[Presentation]):
        self._presentation = value
    
    @property
    def current_file(self) -> Optional[str]:
        return self._current_file
    
    @current_file.setter
    def current_file(self, value: Optional[str]):
        self._current_file = value

    def _hex_to_rgb(self, hex_color: str) -> RGBColor:
        """将十六进制颜色转换为 RGBColor"""
        hex_color = hex_color.lstrip('#')
        return RGBColor(
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    
    def _get_alignment(self, alignment: str) -> PP_ALIGN:
        """将对齐方式字符串转换为 PP_ALIGN"""
        alignments = {
            "left": PP_ALIGN.LEFT,
            "center": PP_ALIGN.CENTER,
            "right": PP_ALIGN.RIGHT
        }
        return alignments.get(alignment.lower(), PP_ALIGN.LEFT)

    def _ensure_presentation_loaded(self, file_path: str) -> bool:
        """确保演示文稿已加载"""
        try:
            if self.current_file != file_path or self.presentation is None:
                if os.path.exists(file_path):
                    # 检查文件是否可写
                    if not os.access(file_path, os.W_OK):
                        logger.error(f"File is not writable: {file_path}")
                        return False
                    try:
                        self.presentation = Presentation(file_path)
                        self.current_file = file_path
                    except PermissionError:
                        logger.error(f"Permission denied: {file_path}. File might be open in another program.")
                        return False
                else:
                    logger.error(f"Presentation file not found: {file_path}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error loading presentation: {str(e)}")
            return False
    
    def create_presentation(self, file_path: str) -> bool:
        """创建新的演示文稿"""
        try:
            # 检查目录是否存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # 检查文件是否可写
            if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
                logger.error(f"File is not writable: {file_path}")
                return False
                
            self.presentation = Presentation()
            self.current_file = file_path
            # 保存空演示文稿
            self.presentation.save(file_path)
            return True
        except PermissionError:
            logger.error(f"Permission denied: {file_path}. File might be open in another program.")
            return False
        except Exception as e:
            logger.error(f"Error creating presentation: {str(e)}")
            return False
    
    def open_presentation(self, file_path: str) -> bool:
        """打开现有的演示文稿"""
        return self._ensure_presentation_loaded(file_path)
    
    def add_slide(self, file_path: str, layout_name: str = "Title and Content") -> Optional[int]:
        """添加新幻灯片"""
        try:
            if not self._ensure_presentation_loaded(file_path):
                return None
                
            layouts = {
                "title": 0,
                "title and content": 1,
                "section header": 2,
                "two content": 3,
                "comparison": 4,
                "title only": 5,
                "blank": 6,
                "content with caption": 7,
                "picture with caption": 8
            }
            layout_index = layouts.get(layout_name.lower(), 1)
            slide_layout = self.presentation.slide_layouts[layout_index]
            slide = self.presentation.slides.add_slide(slide_layout)
            # 保存更改
            self.presentation.save(file_path)
            return len(self.presentation.slides) - 1
        except Exception as e:
            logger.error(f"Error adding slide: {str(e)}")
            return None
    
    def add_text(self, file_path: str, element: TextElement) -> bool:
        """添加文本到幻灯片"""
        try:
            if not self._ensure_presentation_loaded(file_path):
                return False
                
            slide = self.presentation.slides[element.slide_index]
            textbox = slide.shapes.add_textbox(
                Inches(element.x),
                Inches(element.y),
                Inches(element.width),
                Inches(element.height)
            )
            text_frame = textbox.text_frame
            text_frame.text = element.text
            
            # 应用文本格式
            paragraph = text_frame.paragraphs[0]
            paragraph.alignment = self._get_alignment(element.alignment)
            
            run = paragraph.runs[0]
            run.font.size = Pt(element.font_size)
            run.font.color.rgb = self._hex_to_rgb(element.font_color)
            run.font.bold = element.bold
            run.font.italic = element.italic
            
            # 保存更改
            self.presentation.save(file_path)
            return True
        except Exception as e:
            logger.error(f"Error adding text: {str(e)}")
            return False
    
    def add_image(self, file_path: str, element: ImageElement) -> bool:
        """添加图片到幻灯片"""
        try:
            if not self._ensure_presentation_loaded(file_path):
                return False
                
            if not os.path.exists(element.image_path):
                logger.error(f"Image file not found: {element.image_path}")
                return False
                
            if not os.access(element.image_path, os.R_OK):
                logger.error(f"Image file is not readable: {element.image_path}")
                return False
                
            slide = self.presentation.slides[element.slide_index]
            slide.shapes.add_picture(
                element.image_path,
                Inches(element.x),
                Inches(element.y),
                Inches(element.width),
                Inches(element.height)
            )
            # 保存更改
            try:
                self.presentation.save(file_path)
            except PermissionError:
                logger.error(f"Permission denied when saving: {file_path}. File might be open in another program.")
                return False
            return True
        except Exception as e:
            logger.error(f"Error adding image: {str(e)}")
            return False
    
    def add_shape(self, file_path: str, element: ShapeElement) -> bool:
        """添加形状到幻灯片"""
        try:
            if not self._ensure_presentation_loaded(file_path):
                return False
                
            slide = self.presentation.slides[element.slide_index]
            shape_types = {
                "rectangle": 1,
                "oval": 9,
                "line": 13
            }
            shape_type = shape_types.get(element.shape_type.lower(), 1)
            
            shape = slide.shapes.add_shape(
                shape_type,
                Inches(element.x),
                Inches(element.y),
                Inches(element.width),
                Inches(element.height)
            )
            
            # 应用形状格式
            shape.fill.solid()
            shape.fill.fore_color.rgb = self._hex_to_rgb(element.fill_color)
            shape.line.color.rgb = self._hex_to_rgb(element.line_color)
            
            # 保存更改
            self.presentation.save(file_path)
            return True
        except Exception as e:
            logger.error(f"Error adding shape: {str(e)}")
            return False
    
    def _run(self, query: str) -> str:
        """运行 PPT 工具"""
        try:
            # 解析 JSON 查询
            data = json.loads(query)
            operation = data.get("operation")
            parameters = data.get("parameters", {})
            
            # 获取文件路径
            file_path = parameters.get("file_path")
            if not file_path and operation not in ["create"]:
                return json.dumps({"success": False, "message": "file_path is required for this operation"})
            
            if operation == "create":
                if not file_path:
                    file_path = "presentation.pptx"
                success = self.create_presentation(file_path)
                return json.dumps({"success": success, "message": "Presentation created" if success else "Failed to create presentation"})
                
            elif operation == "open":
                success = self.open_presentation(file_path)
                return json.dumps({"success": success, "message": "Presentation opened" if success else "Failed to open presentation"})
                
            elif operation == "add_slide":
                layout = parameters.get("layout", "title and content")
                slide_index = self.add_slide(file_path, layout)
                return json.dumps({"success": slide_index is not None, "slide_index": slide_index})
                
            elif operation == "add_text":
                element = TextElement(**parameters)
                success = self.add_text(file_path, element)
                return json.dumps({"success": success, "message": "Text added" if success else "Failed to add text"})
                
            elif operation == "add_image":
                element = ImageElement(**parameters)
                success = self.add_image(file_path, element)
                return json.dumps({"success": success, "message": "Image added" if success else "Failed to add image"})
                
            elif operation == "add_shape":
                element = ShapeElement(**parameters)
                success = self.add_shape(file_path, element)
                return json.dumps({"success": success, "message": "Shape added" if success else "Failed to add shape"})
                
            else:
                return json.dumps({"success": False, "message": f"Unknown operation: {operation}"})
                
        except Exception as e:
            return json.dumps({"success": False, "message": f"Error: {str(e)}"})
    
    async def _arun(self, query: str) -> str:
        """异步运行 PPT 工具"""
        return self._run(query) 