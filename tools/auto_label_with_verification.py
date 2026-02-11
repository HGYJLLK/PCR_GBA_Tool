"""
半自动OCR图片标注工具

用途：使用预训练CnOCR模型自动标注debug图片，然后人工校验修正

使用方法：
    python tools/auto_label_with_verification.py

工作流程：
1. 使用CnOCR预训练模型自动识别所有图片
2. 逐张显示图片和识别结果
3. 用户按Enter确认正确，或输入正确标签
4. 自动保存到 training_data/from_debug/
"""

import sys
import cv2
from pathlib import Path
import shutil
import hashlib
import sqlite3

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from module.logger import logger
from cnocr import CnOcr


def compute_image_hash(img_path):
    """计算图片的MD5哈希值"""
    with open(img_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def init_cache_db(db_path):
    """初始化缓存数据库"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS label_cache (
            image_hash TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            labeled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn


def get_cached_label(conn, image_hash):
    """从缓存中获取标签"""
    cursor = conn.cursor()
    cursor.execute('SELECT label FROM label_cache WHERE image_hash = ?', (image_hash,))
    result = cursor.fetchone()
    return result[0] if result else None


def save_label_to_cache(conn, image_hash, label):
    """保存标签到缓存"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO label_cache (image_hash, label)
        VALUES (?, ?)
    ''', (image_hash, label))
    conn.commit()


def main():
    # 配置路径
    project_root = Path(__file__).parent.parent
    debug_dir = project_root / "logs" / "ocr_errors"
    output_dir = project_root / "training_data" / "manual_errors"
    cache_db_path = project_root / "training_data" / "label_cache.db"
    
    # 准备输出目录
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化缓存数据库
    logger.info(f"Initializing label cache: {cache_db_path}")
    cache_conn = init_cache_db(cache_db_path)
    
    # 检查debug目录
    if not debug_dir.exists():
        print(f"Error: Debug directory not found: {debug_dir}")
        cache_conn.close()
        return
        
    # 初始化CnOCR（使用预训练模型）
    logger.info("Initializing CnOCR pretrained model...")
    ocr = CnOcr(
        rec_model_name='densenet_lite_136-fc',  # 预训练模型
        cand_alphabet='0123456789:'  # 只识别数字和冒号
    )
    logger.info("CnOCR model loaded successfully")
    
    # 获取所有图片
    all_images = sorted(debug_dir.glob("*.png"))
    min_file_size = 800  # 降低门槛，包含更多图片
    
    valid_images = []
    for img_path in all_images:
        if img_path.stat().st_size >= min_file_size:
            valid_images.append(img_path)
            
    logger.info(f"Found {len(valid_images)} images (>= {min_file_size} bytes) out of {len(all_images)} total")
    
    if not valid_images:
        print("No valid images found!")
        return
        
    # 标注列表
    labels = []
    labeled_count = 0
    skipped_count = 0
    auto_correct_count = 0
    manual_correct_count = 0
    
    print("=" * 70)
    print("Semi-Automated OCR Labeling Tool")
    print("=" * 70)
    print("Instructions:")
    print("  - Press ENTER to accept the predicted label")
    print("  - Type the correct label (e.g., '1:17') to override")
    print("  - Type 's' to skip this image")
    print("  - Type 'q' to quit")
    print("=" * 70)
    
    for i, img_path in enumerate(valid_images):
        # 读取图片
        img = cv2.imread(str(img_path))
        if img is None:
            logger.warning(f"Failed to read: {img_path.name}")
            skipped_count += 1
            continue
        
        # 计算图片哈希并检查缓存
        img_hash = compute_image_hash(img_path)
        cached_label = get_cached_label(cache_conn, img_hash)
        
        if cached_label:
            # 命中缓存，直接使用
            print(f"\n[{i+1}/{len(valid_images)}] {img_path.name}")
            print(f"  [缓存] 标签: '{cached_label}' ✓ 自动跳过")
            
            final_label = cached_label
            auto_correct_count += 1
            
            # 保存图片和标签
            new_name = f"debug_{labeled_count:04d}.png"
            new_path = images_dir / new_name
            shutil.copy(img_path, new_path)
            
            labels.append((f"images/{new_name}", final_label))
            labeled_count += 1
            continue
            
        # OCR识别
        try:
            result = ocr.ocr(str(img_path))
            if result and len(result) > 0:
                # 拼接识别的字符
                predicted_text = ''.join([char for char in result[0]['text']])
            else:
                predicted_text = ""
        except Exception as e:
            logger.warning(f"OCR failed for {img_path.name}: {e}")
            predicted_text = ""
            
        # 放大显示
        scale = 5
        height, width = img.shape[:2]
        resized = cv2.resize(img, (width * scale, height * scale), interpolation=cv2.INTER_NEAREST)
        
        window_name = f"[{i+1}/{len(valid_images)}] {img_path.name}"
        cv2.imshow(window_name, resized)
        cv2.waitKey(1)  # 刷新窗口
        
        # 显示预测结果
        print(f"\n[{i+1}/{len(valid_images)}] {img_path.name}")
        print(f"  Predicted: '{predicted_text}'")
        
        # 等待用户确认或修改
        user_input = input("  Confirm (Enter) / Correct / Skip (s) / Quit (q): ").strip()
        
        cv2.destroyAllWindows()
        
        # 处理用户输入
        if user_input.lower() == 'q':
            logger.info("User requested quit")
            break
        elif user_input.lower() == 's':
            skipped_count += 1
            print("  -> Skipped")
            continue
        elif user_input == '':
            # 用户按Enter，接受预测结果
            if not predicted_text or ':' not in predicted_text:
                print(f"  -> Invalid prediction, skipping")
                skipped_count += 1
                continue
            final_label = predicted_text
            auto_correct_count += 1
            print(f"  -> Accepted: '{final_label}'")
        else:
            # 用户手动输入
            if ':' in user_input and all(c.isdigit() or c == ':' for c in user_input):
                final_label = user_input
                manual_correct_count += 1
                print(f"  -> Corrected to: '{final_label}'")
            else:
                print(f"  -> Invalid format: '{user_input}', skipped")
                skipped_count += 1
                continue
                
        # 保存图片和标签
        new_name = f"debug_{labeled_count:04d}.png"
        new_path = images_dir / new_name
        shutil.copy(img_path, new_path)
        
        # 保存到缓存数据库
        save_label_to_cache(cache_conn, img_hash, final_label)
        
        labels.append((f"images/{new_name}", final_label))
        labeled_count += 1
        
    cv2.destroyAllWindows()
    
    # 保存标签文件
    if labels:
        labels_file = output_dir / "labels.txt"
        with open(labels_file, 'w', encoding='utf-8') as f:
            for img_name, label in labels:
                # 直接保存，不添加空格
                f.write(f"{img_name}\t{label}\n")
                
        print("\n" + "=" * 70)
        print("Labeling Complete!")
        print("=" * 70)
        print(f"  Total processed: {labeled_count + skipped_count}")
        print(f"  Successfully labeled: {labeled_count}")
        print(f"    - Auto-accepted: {auto_correct_count}")
        print(f"    - Manually corrected: {manual_correct_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Output directory: {output_dir}")
        print(f"  Labels file: {labels_file}")
        print("=" * 70)
        print(f"\nNext step: Use this data for training!")
    else:
        print("\nNo images labeled.")
    
    # 关闭缓存数据库连接
    cache_conn.close()


if __name__ == "__main__":
    main()
