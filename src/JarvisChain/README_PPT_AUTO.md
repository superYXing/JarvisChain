# 自动PPT生成系统

## 功能概述

优化后的PPT生成系统支持**自动任务处理**和**短期记忆管理**，能够：

1. 🧠 **短期记忆管理**：自动记录任务状态、步骤进度和历史记录
2. 🤖 **自动任务处理**：接收外部任务后自动完成整个PPT生成流程
3. 📊 **进度监控**：实时查看任务状态和完成进度
4. 📁 **文件管理**：自动整理生成的PPT文件，准备发送给用户
5. 🔄 **连续执行**：一次性完成大纲生成→代码生成→执行→文件整理全流程

## 核心组件

### 1. ShortTermMemory (短期记忆)
```python
memory = ShortTermMemory()

# 创建任务
task = memory.create_task("task-001", "制作AI主题PPT")

# 添加步骤
memory.add_task_step("task-001", "生成大纲")
memory.add_task_step("task-001", "生成代码")

# 完成步骤
memory.complete_current_step("task-001", {"result": "大纲生成成功"})

# 获取状态
summary = memory.get_summary()
```

### 2. TaskProcessor (任务处理器)
```python
processor = TaskProcessor(ppt_generator, memory)

# 自动处理任务
result = await processor.process_task_automatically(
    "创建关于Python编程的教学PPT",
    requirements={"style": "简约", "pages": 8}
)
```

### 3. PPTRunner2 (增强版运行器)
```python
runner = PPTRunner2()

# 自动模式
result = await runner.handle_task_automatically("任务描述")

# 检查任务状态
status = runner.check_task_completion()

# 获取记忆状态
memory_status = runner.get_memory_status()
```

## 使用方式

### 1. 简单自动调用
```python
import asyncio
from run_ppt import create_ppt_automatically

async def main():
    result = await create_ppt_automatically(
        "创建一个关于人工智能发展趋势的PPT，包括技术现状、应用场景、未来展望等内容"
    )
    
    if result["success"]:
        print(f"✅ PPT生成成功！生成了{len(result['files'])}个文件")
        if result["ready_to_send"]:
            print("📤 文件已准备好发送")
    else:
        print(f"❌ 生成失败: {result['error']}")

asyncio.run(main())
```

### 2. 高级监控模式
```python
import asyncio
from run_ppt import get_ppt_runner

async def advanced_usage():
    runner = get_ppt_runner()
    
    # 启动自动任务
    task = asyncio.create_task(
        runner.handle_task_automatically("制作产品介绍PPT")
    )
    
    # 监控进度
    while not task.done():
        status = runner.check_task_completion()
        print(f"📊 {status['message']}")
        
        if status.get('completed'):
            print("🎉 任务完成！")
            break
            
        await asyncio.sleep(3)  # 每3秒检查一次
    
    result = await task
    return result

asyncio.run(advanced_usage())
```

### 3. 交互模式（原有功能）
```python
from run_ppt import main

# 启动交互式界面
main()
```

## 任务流程

自动任务处理的完整流程：

```
📝 接收任务描述
    ↓
🧠 在短期记忆中创建任务记录
    ↓
📋 生成PPT大纲 (Claude-4)
    ↓
💻 生成PPT代码 (Claude-4)  
    ↓
⚙️ 执行代码生成PPT文件
    ↓
🔧 自动错误修复 (如需要)
    ↓
📁 整理生成的文件信息
    ↓
✅ 更新任务状态为完成
    ↓
📤 准备文件发送
```

## 返回结果格式

### 成功结果
```json
{
    "success": true,
    "task_id": "a1b2c3d4",
    "message": "PPT生成完成！共生成2个文件",
    "files": [
        {
            "path": "./ppts/AI主题PPT_20250101_120000.pptx",
            "name": "AI主题PPT_20250101_120000.pptx",
            "size_mb": 2.3,
            "modified_time": "2025-01-01T12:00:00"
        }
    ],
    "memory_summary": "当前任务: 制作AI主题PPT | 状态: completed | 进度: 5/5",
    "ready_to_send": true
}
```

### 失败结果
```json
{
    "success": false,
    "task_id": "a1b2c3d4",
    "error": "代码执行失败",
    "message": "PPT生成失败: 代码执行失败",
    "memory_summary": "当前任务: 制作AI主题PPT | 状态: failed | 进度: 3/5"
}
```

## 短期记忆状态

### 记忆结构
```json
{
    "tasks": {
        "task-id": {
            "id": "task-id",
            "description": "任务描述",
            "status": "completed",
            "steps": [
                {
                    "name": "生成大纲",
                    "completed": true,
                    "result": {...}
                }
            ],
            "files_generated": [...]
        }
    },
    "current_task": "task-id",
    "session_history": [...]
}
```

### 任务状态
- `created`: 任务已创建
- `planning`: 正在规划
- `generating`: 正在生成内容
- `executing`: 正在执行代码
- `completed`: 已完成
- `failed`: 失败

## 集成示例

### 与聊天机器人集成
```python
class ChatBot:
    def __init__(self):
        self.ppt_runner = get_ppt_runner()
    
    async def handle_ppt_request(self, user_message):
        # 解析用户需求
        task_description = self.extract_ppt_requirement(user_message)
        
        # 自动生成PPT
        result = await self.ppt_runner.handle_task_automatically(task_description)
        
        if result["success"] and result.get("ready_to_send"):
            # 发送文件给用户
            await self.send_files_to_user(result["files"])
            return f"✅ {result['message']}"
        else:
            return f"❌ {result['message']}"
```

### 与任务调度器集成
```python
class TaskScheduler:
    def __init__(self):
        self.ppt_runner = get_ppt_runner()
    
    async def process_ppt_task(self, task_data):
        # 检查是否有进行中的任务
        status = self.ppt_runner.check_task_completion()
        
        if status.get("completed"):
            # 上一个任务已完成，可以开始新任务
            result = await self.ppt_runner.handle_task_automatically(
                task_data["description"]
            )
            
            if result.get("ready_to_send"):
                await self.notify_user(result["files"])
        
        return status
```

## 配置要求

### 环境变量
```bash
# yunwu API密钥
YUNWU_API_KEY=your_yunwu_api_key

# Tavily搜索API密钥 (用于图片搜索)
TAVILY_API_KEY=your_tavily_api_key
```

### 依赖库
```bash
pip install openai python-pptx pillow requests python-dotenv tavily-python
```

## 注意事项

1. **API限制**: yunwu API有使用限制，请合理控制调用频率
2. **文件大小**: 生成的PPT文件通常在1-5MB，包含图片可能更大
3. **执行时间**: 完整流程通常需要30-60秒
4. **错误处理**: 系统会自动重试2次，如仍失败会返回详细错误信息
5. **内存管理**: 短期记忆会在进程结束时清空，长期存储需要额外实现

## 示例运行

运行自动模式示例：
```bash
cd src/JarvisChain
python ppt_auto_example.py
```

运行交互模式：
```bash
cd src/JarvisChain
python run_ppt.py
``` 