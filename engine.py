import os
import numpy as np
import logging
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from moviepy.audio.AudioClip import concatenate_audioclips # 引入拼接工具
from proglog import ProgressBarLogger
import asyncio
import edge_tts

# 彻底修复兼容性的音频循环函数
def safe_audio_loop(clip, duration):
    """手动实现音频循环，解决 MoviePy 版本属性丢失问题"""
    try:
        # 尝试使用新版导包
        from moviepy.audio.fx.audio_loop import audio_loop
        return audio_loop(clip, duration=duration)
    except Exception:
        try:
            # 尝试旧版导包
            from moviepy.audio.fx.all import audio_loop
            return audio_loop(clip, duration=duration)
        except Exception:
            # 万能方案：手动拼接
            n_loops = int(np.ceil(duration / clip.duration))
            looped = concatenate_audioclips([clip] * n_loops)
            return looped.with_duration(duration)

# 配置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

# 自定义进度条记录器
class VideoProcessingLogger(ProgressBarLogger):
    def callback(self, **changes):
        for bar_name, bar_data in self.bars.items():
            if bar_name == 't':
                current = bar_data['index']
                total = bar_data['total']
                if total and current % 5 == 0:
                    percentage = (current / total) * 100
                    logging.info(f"视频合成进度: {current}/{total} 帧 ({percentage:.1f}%)")

class XHSVideoEngine:
    def __init__(self, font_reg, font_bold, font_book, reader_avatar, author_avatar, type_sound_path):
        self.font_reg = font_reg
        self.font_bold = font_bold
        self.font_book = font_book 
        self.reader_avatar = reader_avatar
        self.author_avatar = author_avatar
        self.type_sound_path = type_sound_path
        self.width, self.height = 720, 1280

    async def _generate_audio(self, text, role, filename):
        import re
        clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？]', '', text.replace("**", ""))
        role_key = str(role).lower().strip()
        is_author = not ("reader" in role_key or "读者" in role_key)
        voice = "zh-CN-YunxiNeural" if is_author else "zh-CN-XiaoxiaoNeural"
        if os.path.exists(filename): os.remove(filename)
        try:
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(filename)
            return AudioFileClip(filename)
        except Exception as e:
            logging.error(f"TTS Error: {e}")
            raise

    def _make_transparent_clip(self, pil_img, duration):
        img_np = np.array(pil_img)
        clip = ImageClip(img_np[:, :, :3]).with_duration(duration)
        mask_clip = ImageClip(img_np[:, :, 3] / 255.0, is_mask=True).with_duration(duration)
        return clip.with_mask(mask_clip)

    def _draw_rich_text_frame(self, draw, text, start_x, start_y, font_reg, font_bold, fill):
        lines = text.split('\n')
        curr_y = start_y
        for line in lines:
            parts = line.split("**")
            curr_x = start_x
            for i, part in enumerate(parts):
                is_bold = (i % 2 == 1)
                font = font_bold if is_bold else font_reg
                color = (255, 140, 0) if is_bold else fill 
                draw.text((curr_x, curr_y), part, font=font, fill=color)
                bbox = draw.textbbox((curr_x, curr_y), part, font=font)
                curr_x += (bbox[2] - bbox[0])
            curr_y += 52 

    def _smart_wrap(self, text, width=19):
        lines, current_line, visible_count, i = [], "", 0, 0
        while i < len(text):
            if text[i:i+2] == "**": current_line += "**"; i += 2; continue
            if text[i] == "\n": lines.append(current_line); current_line = ""; visible_count = 0; i += 1; continue
            current_line += text[i]; visible_count += 1
            if visible_count >= width: lines.append(current_line); current_line = ""; visible_count = 0
            i += 1
        if current_line: lines.append(current_line)
        return "\n".join(lines)

    def create_scene(self, text, role, audio_clip, pause_time=1.2):
        duration = audio_clip.duration
        total_duration = duration + pause_time
        f_reg = ImageFont.truetype(self.font_reg, 28)
        f_bold = ImageFont.truetype(self.font_bold, 28)
        is_author = not ("reader" in str(role).lower() or "读者" in str(role))
        wrapped_text = self._smart_wrap(text, width=20)
        
        MAX_VISIBLE_LINES = 8
        LINE_HEIGHT = 52
        BUBBLE_PADDING = 50
        
        actual_lines_list = wrapped_text.split('\n')
        display_line_count = min(len(actual_lines_list), MAX_VISIBLE_LINES)
        bubble_h = (display_line_count * LINE_HEIGHT) + BUBBLE_PADDING
        
        target_bubble_y = (650 if is_author else 250) + 120

        bubble_img = Image.new('RGBA', (660, bubble_h), (255, 255, 255, 0))
        draw_b = ImageDraw.Draw(bubble_img)
        b_color = (255, 250, 180, 245) if is_author else (255, 255, 255, 245)
        draw_b.rounded_rectangle([0, 0, 660, bubble_h], 20, fill=b_color)
        bubble_layer = self._make_transparent_clip(bubble_img, total_duration).with_position((30, target_bubble_y))

        clean_text_only = wrapped_text.replace("**", "").replace("\n", "")
        clean_len = len(clean_text_only)
        char_dur = duration / max(clean_len, 1)
        text_frames = []
        text_color = (50, 50, 50) if is_author else (30, 30, 30)

        for i in range(1, clean_len + 1):
            current_raw = self._get_sliced_rich_text(wrapped_text, i)
            lines = current_raw.split('\n')
            if len(lines) > MAX_VISIBLE_LINES: lines = lines[-MAX_VISIBLE_LINES:]
            display_text = "\n".join(lines)
            img = Image.new('RGBA', (720, 1280), (0, 0, 0, 0))
            self._draw_rich_text_frame(ImageDraw.Draw(img), display_text, 60, target_bubble_y + 25, f_reg, f_bold, text_color)
            text_frames.append(self._make_transparent_clip(img, char_dur))

        # 停顿帧
        last_img = Image.new('RGBA', (720, 1280), (0, 0, 0, 0))
        self._draw_rich_text_frame(ImageDraw.Draw(last_img), "\n".join(actual_lines_list[-MAX_VISIBLE_LINES:]), 60, target_bubble_y + 25, f_reg, f_bold, text_color)
        text_frames.append(self._make_transparent_clip(last_img, pause_time))
        
        text_layer = concatenate_videoclips(text_frames)

        def get_pos(t, side, y):
            bx = 35 if side == "left" else 535
            jump = abs(15 * np.sin(6 * t)) if t < duration else 0
            return (bx, y - jump)

        read_clip = ImageClip(self.reader_avatar).resized(width=150).with_duration(total_duration)
        auth_clip = ImageClip(self.author_avatar).resized(width=150).with_duration(total_duration)
        r_pos = (lambda t: get_pos(t, "left", 250)) if not is_author else (35, 250)
        a_pos = (lambda t: get_pos(t, "right", 650)) if is_author else (535, 650)

        return CompositeVideoClip([
            read_clip.with_position(r_pos), 
            auth_clip.with_position(a_pos), 
            bubble_layer, 
            text_layer
        ], size=(720, 1280)).with_duration(total_duration).with_audio(audio_clip)

    def _get_sliced_rich_text(self, text, length):
        visible_count, sliced, i = 0, "", 0
        while i < len(text) and visible_count < length:
            if text[i:i+2] == "**": sliced += "**"; i += 2; continue
            sliced += text[i]
            if text[i] != "\n": visible_count += 1
            i += 1
        if sliced.count("**") % 2 != 0: sliced += "**"
        return sliced

    def create_slogan_scene(self, slogan_text, author_name, book_name, duration=3.0):
        try: f_book = ImageFont.truetype(self.font_book, 75)
        except: f_book = ImageFont.truetype(self.font_bold, 75)
        f_theme, f_author = ImageFont.truetype(self.font_bold, 42), ImageFont.truetype(self.font_reg, 28)
        
        full_book_name = f"《{book_name}》"
        total_chars = len(full_book_name) + len(slogan_text)
        typing_ratio = 0.8
        typing_dur, pause_dur = duration * typing_ratio, duration * (1 - typing_ratio)
        char_dur = typing_dur / max(total_chars, 1)

        def draw_centered(draw_obj, text, y, font, color):
            bbox = draw_obj.textbbox((0, 0), text, font=font)
            x = (720 - (bbox[2] - bbox[0])) / 2
            draw_obj.text((x, y), text, font=font, fill=color)

        typing_frames = []
        for i in range(1, total_chars + 1):
            img = Image.new('RGBA', (720, 1280), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 480, 720, 840], fill=(255, 255, 255, 235))
            curr_book = full_book_name[:i] if i <= len(full_book_name) else full_book_name
            curr_slogan = "" if i <= len(full_book_name) else slogan_text[:i - len(full_book_name)]
            if curr_book: draw_centered(draw, curr_book, 530, f_book, (0, 220, 0))
            if curr_slogan: draw_centered(draw, curr_slogan, 680, f_theme, (180, 0, 0))
            draw_centered(draw, author_name, 770, f_author, (80, 80, 80))
            typing_frames.append(self._make_transparent_clip(img, char_dur))

        typing_clip = concatenate_videoclips(typing_frames)
        # 使用修复后的安全循环函数
        if os.path.exists(self.type_sound_path):
            try:
                sound = AudioFileClip(self.type_sound_path)
                looped_sound = safe_audio_loop(sound, duration=typing_dur)
                typing_clip = typing_clip.with_audio(looped_sound)
            except Exception as e:
                logging.warning(f"加载打字音效失败: {e}")

        last_img = Image.new('RGBA', (720, 1280), (0, 0, 0, 0))
        ld = ImageDraw.Draw(last_img)
        ld.rectangle([0, 480, 720, 840], fill=(255, 255, 255, 235))
        draw_centered(ld, full_book_name, 530, f_book, (0, 220, 0))
        draw_centered(ld, slogan_text, 680, f_theme, (180, 0, 0))
        draw_centered(ld, author_name, 770, f_author, (80, 80, 80))
        pause_clip = self._make_transparent_clip(last_img, pause_dur)

        return concatenate_videoclips([typing_clip, pause_clip])

async def run_engine(script, bg_path, output_path, slogan_ai, authorname_ai):
    engine = XHSVideoEngine(
        "assets/fonts/Normal.ttf", "assets/fonts/Bold.ttf", "assets/fonts/Title.ttf", 
        "assets/avatars/reader.png", "assets/avatars/author.png",
        "assets/audio/type_sound.mp3"
    )
    bg = ImageClip(bg_path).resized(width=720)
    if bg.h < 1280: bg = bg.resized(height=1280)
    
    scenes = []
    book_title = os.path.basename(output_path).replace("_xhs.mp4", "")
    logging.info("--- 开始构建视频片段 ---")
    scenes.append(engine.create_slogan_scene(slogan_ai, authorname_ai, book_title))
    
    for i, item in enumerate(script):
        af = f"temp/a_{i}.mp3"
        audio = await engine._generate_audio(item['content'], item['role'], af)
        scenes.append(engine.create_scene(item['content'], item['role'], audio))
    
    scenes.append(engine.create_slogan_scene(slogan_ai, authorname_ai, book_title, duration=2.5))
    
    content = concatenate_videoclips(scenes)
    final_video = CompositeVideoClip([
        bg.with_duration(content.duration).with_position("center"), 
        content
    ], size=(720, 1280)).with_duration(content.duration)
    
    logging.info(f"--- 启动视频导出: {output_path} ---")
    final_video.write_videofile(
        output_path, fps=15, codec="libx264", audio_codec="aac", 
        preset="ultrafast", logger=VideoProcessingLogger() 
    )
    final_video.close()
    logging.info("--- 视频生成任务完成 ---")