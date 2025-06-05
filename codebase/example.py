import os, io, requests
from typing import Optional
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE, MSO_ANCHOR
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
IMAGE_DIR = "ppt_images_cache"
PPT_SAVE_DIR = "ppts"
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(PPT_SAVE_DIR, exist_ok=True)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

# 颜色定义
COLOR_WHITE, COLOR_BLACK = RGBColor(255, 255, 255), RGBColor(0, 0, 0)
COLOR_BLUE, COLOR_RED = RGBColor(0, 78, 152), RGBColor(204, 0, 0)
COLOR_GREEN, COLOR_ORANGE = RGBColor(0, 153, 76), RGBColor(255, 136, 0)
COLOR_PURPLE, COLOR_GRAY = RGBColor(102, 0, 153), RGBColor(68, 68, 68)
COLOR_LIGHT_GRAY = RGBColor(240, 240, 240)
COLOR_YELLOW = RGBColor(255, 215, 0)

def search_and_download_image(query: str, filename: str, search_online=True) -> Optional[str]:
    """搜索并下载图片"""
    try:
        if not search_online or not tavily_client:
            return None
        
        local_path = os.path.join(IMAGE_DIR, filename)
        if os.path.exists(local_path):
            return local_path

        results = tavily_client.search(query=query, include_images=True, max_results=3)
        image_urls = results.get("images", [])
        
        if not image_urls:
            print(f"未找到图片: {query}")
            return None

        for url in image_urls[:2]:  # 只尝试前2个URL
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                res = requests.get(url, timeout=10, headers=headers)
                res.raise_for_status()
                
                img = Image.open(io.BytesIO(res.content))
                if img.width < 300 or img.height < 200:
                    continue
                    
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img.save(local_path, 'JPEG', quality=85)
                print(f"图片下载成功: {local_path}")
                return local_path
            except Exception as e:
                print(f"下载失败: {url}, 错误: {e}")
                continue
                
        print(f"所有图片下载失败: {query}")
    except Exception as e:
        print(f"搜索图片错误: {e}")
    return None

def create_ppt_example():
    """创建示例PPT"""
    prs = Presentation()
    prs.slide_width = Inches(16)
    prs.slide_height = Inches(9)

    def set_background_color(slide, color):
        """设置背景色"""
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = color

    def add_title_slide(title_text, subtitle_text, image_query):
        """添加标题页"""
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        set_background_color(slide, COLOR_BLUE)

        # 添加背景图片
        img_path = search_and_download_image(image_query, "title_bg.jpg")
        if img_path:
            pic = slide.shapes.add_picture(img_path, Inches(0), Inches(0), 
                                         width=prs.slide_width, height=prs.slide_height)
            slide.shapes._spTree.insert(2, pic._element)

        # 主标题
        title_shape = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(14), Inches(2))
        title_frame = title_shape.text_frame
        title_frame.text = title_text
        p = title_frame.paragraphs[0]
        p.font.name = 'Arial Black'
        p.font.size = Pt(64)
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.CENTER

        # 副标题
        subtitle_shape = slide.shapes.add_textbox(Inches(1), Inches(4.5), Inches(14), Inches(1.5))
        subtitle_frame = subtitle_shape.text_frame
        subtitle_frame.text = subtitle_text
        p = subtitle_frame.paragraphs[0]
        p.font.name = 'Arial'
        p.font.size = Pt(32)
        p.font.color.rgb = COLOR_YELLOW
        p.alignment = PP_ALIGN.CENTER

    def add_content_slide(title_text, content_points, image_query, image_filename, image_left=False):
        """添加内容页"""
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        bg_color = COLOR_LIGHT_GRAY if not image_left else COLOR_ORANGE
        set_background_color(slide, bg_color)

        # 标题
        title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(15), Inches(1))
        title_frame = title_shape.text_frame
        title_frame.text = title_text
        p = title_frame.paragraphs[0]
        p.font.name = 'Arial Black'
        p.font.size = Pt(36)
        p.font.color.rgb = COLOR_WHITE if image_left else COLOR_BLUE
        p.alignment = PP_ALIGN.LEFT

        # 图片位置
        img_path = search_and_download_image(image_query, image_filename)
        if img_path:
            pic_width = Inches(6.5)
            pic_height = Inches(6)
            if image_left:
                left = Inches(0.5)
                content_left = Inches(7.5)
            else:
                left = prs.slide_width - pic_width - Inches(0.5)
                content_left = Inches(0.7)
            
            top = Inches(1.5)
            slide.shapes.add_picture(img_path, left, top, width=pic_width, height=pic_height)
        else:
            content_left = Inches(0.7)

        # 内容文本
        content_width = Inches(7.5) if img_path else Inches(14.5)
        content_shape = slide.shapes.add_textbox(content_left, Inches(1.5), content_width, Inches(6.5))
        tf = content_shape.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        
        for point in content_points:
            p = tf.add_paragraph()
            p.text = point
            p.font.name = 'Arial'
            p.font.size = Pt(24)
            p.font.color.rgb = COLOR_WHITE if image_left else COLOR_BLACK
            p.level = 0
            p.space_before = Pt(8)

    def add_image_overlay_slide(image_query, image_filename, overlay_text):
        """添加图片覆盖文字页"""
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        set_background_color(slide, COLOR_PURPLE)

        # 全屏背景图
        img_path = search_and_download_image(image_query, image_filename)
        if img_path:
            pic = slide.shapes.add_picture(img_path, Inches(0), Inches(0), 
                                         width=prs.slide_width, height=prs.slide_height)
            slide.shapes._spTree.insert(2, pic._element)
        
        # 文字覆盖
        overlay_box = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(14), Inches(3))
        tf = overlay_box.text_frame
        p = tf.paragraphs[0]
        p.text = overlay_text
        p.font.name = 'Arial Black'
        p.font.size = Pt(52)
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.CENTER
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    def add_conclusion_slide(main_text, sub_text, image_query):
        """添加结论页"""
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        set_background_color(slide, COLOR_GREEN)

        # 背景图片
        img_path = search_and_download_image(image_query, "conclusion_bg.jpg")
        if img_path:
            pic = slide.shapes.add_picture(img_path, Inches(0), Inches(0), 
                                         width=prs.slide_width, height=prs.slide_height)
            slide.shapes._spTree.insert(2, pic._element)
            
            # 半透明遮罩
            overlay = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), 
                                           prs.slide_width, prs.slide_height)
            fill = overlay.fill
            fill.solid()
            fill.fore_color.rgb = COLOR_BLACK
            fill.transparency = 0.5
            overlay.line.fill.background()
            slide.shapes._spTree.insert(3, overlay._element)

        # 主文字
        title_shape = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(14), Inches(2))
        title_frame = title_shape.text_frame
        title_frame.text = main_text
        p = title_frame.paragraphs[0]
        p.font.name = 'Arial Black'
        p.font.size = Pt(56)
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.CENTER
        
        # 副文字
        subtitle_shape = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(14), Inches(1.5))
        subtitle_frame = subtitle_shape.text_frame
        subtitle_frame.text = sub_text
        p = subtitle_frame.paragraphs[0]
        p.font.name = 'Arial'
        p.font.size = Pt(28)
        p.font.color.rgb = COLOR_YELLOW
        p.alignment = PP_ALIGN.CENTER

    # 生成PPT内容
    
    # 第1页：标题页
    add_title_slide(
        "人工智能时代",
        "探索AI技术的无限可能",
        "artificial intelligence future technology"
    )

    # 第2页：内容页（图片在右）
    add_content_slide(
        "AI技术发展",
        [
            "机器学习算法不断优化升级",
            "深度学习在各领域广泛应用", 
            "自然语言处理技术日趋成熟",
            "计算机视觉识别精度持续提升"
        ],
        "machine learning artificial intelligence",
        "ai_development.jpg",
        image_left=False
    )

    # 第3页：内容页（图片在左）
    add_content_slide(
        "AI应用场景",
        [
            "智能客服提升用户体验",
            "自动驾驶改变出行方式",
            "医疗诊断辅助精准治疗",
            "智能制造优化生产效率",
            "教育个性化学习方案"
        ],
        "AI applications smart city",
        "ai_applications.jpg", 
        image_left=True
    )

    # 第4页：图片覆盖页
    add_image_overlay_slide(
        "future technology innovation",
        "ai_future.jpg",
        "AI驱动未来创新"
    )

    # 第5页：结论页
    add_conclusion_slide(
        "拥抱AI时代",
        "让科技为美好生活赋能",
        "technology future bright"
    )

    # 保存PPT
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ppt_filename = os.path.join(PPT_SAVE_DIR, f"AI主题PPT_{timestamp}.pptx")
    prs.save(ppt_filename)
    print(f"PPT已保存: {ppt_filename}")

if __name__ == '__main__':
    if not TAVILY_API_KEY:
        print("未设置TAVILY_API_KEY，将跳过图片搜索功能")
    create_ppt_example()
