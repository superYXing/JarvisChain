#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT可视化渲染器 - 将PPT转换为图片以供视觉语言模型分析
"""

import os
import platform
import subprocess
from typing import List, Optional, Dict, Any
from PIL import Image
import base64
import io
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('ppt_visual_renderer')

class PPTVisualRenderer:
    """PPT可视化渲染器，将PPT转换为图片"""
    
    def __init__(self):
        self.render_method = self._detect_render_method()
        self.temp_dir = os.path.join(os.getcwd(), "temp", "ppt_renders")
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def _detect_render_method(self) -> str:
        """检测可用的渲染方法"""
        system = platform.system()
        
        if system == "Windows":
            # Windows系统，尝试使用PowerPoint COM对象
            try:
                import win32com.client
                logger.info("✅ 检测到Windows系统，将使用PowerPoint COM对象渲染")
                return "powerpoint_com"
            except ImportError:
                logger.warning("⚠️ Windows系统但未安装pywin32，将使用备选方案")
                
        
        
        # 默认使用python-pptx截图方法（功能有限）
        logger.warning("⚠️ 未找到合适的PPT渲染方法，将使用基础截图")
        return "basic_screenshot"
    
    def _check_command_exists(self, command: str) -> bool:
        """检查命令是否存在"""
        try:
            subprocess.run([command, "--version"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def render_ppt_to_images(self, ppt_path: str, output_dir: Optional[str] = None) -> List[str]:
        """将PPT渲染为图片列表"""
        if not os.path.exists(ppt_path):
            logger.error(f"PPT文件不存在: {ppt_path}")
            return []
        
        if output_dir is None:
            output_dir = os.path.join(self.temp_dir, 
                                    os.path.splitext(os.path.basename(ppt_path))[0])
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 根据渲染方法选择相应的实现
        if self.render_method == "powerpoint_com":
            return self._render_with_powerpoint(ppt_path, output_dir)
        elif self.render_method == "libreoffice":
            return self._render_with_libreoffice(ppt_path, output_dir)
        else:
            return self._render_basic_screenshot(ppt_path, output_dir)
    
    def _render_with_powerpoint(self, ppt_path: str, output_dir: str) -> List[str]:
        """使用PowerPoint COM对象渲染（Windows）"""
        try:
            import win32com.client
            
            logger.info("使用PowerPoint COM对象渲染PPT")
            
            # 创建PowerPoint应用实例
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            powerpoint.Visible = True
            
            # 打开PPT文件
            presentation = powerpoint.Presentations.Open(os.path.abspath(ppt_path))
            
            image_paths = []
            
            # 导出每一页为图片
            for i, slide in enumerate(presentation.Slides, 1):
                image_path = os.path.join(output_dir, f"slide_{i:03d}.png")
                slide.Export(image_path, "PNG", 1920, 1080)
                image_paths.append(image_path)
                logger.info(f"✅ 导出第 {i} 页: {image_path}")
            
            # 关闭演示文稿
            presentation.Close()
            powerpoint.Quit()
            
            return image_paths
            
        except Exception as e:
            logger.error(f"PowerPoint渲染失败: {str(e)}")
            return []
    
    def _render_with_libreoffice(self, ppt_path: str, output_dir: str) -> List[str]:
        """使用LibreOffice渲染"""
        try:
            logger.info("使用LibreOffice渲染PPT")
            
            # 先转换为PDF
            pdf_path = os.path.join(output_dir, "presentation.pdf")
            cmd = [
                "libreoffice", 
                "--headless", 
                "--convert-to", "pdf",
                "--outdir", output_dir,
                ppt_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"LibreOffice转换失败: {result.stderr}")
                return []
            
            # 使用pdf2image或类似工具将PDF转换为图片
            try:
                from pdf2image import convert_from_path
                
                images = convert_from_path(pdf_path, dpi=150)
                image_paths = []
                
                for i, image in enumerate(images, 1):
                    image_path = os.path.join(output_dir, f"slide_{i:03d}.png")
                    image.save(image_path, "PNG")
                    image_paths.append(image_path)
                    logger.info(f"✅ 导出第 {i} 页: {image_path}")
                
                # 删除临时PDF文件
                os.remove(pdf_path)
                
                return image_paths
                
            except ImportError:
                logger.error("需要安装pdf2image库: pip install pdf2image")
                return []
                
        except Exception as e:
            logger.error(f"LibreOffice渲染失败: {str(e)}")
            return []
    
    def _render_basic_screenshot(self, ppt_path: str, output_dir: str) -> List[str]:
        """基础截图方法（使用python-pptx创建预览）"""
        try:
            from pptx import Presentation
            
            logger.info("使用基础方法创建PPT预览")
            
            prs = Presentation(ppt_path)
            image_paths = []
            
            for i, slide in enumerate(prs.slides, 1):
                # 创建预览图片（简化版本）
                img = Image.new('RGB', (1920, 1080), color='white')
                
                # 这里可以添加更复杂的渲染逻辑
                # 暂时只创建空白图片作为占位符
                
                image_path = os.path.join(output_dir, f"slide_{i:03d}_preview.png")
                img.save(image_path)
                image_paths.append(image_path)
                
                logger.warning(f"⚠️ 第 {i} 页使用基础预览（功能有限）")
            
            return image_paths
            
        except Exception as e:
            logger.error(f"基础截图失败: {str(e)}")
            return []
    
    def get_slide_image_base64(self, ppt_path: str, slide_number: int) -> Optional[str]:
        """获取指定幻灯片的Base64编码图片"""
        try:
            # 先渲染所有图片
            image_paths = self.render_ppt_to_images(ppt_path)
            
            if slide_number < 1 or slide_number > len(image_paths):
                logger.error(f"幻灯片编号超出范围: {slide_number}")
                return None
            
            image_path = image_paths[slide_number - 1]
            
            # 读取图片并转换为Base64
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
                base64_data = base64.b64encode(img_data).decode('utf-8')
                
            return f"data:image/png;base64,{base64_data}"
            
        except Exception as e:
            logger.error(f"获取幻灯片Base64失败: {str(e)}")
            return None
    
    def prepare_images_for_vlm(self, ppt_path: str, max_slides: int = 10) -> List[Dict[str, Any]]:
        """准备图片供视觉语言模型分析"""
        try:
            logger.info(f"准备PPT图片供VLM分析，最多 {max_slides} 页")
            
            # 渲染PPT为图片
            image_paths = self.render_ppt_to_images(ppt_path)
            
            if not image_paths:
                logger.error("无法渲染PPT图片")
                return []
            
            # 限制数量
            image_paths = image_paths[:max_slides]
            
            vlm_images = []
            
            for i, image_path in enumerate(image_paths, 1):
                # 压缩图片以减少传输大小
                img = Image.open(image_path)
                
                # 如果图片太大，调整大小
                max_size = (1280, 720)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 转换为Base64
                buffered = io.BytesIO()
                img.save(buffered, format="PNG", optimize=True)
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                vlm_images.append({
                    "slide_number": i,
                    "image_base64": f"data:image/png;base64,{img_base64}",
                    "width": img.width,
                    "height": img.height
                })
                
                logger.info(f"✅ 准备第 {i} 页图片 ({img.width}x{img.height})")
            
            return vlm_images
            
        except Exception as e:
            logger.error(f"准备VLM图片失败: {str(e)}")
            return []
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info("✅ 清理临时渲染文件")
        except Exception as e:
            logger.error(f"清理临时文件失败: {str(e)}") 