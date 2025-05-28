# uv 包管理器快速参考

## 🚀 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 使用 pip
pip install uv

# 使用 Homebrew (macOS)
brew install uv
```

## 📦 项目管理

### 初始化项目
```bash
# 创建新项目
uv init my-project
uv init --lib my-library  # 创建库项目

# 在现有目录初始化
uv init
```

### 虚拟环境管理
```bash
# 创建虚拟环境
uv venv

# 指定 Python 版本
uv venv --python 3.11

# 创建命名虚拟环境
uv venv my-env

# 删除虚拟环境
rm -rf .venv
```

## 📋 依赖管理

### 添加依赖
```bash
# 添加运行时依赖
uv add requests
uv add "django>=4.0"

# 添加开发依赖
uv add --dev pytest black

# 添加可选依赖组
uv add --optional docs mkdocs

# 从 requirements.txt 添加
uv add -r requirements.txt

# 从 Git 仓库添加
uv add git+https://github.com/user/repo.git

# 从本地路径添加
uv add --editable ./local-package
```

### 移除依赖
```bash
# 移除依赖
uv remove requests

# 移除开发依赖
uv remove --dev pytest
```

### 更新依赖
```bash
# 更新所有依赖
uv lock --upgrade

# 更新特定依赖
uv lock --upgrade-package requests

# 同步更新后的依赖
uv sync
```

## 🔄 同步和安装

### 同步依赖
```bash
# 同步所有依赖
uv sync

# 仅同步生产依赖
uv sync --no-dev

# 同步包含可选依赖
uv sync --extra docs

# 同步所有可选依赖
uv sync --all-extras
```

### 直接安装
```bash
# 安装到当前环境
uv pip install requests

# 从 requirements.txt 安装
uv pip install -r requirements.txt

# 安装项目（可编辑模式）
uv pip install -e .
```

## 🏃 运行命令

### 在虚拟环境中运行
```bash
# 运行 Python 脚本
uv run python script.py

# 运行模块
uv run -m pytest

# 运行项目脚本（pyproject.toml 中定义）
uv run my-script

# 运行任意命令
uv run black .
uv run pytest
```

## 🔒 锁文件管理

### 生成和使用锁文件
```bash
# 生成锁文件
uv lock

# 从锁文件安装
uv sync

# 检查锁文件是否最新
uv lock --check

# 更新锁文件
uv lock --upgrade
```

## 🛠️ 构建和发布

### 构建项目
```bash
# 构建 wheel 和 sdist
uv build

# 仅构建 wheel
uv build --wheel

# 仅构建 sdist
uv build --sdist
```

### 发布到 PyPI
```bash
# 发布到 PyPI
uv publish

# 发布到测试 PyPI
uv publish --repository testpypi

# 使用令牌发布
uv publish --token $PYPI_TOKEN
```

## 🔍 信息查询

### 查看项目信息
```bash
# 查看依赖树
uv tree

# 查看过时的依赖
uv pip list --outdated

# 查看已安装的包
uv pip list

# 显示包信息
uv pip show requests
```

## ⚙️ 配置

### 环境变量
```bash
# 设置缓存目录
export UV_CACHE_DIR=/path/to/cache

# 设置 PyPI 镜像
export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/

# 禁用网络访问
export UV_OFFLINE=1

# 设置并发数
export UV_CONCURRENT_DOWNLOADS=10
```

### 配置文件
```toml
# pyproject.toml
[tool.uv]
dev-dependencies = [
    "pytest>=7.0.0",
    "black>=23.0.0",
]

[tool.uv.sources]
# 从 Git 安装
my-package = { git = "https://github.com/user/repo.git" }
# 从本地路径安装
local-package = { path = "../local-package" }
```

## 🚨 故障排除

### 常见问题
```bash
# 清理缓存
uv cache clean

# 重新生成锁文件
rm uv.lock && uv lock

# 重新创建虚拟环境
rm -rf .venv && uv venv && uv sync

# 检查依赖冲突
uv pip check

# 详细输出
uv --verbose sync
```

### 调试选项
```bash
# 显示详细信息
uv --verbose command

# 显示调试信息
uv --debug command

# 静默模式
uv --quiet command
```

## 📊 性能对比

| 操作 | pip | uv | 提升 |
|------|-----|----|----- |
| 依赖解析 | 慢 | 快 | 10-100x |
| 包安装 | 中等 | 快 | 2-10x |
| 缓存效率 | 低 | 高 | 显著 |
| 锁文件 | 需要 pip-tools | 内置 | 更简单 |

## 🔗 有用链接

- [uv 官方文档](https://docs.astral.sh/uv/)
- [uv GitHub 仓库](https://github.com/astral-sh/uv)
- [从 pip 迁移指南](https://docs.astral.sh/uv/pip/)
- [pyproject.toml 规范](https://peps.python.org/pep-0621/)

## 💡 最佳实践

1. **始终使用锁文件**: 确保可重现的构建
2. **分离开发和生产依赖**: 使用 `--dev` 标志
3. **使用虚拟环境**: 避免全局包污染
4. **定期更新依赖**: 保持安全性和兼容性
5. **使用 pre-commit**: 自动化代码质量检查
6. **配置 CI/CD**: 在持续集成中使用 uv 