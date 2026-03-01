import os
import shutil
import time
from pathlib import Path

def cleanup_temp_dir(target_dir="temp", older_than_seconds=3600):
    """
    自动清理指定的临时目录
    :param target_dir: 目标目录路径
    :param older_than_seconds: 清理多久之前的文件（默认 1 小时）
    """
    temp_path = Path(target_dir)
    
    if not temp_path.exists():
        print(f"⚠️ 目录 {target_dir} 不存在，无需清理。")
        return

    print(f"🧹 开始清理目录: {temp_path.absolute()}")
    
    count = 0
    current_time = time.time()

    for item in temp_path.iterdir():
        try:
            # 获取文件最后修改时间
            file_time = item.stat().st_mtime
            
            # 仅清理超过指定时间的文件，防止删掉正在合成中的素材
            if current_time - file_time > older_than_seconds:
                if item.is_file():
                    item.unlink() # 删除文件
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item) # 删除子目录
                    count += 1
        except Exception as e:
            print(f"❌ 无法删除 {item.name}: {e}")

    print(f"✅ 清理完成，共删除 {count} 个过期文件/目录。")

if __name__ == "__main__":
    # 执行清理
    cleanup_temp_dir()