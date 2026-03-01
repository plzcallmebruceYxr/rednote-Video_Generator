# 🎬 书单视频助手 (XHS Book Video Assistant)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**书单视频助手** 是一款专为小红书（XHS）创作者设计的自动化视频生产工具。它集成了大语言模型（Gemini/OpenAI）生成脚本、Edge-TTS 语音合成以及 MoviePy 视频自动化渲染技术，只需输入书名，即可一键生成极具爆款潜质的对话式书单推荐视频。

---

## ✨ 功能特性

-   **🤖 智能剧本创作**：支持 Google Gemini 和 OpenAI 双接口，自动生成读者与作者的深度对话脚本。
-   **🎙️ 高质量语音合成**：采用 Microsoft Edge-TTS，提供极具表现力的男女声对白。
-   **🎨 自动化视觉渲染**：
    -   自动生成对话气泡与打字机效果。
    -   支持自定义背景图与头像。
    -   **修复补丁**：内置针对 MoviePy v2.0+ 的音频循环兼容性方案。
-   **⚡ 实时预览与下载**：基于 Streamlit 的 Web 界面，实时查看渲染进度并直接下载成品。
-   [cite_start]**🧹 自动维护**：内置缓存清理机制，防止临时音频文件占用过多磁盘空间 。

---

## 🛠️ 安装与部署

### 1. 环境要求
-   **Python**: 3.9 或更高版本。
-   **FFmpeg**: 必须安装。视频渲染强依赖 FFmpeg，请确保其已添加至系统环境变量 `Path`。

### 2. 克隆项目与安装依赖
```bash
# 安装必要依赖
pip install -r requirements.txt