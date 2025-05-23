# J-A-R-V-I-S 数字分身助手

J-A-R-V-I-S是一个基于人工智能的通用数字分身助手，专为打工人设计。它能够帮助用户处理各种工作任务，包括但不限于PPT制作、文案创作、报告生成、与领导沟通等。该助手集成了多种智能工具，提供直观的交互体验和专业的建议。

## 主要功能

- **智能任务处理**：自动分析用户需求，选择合适的处理方式
- **PPT制作**：支持创建、编辑、美化演示文稿
- **长期记忆**：保存用户历史交互信息，提供个性化服务
- **用户画像**：记录用户偏好和习惯，优化服务体验
- **多Agent协作**：主Agent协调多个专业Agent完成复杂任务
- **错误恢复**：智能处理异常情况，确保服务连续性

## 技术架构

- 基于Python 3.9开发
- 使用LangChain框架构建AI代理系统
- 采用异步编程模式提高性能
- 集成多种专业工具和API
- 包含完整的日志记录系统
- 支持多种文档格式处理
- 使用向量数据库存储长期记忆

## 安装说明

### 环境要求
- Python 3.9+
- uv包管理器

### 安装步骤

1. 克隆项目仓库：
```bash
git clone https://github.com/yourusername/JarvisChain.git
cd JarvisChain
```

2. 使用uv安装依赖包：
```bash
uv venv
uv pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，填入必要的配置信息
```

## 使用方法

1. 启动程序：
```bash
python src/JarvisChain/main.py
```

2. 交互方式：
- 直接输入您的需求，例如：
  - "帮我写一份周报"
  - "创建一个项目演示PPT"
  - "帮我回复领导的邮件"
  - "分析这个外包项目的可行性"
- 按照助手的提示进行操作
- 输入'exit'结束对话

## 项目结构
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
│       └── tests/               # 测试用例目录
├── logs/                        # 日志文件目录
├── docs/                        # 文档存储目录
├── requirements.txt             # 项目依赖清单
└── README.md                    # 项目说明文档
```


