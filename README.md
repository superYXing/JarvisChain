# J-A-R-V-I-S 数字分身助手


J-A-R-V-I-S是一个基于人工智能的通用数字分身助手，专为打工人设计。它能够帮助用户处理各种工作任务，包括但不限于PPT制作、文案创作、报告生成、与领导沟通等。该助手集成了多种智能工具，提供直观的交互体验和专业的建议。

## 🚀 主要功能

- **🧠 智能任务处理**：自动分析用户需求，选择合适的处理方式
- **📊 PPT制作**：支持创建、编辑、美化演示文稿
- **🧠 长期记忆**：保存用户历史交互信息，提供个性化服务
- **👤 用户画像**：记录用户偏好和习惯，优化服务体验
- **🤖 多Agent协作**：主Agent协调多个专业Agent完成复杂任务
- **🔄 错误恢复**：智能处理异常情况，确保服务连续性
- **⚡ 自主迭代**：类似LangChain Agent的自主思考和决策机制

## 🏗️ 技术架构

- **语言**: Python 3.9+
- **AI框架**: LangChain
- **包管理**: uv (现代化的Python包管理器)
- **异步编程**: asyncio
- **向量数据库**: ChromaDB
- **Web框架**: FastAPI
- **文档处理**: python-pptx, python-docx
- **代码质量**: Black, isort, Ruff, mypy

## 📦 uv 包管理器完整使用教程



### 🚀 快速开始

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/JarvisChain.git
cd JarvisChain
```

#### 2. 创建虚拟环境

```bash
# uv 会自动检测 Python 版本要求并创建虚拟环境
uv venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

#### 3. 安装依赖

```bash
# 安装项目依赖
uv pip install -e .

# 或者直接同步所有依赖（推荐）
uv sync
```

#### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入必要的配置信息
# 需要配置的主要变量：
# OPENAI_API_KEY=your_openai_api_key
# TAVILY_API_KEY=your_tavily_api_key
```

#### 5. 运行项目

```bash
# 使用 uv 运行
uv run python src/JarvisChain/main.py

# 或者在激活的虚拟环境中运行
python src/JarvisChain/main.py
```


## 🚀 使用方法

### 基本使用

1. **启动程序**：
```bash
uv run python src/JarvisChain/main.py
```

2. **交互方式**：
- 直接输入您的需求，例如：
  - "帮我写一份周报"
  - "创建一个项目演示PPT"
  - "帮我回复领导的邮件"
  - "分析这个外包项目的可行性"
- 按照助手的提示进行操作
- 输入'exit'结束对话

### 高级功能

#### 自主迭代执行
系统支持最大10轮自主迭代，能够：
- 自主思考和分析当前情况
- 制定执行计划
- 执行具体行动
- 观察结果并调整策略
- 判断任务完成状态

#### 短期记忆机制
- 保存最近10轮对话历史
- 支持上下文感知的决策
- 提供连贯的任务执行体验

## 📁 项目结构

```
JarvisChain/
├── src/
│   └── JarvisChain/
│       ├── main.py              # 主程序入口文件
│       ├── agents/              # AI代理模块
│       │   ├── base_agent.py    # 基础代理类定义
│       │   ├── master_agent.py  # 主控代理实现
│       │   └── ppt_agent.py     # PPT专用代理实现
│       ├── models/              # AI模型相关代码
│       ├── tools/               # 工具集模块
│       │   ├── ppt_tools/       # PPT相关工具集
│       │   ├── doc_tools/       # 文档处理工具集
│       │   ├── comm_tools/      # 沟通工具集
│       │   └── project_tools/   # 项目管理工具集
│       ├── utils/               # 工具函数模块
│       │   ├── logger.py        # 日志记录工具
│       │   ├── memory_manager.py # 记忆管理系统
│       │   └── user_profile.py  # 用户画像管理
│       ├── config/              # 配置管理
│       ├── database/            # 数据库相关
│       └── memory/              # 记忆系统
├── tests/                       # 测试用例目录
├── docs/                        # 文档存储目录
├── logs/                        # 日志文件目录
├── pyproject.toml              # 项目配置和依赖管理
├── uv.lock                     # uv 锁文件
├── .python-version             # Python 版本固定
├── .env.example                # 环境变量模板
└── README.md                   # 项目说明文档
```

## 🔧 开发指南

### 环境要求

- Python 3.9+
- uv 包管理器
- OpenAI API Key
- Tavily API Key（用于图片搜索）


**让AI助手成为您工作中的得力伙伴！** 🚀


