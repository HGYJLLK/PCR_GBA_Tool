"""
OCR 识别调试工具
实时显示原图、预处理后的图像和识别结果

用法:
    python tools/debug_ocr.py
"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from module.config.config import PriconneConfig
from module.device.device import Device
from module.ocr.models import OCR_MODEL
from module.logger import logger


class OcrDebugger:
    """OCR 调试器"""
    
    def __init__(self):
        self.config = PriconneConfig("maple", "Pcr")
        self.device = Device(self.config)
        self.device.disable_stuck_detection()
        
        # 初始化 OCR
        self.ocr_engine = OCR_MODEL.pcr
        self.ocr_engine.init()
        
        # 计时器 ROI 区域
        self.timer_roi = (1078, 24, 1120, 48)
        
    def debug_realtime(self):
        """实时调试模式"""
        logger.hr("OCR 实时调试", level=1)
        logger.info("按 'q' 退出，'s' 保存当前图像")
        
        save_count = 0
        
        while True:
            try:
                # 截图
                screenshot = self.device.screenshot()
                
                # 裁剪计时器区域
                x1, y1, x2, y2 = self.timer_roi
                timer_img = screenshot[y1:y2, x1:x2]
                
                # 预处理
                processed_img = self._preprocess_image(timer_img)
                
                # OCR 识别
                # 原图识别
                result_raw = self.ocr_engine._ocr.ocr(timer_img)
                text_raw = result_raw[0]['text'] if result_raw else ""
                score_raw = result_raw[0]['score'] if result_raw else 0.0
                
                # 预处理后识别
                result_processed = self.ocr_engine._ocr.ocr(processed_img)
                text_processed = result_processed[0]['text'] if result_processed else ""
                score_processed = result_processed[0]['score'] if result_processed else 0.0
                
                # 过滤只保留数字和冒号
                text_raw_filtered = ''.join(c for c in text_raw if c in "0123456789:")
                text_processed_filtered = ''.join(c for c in text_processed if c in "0123456789:")
                
                # 打印结果
                print(f"\r原图: '{text_raw_filtered}' ({score_raw:.2%}) | "
                      f"预处理: '{text_processed_filtered}' ({score_processed:.2%})   ", end='')
                
                # 显示图像（放大以便查看）
                scale = 4
                timer_large = cv2.resize(timer_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
                processed_large = cv2.resize(processed_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
                
                # 转换为 BGR 以便显示
                if len(processed_large.shape) == 2:
                    processed_large = cv2.cvtColor(processed_large, cv2.COLOR_GRAY2BGR)
                
                # 添加文本标签
                cv2.putText(timer_large, f"Raw: {text_raw_filtered}", (5, 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.putText(processed_large, f"Processed: {text_processed_filtered}", (5, 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # 横向拼接
                combined = np.hstack([timer_large, processed_large])
                
                cv2.imshow("OCR Debug (Original | Processed)", combined)
                
                # 按键处理
                key = cv2.waitKey(500) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    # 保存图像
                    save_dir = Path("ocr_debug_images")
                    save_dir.mkdir(exist_ok=True)
                    
                    cv2.imwrite(str(save_dir / f"raw_{save_count:03d}.png"), timer_img)
                    cv2.imwrite(str(save_dir / f"processed_{save_count:03d}.png"), processed_img)
                    
                    with open(save_dir / f"result_{save_count:03d}.txt", 'w') as f:
                        f.write(f"Raw: {text_raw_filtered} ({score_raw:.2%})\n")
                        f.write(f"Processed: {text_processed_filtered} ({score_processed:.2%})\n")
                    
                    logger.info(f"\n已保存图像 #{save_count}")
                    save_count += 1
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(1)
        
        cv2.destroyAllWindows()
        print("\n调试结束")
    
    def _preprocess_image(self, img):
        """
        预处理图像（与 models.py 中的实现相同）
        """
        # 1. 转灰度
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # 2. 自适应二值化
        binary = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 2
        )
        
        # 3. 去噪
        denoised = cv2.fastNlMeansDenoising(binary, None, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # 4. 轻微锐化
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        return sharpened
    
    def test_static_images(self, image_dir):
        """测试静态图像"""
        logger.hr("测试静态图像", level=1)
        
        image_dir = Path(image_dir)
        if not image_dir.exists():
            logger.error(f"目录不存在: {image_dir}")
            return
        
        images = list(image_dir.glob("*.png")) + list(image_dir.glob("*.jpg"))
        logger.info(f"找到 {len(images)} 张图像")
        
        for img_path in images:
            img = cv2.imread(str(img_path))
            
            # 预处理
            processed = self._preprocess_image(img)
            
            # OCR
            result_raw = self.ocr_engine._ocr.ocr(img)
            result_processed = self.ocr_engine._ocr.ocr(processed)
            
            text_raw = result_raw[0]['text'] if result_raw else ""
            text_processed = result_processed[0]['text'] if result_processed else ""
            
            logger.info(f"{img_path.name}: '{text_raw}' -> '{text_processed}'")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OCR 调试工具")
    parser.add_argument("--static", type=str, help="测试静态图像目录")
    args = parser.parse_args()
    
    debugger = OcrDebugger()
    
    if args.static:
        debugger.test_static_images(args.static)
    else:
        debugger.debug_realtime()


if __name__ == "__main__":
    main()
