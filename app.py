import streamlit as st
import asyncio
import os
import json
import re
import time
import logging
from pathlib import Path
from google import genai
from engine import run_engine

# 配置日志输出格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

# 尝试导入 OpenAI 以支持兼容接口
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

st.set_page_config(page_title="书单视频助手", page_icon="🎬")

@st.cache_resource
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

@st.cache_resource
def get_openai_client(api_key, base_url):
    if OpenAI: return OpenAI(api_key=api_key, base_url=base_url)
    return None

def cleanup_temp_files():
    temp_path = Path("temp")
    if not temp_path.exists(): return
    for item in temp_path.iterdir():
        try:
            if item.is_file() and (time.time() - item.stat().st_mtime > 600):
                item.unlink()
        except: pass

async def get_script_multi_model(book_name, hint, provider, api_key, base_url, model_id):
    logging.info(f"正在请求 {provider} 生成剧本: 《{book_name}》")
    prompt = (
        f"你是一位资深书评人。针对《{book_name}》，生成几组读者与作者的对话，目的是吸引读者买书。\n"
        f"要求：1. 关键结论用双星号加粗（**关键内容**）；2. 具体生成要求：{hint}；"
        f"3. 仅输出 JSON 数组，含 role('reader'/'author') 和 content 字段。"
    )
    try:
        if provider == "Google Gemini":
            client = get_gemini_client(api_key)
            response = await client.aio.models.generate_content(model=model_id, contents=prompt)
            res = response.text
        else:
            client = get_openai_client(api_key, base_url)
            completion = client.chat.completions.create(model=model_id, messages=[{"role": "user", "content": prompt}])
            res = completion.choices[0].message.content
        match = re.search(r'\[.*\]', res, re.DOTALL)
        return json.loads(match.group() if match else res)
    except Exception as e:
        st.error(f"脚本生成失败: {e}")
        return None

# --- 1. 基础页面配置 ---
st.title("🎬 书单视频生成器")
st.caption("🚀 修复补丁：解决了 MoviePy 音频循环的兼容性报错")

with st.sidebar:
    st.header("⚙️ 接口设置")
    provider = st.selectbox("供应商", ["Google Gemini", "OpenAI / 兼容接口"])
    user_api_key = st.text_input("API Key", type="password")
    model_id = st.text_input("模型 ID", value="gemini-2.5-flash" if provider == "Google Gemini" else "gpt-4o-mini")
    base_url = st.text_input("Base URL", value="https://api.openai.com/v1") if provider != "Google Gemini" else None

tab1, tab2 = st.tabs(["🤖 AI 构思", "⌨️ 手动输入"])
with tab1:
    book_ai = st.text_input("📖 书名", key="ai_b")
    hint_ai = st.text_area("🎯 视频重点", key="ai_h", placeholder="例如：介绍核心观点")
    slogan_ai = st.text_area("✨ 主旨", key="ai_s", placeholder="例如：每天进步一点点")
    authorname_ai = st.text_area("🤖 作者名称", key="ai_a", placeholder="例如：@与你同行伴你成长")
with tab2:
    book_man = st.text_input("📖 视频标题", value="认知觉醒", key="man_b")
    manual_json = st.text_area("✍️ 编辑对话 JSON", value='''[
  {"role": "reader", "content": "为什么我要读这本**《思考，快与慢》**？"},
  {"role": "author", "content": "因为我们要学会警惕**直觉偏见**，调用更理性的**系统2**。"}
]''', height=150)

bg_file = st.file_uploader("🖼️ 背景图", type=["jpg", "png"])

if st.button("🚀 开始制作", use_container_width=True):
    if not user_api_key or not bg_file:
        st.warning("请检查 API Key 和背景图")
    else:
        with st.status("正在制作中，控制台实时显示帧进度...", expanded=True) as status:
            try:
                async def main_process():
                    if book_ai:
                        script = await get_script_multi_model(book_ai, hint_ai, provider, user_api_key, base_url, model_id)
                        name_val = book_ai
                    else:
                        script = json.loads(manual_json)
                        name_val = book_man
                    if not script: return None, None, None
                    if not os.path.exists("temp"): os.makedirs("temp")
                    bg_path = "temp/bg.jpg"
                    with open(bg_path, "wb") as f: f.write(bg_file.getbuffer())
                    out_p = f"output/{name_val}_xhs.mp4"
                    if not os.path.exists("output"): os.makedirs("output")
                    logging.info("启动渲染引擎...")
                    await run_engine(script, bg_path, out_p, slogan_ai, authorname_ai)
                    return script, out_p, name_val

                result = asyncio.run(main_process())
                if result and result[0]:
                    status.update(label="✅ 生成成功！", state="complete")
                    st.video(result[1])
                    st.download_button("📥 下载视频", open(result[1], "rb"), file_name=f"{result[2]}.mp4")
                    logging.info("清理临时缓存...")
                    cleanup_temp_files()
            except Exception as e:
                st.error(f"❌ 失败：{e}")