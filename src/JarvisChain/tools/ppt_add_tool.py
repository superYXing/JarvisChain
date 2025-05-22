from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import json
from src.JarvisChain.utils.logger import get_logger
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import os
from datetime import datetime
from src.JarvisChain.models.llm_models import INTENT_MODEL

# Get logger
logger = get_logger('ppt_add')



class PPTAddTool(BaseTool):
    name: str = "ppt_add_tool"
    description: str = """用于创建和添加PPT元素的工具，包括新建幻灯片、添加文本、图片等。"""
    ppts_dir: str = os.path.join(os.getcwd(), "ppts")

    def __init__(self, **data):
        super().__init__(**data)
        if not os.path.exists(self.ppts_dir):
            os.makedirs(self.ppts_dir)

    def _generate_filename(self, prefix: str = "presentation") -> str:
        """生成唯一的文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.pptx"

    def _create_new_presentation(self, filename: str = None) -> tuple[Presentation, str]:
        """创建新的演示文稿"""
        if not filename:
            filename = self._generate_filename()
        filepath = os.path.join(self.ppts_dir, filename)
        prs = Presentation()
        return prs, filename

    def _save_presentation(self, prs: Presentation, filename: str) -> str:
        """保存演示文稿"""
        filepath = os.path.join(self.ppts_dir, filename)
        prs.save(filepath)
        return filepath

    def _create_presentation(self, filename: str = None) -> tuple[Presentation, str]:
        """创建或打开演示文稿"""
        if not filename:
            filename = self._generate_filename()
        filepath = os.path.join(self.ppts_dir, filename)
        if os.path.exists(filepath):
            return Presentation(filepath), filename
        return self._create_new_presentation(filename)

    def _add_slide(self, prs: Presentation, layout_name: str = "标题和内容") -> None:
        """添加新幻灯片"""
        layouts = {layout.name: layout for layout in prs.slide_layouts}
        layout = layouts.get(layout_name, prs.slide_layouts[1])
        return prs.slides.add_slide(layout)

    def _get_layout_by_name(self, prs: Presentation, layout_name: str) -> object:
        """根据名称获取布局"""
        # 常见的布局名称映射
        layout_mapping = {
            "标题": 0,  # 标题幻灯片
            "标题和内容": 1,  # 标题和内容
            "章节标题": 2,  # 章节标题
            "两栏内容": 3,  # 两栏内容
            "仅标题": 5,  # 仅标题
            "空白": 6   # 空白幻灯片
        }
        
        # 尝试按名称查找布局
        layouts = {layout.name: layout for layout in prs.slide_layouts}
        layout = layouts.get(layout_name)
        
        # 如果找不到，尝试使用映射的索引
        if not layout and layout_name in layout_mapping:
            index = layout_mapping[layout_name]
            if 0 <= index < len(prs.slide_layouts):
                layout = prs.slide_layouts[index]
        
        # 仍找不到，使用默认的标题和内容布局
        if not layout:
            layout = prs.slide_layouts[1]  # 标题和内容
            
        return layout

    def _add_text(self, slide, text: str, position: dict, style: dict) -> None:
        """添加文本"""
        left = Inches(position.get('left', 1))
        top = Inches(position.get('top', 1))
        width = Inches(position.get('width', 8))
        height = Inches(position.get('height', 2))

        textbox = slide.shapes.add_textbox(left, top, width, height)
        text_frame = textbox.text_frame
        text_frame.text = ""  # 清空默认文本

        # 处理多行文本，支持项目符号
        lines = text.split('\n')
        first = True
        for line in lines:
            if first:
                p = text_frame.paragraphs[0]
                first = False
            else:
                p = text_frame.add_paragraph()
            
            # 检查是否为项目符号行
            if line.strip().startswith('-') or line.strip().startswith('•'):
                p.level = 0
                p.text = line.strip()[1:].strip()  # 移除符号并清理空格
            elif line.strip().startswith('  -') or line.strip().startswith('  •'):
                p.level = 1
                p.text = line.strip()[3:].strip()  # 移除符号并清理空格
            else:
                p.text = line

            # 设置段落样式
            p.alignment = PP_ALIGN.CENTER if style.get('align') == 'center' else PP_ALIGN.LEFT
            
            # 设置字体
            font = p.font
            font.name = style.get('font', '微软雅黑')
            font.size = Pt(style.get('size', 18))
            
            # 设置颜色
            if 'color' in style:
                r, g, b = style['color']
                font.color.rgb = RGBColor(r, g, b)

    def _add_image(self, slide, image_path: str, position: dict) -> None:
        """添加图片"""
        left = Inches(position.get('left', 1))
        top = Inches(position.get('top', 1))
        width = Inches(position.get('width', 6))
        height = Inches(position.get('height', 4))
        
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            # 尝试在img目录查找
            img_dir = os.path.join(os.getcwd(), "img")
            alternative_path = os.path.join(img_dir, os.path.basename(image_path))
            if os.path.exists(alternative_path):
                image_path = alternative_path
            else:
                logger.warning(f"图片文件不存在: {image_path}")
                return
        
        slide.shapes.add_picture(image_path, left, top, width, height)

    def _set_background(self, slide, color: tuple) -> None:
        """设置背景颜色"""
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(*color)

    def _create_title_slide(self, prs: Presentation, title: str, subtitle: str = None) -> None:
        """创建标题幻灯片"""
        layout = self._get_layout_by_name(prs, "标题")
        slide = prs.slides.add_slide(layout)
        
        # 添加标题
        title_shape = slide.shapes.title
        title_shape.text = title
        
        # 添加副标题（如果有）
        if subtitle and slide.placeholders[1]:
            subtitle_shape = slide.placeholders[1]
            subtitle_shape.text = subtitle
        
        return slide

    def _create_content_slide(self, prs: Presentation, title: str, content: str, image_path: str = None) -> None:
        """创建内容幻灯片"""
        layout = self._get_layout_by_name(prs, "标题和内容")
        slide = prs.slides.add_slide(layout)
        
        # 添加标题
        title_shape = slide.shapes.title
        title_shape.text = title
        
        # 添加内容
        if hasattr(slide, 'placeholders') and len(slide.placeholders) > 1:
            content_shape = None
            for shape in slide.placeholders:
                if shape.placeholder_format.type == 1:  # 内容占位符
                    content_shape = shape
                    break
            
            if content_shape:
                tf = content_shape.text_frame
                tf.text = ""  # 清除默认文本
                
                # 处理多行内容
                lines = content.split('\n')
                first = True
                for line in lines:
                    if first:
                        p = tf.paragraphs[0]
                        first = False
                    else:
                        p = tf.add_paragraph()
                    
                    # 检查是否为项目符号行
                    if line.strip().startswith('-') or line.strip().startswith('•'):
                        p.level = 0
                        p.text = line.strip()[1:].strip()
                    elif line.strip().startswith('  -') or line.strip().startswith('  •'):
                        p.level = 1
                        p.text = line.strip()[3:].strip()
                    else:
                        p.text = line
        
        # 添加图片（如果有）
        if image_path:
            # 如果有图片，调整布局，把图片放在右侧
            position = {'left': 6, 'top': 2.5, 'width': 3.5, 'height': 3}
            self._add_image(slide, image_path, position)
        
        return slide

    def _batch_add_slides(self, prs: Presentation, slides_data: list) -> None:
        """批量添加幻灯片"""
        for slide_data in slides_data:
            slide_type = slide_data.get("type", "content")
            
            if slide_type == "title":
                self._create_title_slide(
                    prs, 
                    slide_data.get("title", ""), 
                    slide_data.get("subtitle", "")
                )
            elif slide_type == "content":
                self._create_content_slide(
                    prs, 
                    slide_data.get("title", ""), 
                    slide_data.get("content", ""),
                    slide_data.get("image_path")
                )
            elif slide_type == "custom":
                layout_name = slide_data.get("layout", "标题和内容")
                slide = self._add_slide(prs, layout_name)
                
                # 添加标题
                if "title" in slide_data and hasattr(slide, "shapes") and hasattr(slide.shapes, "title"):
                    slide.shapes.title.text = slide_data["title"]
                
                # 添加文本
                if "texts" in slide_data:
                    for text_data in slide_data["texts"]:
                        self._add_text(
                            slide,
                            text_data.get("content", ""),
                            text_data.get("position", {}),
                            text_data.get("style", {})
                        )
                
                # 添加图片
                if "images" in slide_data:
                    for image_data in slide_data["images"]:
                        self._add_image(
                            slide,
                            image_data.get("path", ""),
                            image_data.get("position", {})
                        )
                
                # 设置背景
                if "background_color" in slide_data:
                    self._set_background(slide, slide_data["background_color"])

    def _run(self, input_data: str) -> str:
        """处理添加PPT元素的命令"""
        try:
            from src.JarvisChain.models.llm_models import INTENT_MODEL
            from langchain.schema import SystemMessage, HumanMessage
            
            system_prompt = """你是一个PPT助手，负责将自然语言命令转换为结构化的JSON操作。输出时不要包含开头的"json"这个字符串。如果用户输入的
            指令中有image路径等信息，请调用add_image操作。
                支持的操作：
                - create: 创建新演示文稿
                - add_slide: 添加单个幻灯片
                - add_text: 添加文本
                - add_image: 添加图片
                - set_background: 设置背景
                - batch_add_slides: 批量添加多张幻灯片
                
                返回JSON格式：
                {
                    "operation": "操作名称",
                    "parameters": {
                        "filename": "文件名.pptx",
                        "element_type": "元素类型",
                        "content": "内容",
                        "position": {"left": 1, "top": 1, "width": 8, "height": 2},
                        "style": {
                            "font": "字体",
                            "size": 18,
                            "color": [255, 0, 0],
                            "align": "center"
                        },
                        "slides_data": [
                            {
                                "type": "title",
                                "title": "演示文稿标题",
                                "subtitle": "副标题"
                            },
                            {
                                "type": "content",
                                "title": "幻灯片标题",
                                "content": "幻灯片内容，可以包含多行和项目符号",
                                "image_path": "图片路径"
                            },
                            {
                                "type": "custom",
                                "layout": "布局名称",
                                "title": "幻灯片标题",
                                "texts": [
                                    {
                                        "content": "文本内容",
                                        "position": {"left": 1, "top": 1, "width": 8, "height": 2},
                                        "style": {"font": "字体", "size": 18, "color": [255, 0, 0], "align": "center"}
                                    }
                                ],
                                "images": [
                                    {
                                        "path": "图片路径",
                                        "position": {"left": 1, "top": 1, "width": 6, "height": 4}
                                    }
                                ],
                                "background_color": [255, 255, 255]
                            }
                        ]
                    }
                }
                
                重要：1.按照示例给出json文件，根据情况，可以给出默认值。
                2.filename必须给出
                3.如果没有slides_data，则给出5页的默认数据"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=input_data)
            ]
            response = INTENT_MODEL.invoke(messages)
            response_text = response.content
            if response_text.startswith("```json"):
                response_text = "" + response_text[7:]
            response_text = response_text.rstrip("```")
            print(f"************PPT工具的大模型输出：{response_text}**********************")
            
            try:
                if not response_text or not response_text.strip():
                    raise ValueError("模型返回了空响应")
                
                # 处理多个JSON对象
                json_objects = []
                current_pos = 0
                while current_pos < len(response_text):
                    try:
                        # 找到下一个JSON对象的开始位置
                        start_pos = response_text.find('{', current_pos)
                        if start_pos == -1:
                            break
                            
                        # 找到匹配的结束括号
                        bracket_count = 0
                        end_pos = start_pos
                        for i in range(start_pos, len(response_text)):
                            if response_text[i] == '{':
                                bracket_count += 1
                            elif response_text[i] == '}':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    end_pos = i + 1
                                    break
                        
                        if bracket_count != 0:
                            raise ValueError("JSON对象括号不匹配")
                            
                        # 解析当前JSON对象
                        json_str = response_text[start_pos:end_pos]
                        json_obj = json.loads(json_str)
                        json_objects.append(json_obj)
                        
                        current_pos = end_pos
                    except json.JSONDecodeError as e:
                        logger.error(f"解析JSON对象时出错: {str(e)}")
                        current_pos += 1
                
                if not json_objects:
                    raise ValueError("没有找到有效的JSON对象")
                
                # 处理第一个JSON对象（创建PPT）
                operation_json = json_objects[0]
                operation = operation_json.get("operation")
                parameters = operation_json.get("parameters", {})
                
                # 执行创建操作
                if operation == "create":
                    prs, filename = self._create_new_presentation(parameters.get("filename"))
                else:
                    prs, filename = self._create_presentation(parameters.get("filename"))
                
                # 处理后续的JSON对象（添加内容）
                for json_obj in json_objects[1:]:
                    operation = json_obj.get("operation")
                    parameters = json_obj.get("parameters", {})
                    
                    if operation == "add_slide":
                        layout = parameters.get("layout", "标题和内容")
                        self._add_slide(prs, layout)
                    elif operation == "add_text":
                        slide = prs.slides[-1] if prs.slides else self._add_slide(prs, "标题和内容")
                        self._add_text(slide, parameters["content"], 
                                     parameters.get("position", {}),
                                     parameters.get("style", {}))
                    elif operation == "add_image":
                        slide = prs.slides[-1] if prs.slides else self._add_slide(prs, "标题和内容")
                        self._add_image(slide, parameters["image_path"],
                                      parameters.get("position", {}))
                    elif operation == "set_background":
                        slide = prs.slides[-1] if prs.slides else self._add_slide(prs, "标题和内容")
                        self._set_background(slide, parameters["color"])
                    elif operation == "batch_add_slides":
                        self._batch_add_slides(prs, parameters.get("slides_data", []))
                
                # 保存演示文稿
                filepath = self._save_presentation(prs, filename)
                
                return json.dumps({
                    "success": True,
                    "operation": "batch_operations",
                    "message": f"成功执行多个操作",
                    "filepath": filepath,
                    "filename": filename
                })
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"无法解析模型响应为JSON: {str(e)}")
                logger.error(f"原始响应内容: {response_text}")
                # 如果没有当前PPT，则创建新的
                if not self.current_presentation:
                    operation_json = {
                        "operation": "create",
                        "parameters": {"filename": self._generate_filename()}
                    }
                else:
                    # 如果有当前PPT，则添加新幻灯片
                    operation_json = {
                        "operation": "add_slide",
                        "parameters": {"layout": "标题和内容"}
                    }
            
            # 执行操作
            operation = operation_json.get("operation")
            parameters = operation_json.get("parameters", {})
            
            # 执行操作
            if operation == "create":
                prs, filename = self._create_new_presentation(parameters.get("filename"))
            else:
                prs, filename = self._create_presentation(parameters.get("filename"))
            
            if operation == "add_slide":
                layout = parameters.get("layout", "标题和内容")
                self._add_slide(prs, layout)
            elif operation == "add_text":
                slide = prs.slides[-1] if prs.slides else self._add_slide(prs, "标题和内容")
                self._add_text(slide, parameters["content"], 
                             parameters.get("position", {}),
                             parameters.get("style", {}))
            elif operation == "add_image":
                slide = prs.slides[-1] if prs.slides else self._add_slide(prs, "标题和内容")
                self._add_image(slide, parameters["image_path"],
                              parameters.get("position", {}))
            elif operation == "set_background":
                slide = prs.slides[-1] if prs.slides else self._add_slide(prs, "标题和内容")
                self._set_background(slide, parameters["color"])
            elif operation == "batch_add_slides":
                self._batch_add_slides(prs, parameters.get("slides_data", []))
            
            # 保存演示文稿
            filepath = self._save_presentation(prs, filename)
            
            return json.dumps({
                "success": True,
                "operation": operation,
                "message": f"成功执行{operation}操作",
                "filepath": filepath,
                "filename": filename
            })

        except Exception as e:
            logger.error(f"PPT添加工具错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return json.dumps({
                "success": False,
                "message": f"错误: {str(e)}"
            })

    async def _arun(self, input_data: str) -> str:
        return self._run(input_data) 