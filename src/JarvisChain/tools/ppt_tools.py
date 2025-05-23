from langchain.tools import BaseTool
import json
import os
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from src.JarvisChain.utils.logger import get_logger

# 获取日志记录器
logger = get_logger('ppt_tools')

class BasePPTTool(BaseTool):
    """PPT工具基类，提供通用功能"""
    ppts_dir: str = os.path.join(os.getcwd(), "ppts")

    def __init__(self, **data):
        super().__init__(**data)
        if not os.path.exists(self.ppts_dir):
            os.makedirs(self.ppts_dir)

    def _generate_filename(self, prefix: str = "presentation") -> str:
        """生成唯一的文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.pptx"

    def _get_layout_by_name(self, prs: Presentation, layout_name: str) -> object:
        """根据名称获取布局"""
        layout_mapping = {
            "标题": 0,
            "标题和内容": 1,
            "章节标题": 2,
            "两栏内容": 3,
            "仅标题": 5,
            "空白": 6
        }
        
        layouts = {layout.name: layout for layout in prs.slide_layouts}
        layout = layouts.get(layout_name)
        
        if not layout and layout_name in layout_mapping:
            index = layout_mapping[layout_name]
            if 0 <= index < len(prs.slide_layouts):
                layout = prs.slide_layouts[index]
        
        if not layout:
            layout = prs.slide_layouts[1]
            
        return layout

class PPTCreateTool(BasePPTTool):
    """创建新的PPT文件"""
    name: str = "ppt_create_tool"
    description: str = (
    "创建一个新的PPT文件。输入为JSON格式。，字段："
    "'filename'（可选，PPT文件名）。"
    "注意：'filename' 不能包含文件扩展名。"
)

    def _run(self, input_data: str) -> str:
        try:
            data = json.loads(input_data)
            filename = data.get("filename")
            filename = filename + ".pptx"
            filepath = os.path.join(self.ppts_dir, filename)
            
            prs = Presentation()
            prs.save(filepath)
            
            return json.dumps({
                "success": True,
                "filename": filename,
                "filepath": filepath
            })
        except Exception as e:
            logger.error(f"创建PPT文件失败: {str(e)}")
            return json.dumps({
                "success": False,
                "message": str(e)
            })

    async def _arun(self, input_data: str) -> str:
        return self._run(input_data)


class PPTAddSlideTool(BasePPTTool):
    """添加新的幻灯片"""
    name: str = "ppt_add_slide_tool"
    description: str = (
    "向指定PPT添加一页新的幻灯片。输入为JSON格式，不要有多余内容。字段："
    "'filename'（PPT文件名）、"
    "'layout'（可选，幻灯片布局名称，默认：标题和内容）。"
    "注意：'filename' 不能包含文件扩展名。"
)

    def _run(self, input_data: str) -> str:
        try:
            data = json.loads(input_data)
            filename = data.get("filename")
            filename = filename + ".pptx"
            layout_name = data.get("layout", "标题和内容")
            
            filepath = os.path.join(self.ppts_dir, filename)
            prs = Presentation(filepath)
            
            layout = self._get_layout_by_name(prs, layout_name)
            slide = prs.slides.add_slide(layout)
            
            prs.save(filepath)
            
            return json.dumps({
                "success": True,
                "slide_index": len(prs.slides) - 1
            })
        except Exception as e:
            logger.error(f"添加幻灯片失败: {str(e)}")
            return json.dumps({
                "success": False,
                "message": str(e)
            })

    async def _arun(self, input_data: str) -> str:
        return self._run(input_data)

class PPTAddTextTool(BasePPTTool):
    """添加文本到幻灯片"""
    name: str = "ppt_add_text_tool"
    description: str = (
    "向指定幻灯片添加文本框。输入为JSON格式。字段："
    "'filename'（PPT文件名）、"
    "'slide_index'（幻灯片编号，从0开始）"
    "'text'（要插入的文本内容，支持换行和项目符号）、"
    "'position'（可选，字典：left, top, width, height，单位：英寸）、"
    "'style'（可选，字体样式，包括 font、size、color、align）。"
    "The slide index should start from 0 for the first slide."
     "注意：'color' 必须是长度为3的数组，如 [0, 0, 0] 表示黑色。"
     "注意：'filename' 不能包含文件扩展名。"
    
)

    def _run(self, input_data: str) -> str:
        try:
            data = json.loads(input_data)
            filename = data.get("filename")
            filename = filename + ".pptx"

            slide_index = data.get("slide_index", -1)
            text = data.get("text", "")
            position = data.get("position", {})
            style = data.get("style", {})
            
            filepath = os.path.join(self.ppts_dir, filename)
            prs = Presentation(filepath)
            
            if not (0 <= slide_index < len(prs.slides)):
                raise ValueError("无效的幻灯片索引")
            
            slide = prs.slides[slide_index]
            
            left = Inches(position.get('left', 1))
            top = Inches(position.get('top', 1))
            width = Inches(position.get('width', 8))
            height = Inches(position.get('height', 2))
            
            textbox = slide.shapes.add_textbox(left, top, width, height)
            text_frame = textbox.text_frame
            text_frame.text = ""
            
            lines = text.split('\n')
            first = True
            for line in lines:
                if first:
                    p = text_frame.paragraphs[0]
                    first = False
                else:
                    p = text_frame.add_paragraph()
                
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    p.level = 0
                    p.text = line.strip()[1:].strip()
                elif line.strip().startswith('  -') or line.strip().startswith('  •'):
                    p.level = 1
                    p.text = line.strip()[3:].strip()
                else:
                    p.text = line
                
                p.alignment = PP_ALIGN.CENTER if style.get('align') == 'center' else PP_ALIGN.LEFT
                
                font = p.font
                font.name = style.get('font', '微软雅黑')
                font.size = Pt(style.get('size', 18))
                
                if 'color' in style:
                    r, g, b = style['color']
                    font.color.rgb = RGBColor(r, g, b)
            
            prs.save(filepath)
            
            return json.dumps({
                "success": True,
                "shape_index": len(slide.shapes) - 1
            })
        except Exception as e:
            logger.error(f"添加文本失败: {str(e)}")
            return json.dumps({
                "success": False,
                "message": str(e)
            })

    async def _arun(self, input_data: str) -> str:
        return self._run(input_data)

class PPTAddImageTool(BasePPTTool):
    """添加图片到幻灯片"""
    name: str = "ppt_add_image_tool"
    description: str = (
    "向指定幻灯片添加图片。输入为JSON格式。字段："
    "'filename'（PPT文件名）、"
    "'slide_index'（幻灯片编号，从1开始）、"
    "'image_path'（图片文件路径）、"
    "'position'（可选，字典：left, top, width, height，单位：英寸）。"
    "图片文件支持放置于项目根目录的 img 文件夹内。"
     "The slide index should start from 0 for the first slide."
     "注意：'filename' 不能包含文件扩展名。"
)

    def _run(self, input_data: str) -> str:
        try:
            data = json.loads(input_data)
            filename = data.get("filename")
            filename = filename + ".pptx"

            slide_index = data.get("slide_index", -1)
            image_path = data.get("image_path")
            position = data.get("position", {})
            
            if not image_path:
                raise ValueError("需要提供图片路径")
            
            filepath = os.path.join(self.ppts_dir, filename)
            prs = Presentation(filepath)
            
            if not (0 <= slide_index < len(prs.slides)):
                raise ValueError("无效的幻灯片索引")
            
            slide = prs.slides[slide_index]
            
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                # 尝试在img目录查找
                img_dir = os.path.join(os.getcwd(), "img")
                alternative_path = os.path.join(img_dir, os.path.basename(image_path))
                if os.path.exists(alternative_path):
                    image_path = alternative_path
                else:
                    raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            left = Inches(position.get('left', 1))
            top = Inches(position.get('top', 1))
            width = Inches(position.get('width', 6))
            height = Inches(position.get('height', 4))
            
            slide.shapes.add_picture(image_path, left, top, width, height)
            prs.save(filepath)
            
            return json.dumps({
                "success": True,
                "shape_index": len(slide.shapes) - 1
            })
        except Exception as e:
            logger.error(f"添加图片失败: {str(e)}")
            return json.dumps({
                "success": False,
                "message": str(e)
            })

    async def _arun(self, input_data: str) -> str:
        return self._run(input_data)

class PPTSetBackgroundTool(BasePPTTool):
    """设置幻灯片背景"""
    name: str = "ppt_set_background_tool"
    description: str = (
    "设置指定幻灯片的背景颜色。输入为JSON格式。字段："
    "'filename'（PPT文件名）、"
    "'slide_index'（幻灯片编号，从1开始）、"
    "'color'（RGB颜色数组，如：[255,255,255] 表示白色）。"
    "The slide index should start from 0 for the first slide."
    "注意：'filename' 不能包含文件扩展名。"
)

    def _run(self, input_data: str) -> str:
        try:
            data = json.loads(input_data)
            filename = data.get("filename")
            filename = filename + ".pptx"
            
            slide_index = data.get("slide_index", -1)
            color = data.get("color", (255, 255, 255))
            
            filepath = os.path.join(self.ppts_dir, filename)
            prs = Presentation(filepath)
            
            if not (0 <= slide_index < len(prs.slides)):
                raise ValueError("无效的幻灯片索引")
            
            slide = prs.slides[slide_index]
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(*color)
            
            prs.save(filepath)
            
            return json.dumps({
                "success": True
            })
        except Exception as e:
            logger.error(f"设置背景失败: {str(e)}")
            return json.dumps({
                "success": False,
                "message": str(e)
            })

    async def _arun(self, input_data: str) -> str:
        return self._run(input_data) 