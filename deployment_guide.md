# 🎬 书单视频助手部署指南

## 1. 准备要求
* **Python**: 3.9+
* **FFmpeg**: 必须安装并添加到系统路径 (Path)
* **硬件**: 建议 8G 内存以上（视频渲染较占资源）

## 2. 核心文件清单
1. `app.py`: Streamlit 用户界面与业务逻辑 [cite: 1]
2. `engine.py`: 视频合成与 Edge-TTS 语音生成核心 [cite: 3]
3. `cleanup.py`: 自动清理 temp 目录下的过期文件 [cite: 2]
4. `run_tool.bat`: Windows 一键启动脚本 [cite: 4]
5. `requirements.txt`: 依赖库清单

## 3. 资源配置 (Assets)
请确保根目录下存在 `/assets` 文件夹，并包含以下子目录：
- `/fonts`: Normal.ttf, Bold.ttf, Title.ttf
- `/avatars`: reader.png, author.png
- `/audio`: type_sound.mp3

## 4. 安装步骤
### 方案 A：Windows (推荐)
直接运行 `run_tool.bat`，脚本将自动处理环境 [cite: 4]。

### 方案 B：手动安装
1. 创建虚拟环境: `python -m venv venv`
2. 激活环境: `venv\Scripts\activate`
3. 安装依赖: `pip install -r requirements.txt`
4. 启动程序: `streamlit run app.py`

## 5. 注意事项
* **音频修复**: `engine.py` 已内置 `safe_audio_loop` 补丁，解决了 MoviePy 版本兼容性导致的循环报错问题 [cite: 3]。
* **清理机制**: 程序启动后会定期清理 `temp/` 目录，请勿手动删除正在合成中的文件 [cite: 2]。
