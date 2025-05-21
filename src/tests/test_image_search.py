import asyncio
from src.tools.image_search_tool import ImageSearchTool
import os

async def test_image_search():
    """测试图片搜索功能"""
    print("\n=== 图片搜索测试 ===")
    
    # 创建图片搜索工具实例
    image_tool = ImageSearchTool()
    
    while True:
        # 获取用户输入
        query = input("\n请输入要搜索的图片关键词（输入'q'退出）: ")
        
        if query.lower() == 'q':
            print("测试结束")
            break
            
        if not query.strip():
            print("关键词不能为空，请重新输入")
            continue
            
        print(f"\n正在搜索: {query}")
        
        try:
            # 执行图片搜索
            result = await image_tool._arun(query)
            print(f"\n搜索结果: {result}")
            
            # 显示保存的图片数量
            img_dir = os.path.join(os.getcwd(), "img")
            if os.path.exists(img_dir):
                saved_images = [f for f in os.listdir(img_dir) if f.startswith("image_")]
                print(f"\n当前img目录中共有 {len(saved_images)} 张图片")
                
        except Exception as e:
            print(f"\n搜索过程中发生错误: {str(e)}")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_image_search()) 