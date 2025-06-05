#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit PPT生成器启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """检查依赖包"""
    required_packages = [
        ('streamlit', 'streamlit'),
        ('python-dotenv', 'dotenv'),
        ('asyncio', 'asyncio')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 请安装缺少的包:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_environment():
    """检查环境变量"""
    required_env = ['YUNWU_API_KEY']
    optional_env = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    
    print("🔍 检查环境变量配置...")
    
    # 检查必需的环境变量
    missing_required = []
    for env_var in required_env:
        if not os.getenv(env_var):
            missing_required.append(env_var)
    
    if missing_required:
        print("❌ 缺少必需的环境变量:")
        for env_var in missing_required:
            print(f"   - {env_var}")
        print("\n💡 请在 .env 文件中配置或设置环境变量")
        return False
    
    print("✅ 必需环境变量配置正确")
    
    # 检查可选的环境变量
    for env_var in optional_env:
        if os.getenv(env_var):
            print(f"✅ {env_var} 已配置")
        else:
            print(f"⚠️ {env_var} 未配置 (可选)")
    
    return True

def main():
    """主启动函数"""
    print("🎯 启动 Streamlit PPT生成器")
    print("=" * 50)
    
    # 检查依赖
    print("📦 检查依赖包...")
    if not check_requirements():
        return 1
    print("✅ 依赖包检查通过")
    
    # 检查环境变量
    if not check_environment():
        return 1
    
    # 检查应用文件
    app_file = Path("streamlit_ppt_app.py")
    if not app_file.exists():
        print(f"❌ 找不到应用文件: {app_file}")
        return 1
    
    print("✅ 环境检查完成")
    print("\n🚀 启动 Streamlit 应用...")
    print("-" * 50)
    print("💡 应用将在浏览器中自动打开")
    print("💡 如果没有自动打开，请访问: http://localhost:8501")
    print("💡 按 Ctrl+C 停止应用")
    print("-" * 50)
    
    try:
        # 启动 Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            str(app_file),
            "--server.address", "localhost",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false"
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 