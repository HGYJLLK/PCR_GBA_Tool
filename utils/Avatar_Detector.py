import os
import cv2
import numpy as np
import logging
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CharacterGridDetector:
    def __init__(self, character_data: Dict = None):
        """
        初始化检测器

        Args:
            character_data: 角色数据字典
        """
        self.character_data = character_data or {}

        # 颜色范围配置
        self.color_ranges = [
            # 橙色范围
            (np.array([0, 40, 50]), np.array([30, 255, 255])),
            # 黄色范围
            (np.array([15, 40, 50]), np.array([40, 255, 255]))
        ]

        # 形态学操作参数
        self.morph_kernel = np.ones((5, 5), np.uint8)
        self.close_iterations = 2
        self.open_iterations = 1

        # 检测参数
        self.min_area = 3000
        self.max_area = 60000
        self.aspect_ratio_range = (0.6, 1.4)
        self.similarity_threshold = 0.3

    def _normalize_path(self, path: Union[str, Path]) -> Path:
        """
        标准化路径，确保使用正确的路径分隔符
        """
        return Path(str(path).replace('\\', os.sep)).resolve()

    def _ensure_path(self, path: Union[str, Path]) -> Path:
        """确保路径存在且格式正确"""
        path = self._normalize_path(path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        return path

    def _load_image(self, image_path: Union[str, Path]) -> np.ndarray:
        """安全地加载图片"""
        try:
            path = self._normalize_path(image_path)
            if not path.exists():
                raise FileNotFoundError(f"文件不存在: {path}")

            # 使用 cv2.imread 读取图片，处理中文路径
            img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"无法解码图片: {path}")
            return img
        except Exception as e:
            logger.error(f"图片加载失败: {str(e)}")
            raise

    def _save_image(self, image: np.ndarray, save_path: Union[str, Path]) -> bool:
        """安全地保存图片"""
        try:
            save_path = self._normalize_path(save_path)
            # 确保保存路径的父目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)

            is_success = cv2.imencode(save_path.suffix, image)[1].tofile(str(save_path))
            if is_success:
                logger.info(f"已保存图片到: {save_path}")
            return is_success
        except Exception as e:
            logger.error(f"保存图片失败: {str(e)}")
            return False

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """预处理图片以提高匹配精度"""
        # 统一大小
        img = cv2.resize(img, (64, 64))

        # 转换到HSV空间
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 去除边框的影响
        mask = np.ones(hsv.shape[:2], dtype=np.uint8) * 255
        mask[0:5, :] = 0  # 去除上边框
        mask[-5:, :] = 0  # 去除下边框
        mask[:, 0:5] = 0  # 去除左边框
        mask[:, -5:] = 0  # 去除右边框

        img = cv2.bitwise_and(img, img, mask=mask)
        return img

    def compare_images(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """改进的图像比较方法"""
        try:
            # 预处理
            img1 = self._preprocess_image(img1)
            img2 = self._preprocess_image(img2)

            # 1. 直方图相似度
            hist_scores = []
            for i in range(3):  # BGR三通道分别计算
                hist1 = cv2.calcHist([img1], [i], None, [64], [0, 256])
                hist2 = cv2.calcHist([img2], [i], None, [64], [0, 256])
                cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
                cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
                hist_scores.append(cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL))
            hist_score = np.mean(hist_scores)

            # 2. 结构相似度
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            ssim_score = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)[0][0]

            # 3. 边缘特征相似度
            edges1 = cv2.Canny(gray1, 100, 200)
            edges2 = cv2.Canny(gray2, 100, 200)
            edge_score = cv2.matchTemplate(edges1, edges2, cv2.TM_CCOEFF_NORMED)[0][0]

            # 加权平均
            final_score = (hist_score * 0.5 + ssim_score * 0.3 + edge_score * 0.2)
            return float(final_score)

        except Exception as e:
            logger.error(f"图片比较失败: {e}")
            return 0.0

    def identify_character(self, char_img: np.ndarray) -> Tuple[Optional[Dict], float]:
        """识别角色"""
        try:
            scores = []
            for char_id, char_info in tqdm(self.character_data.items(), desc="识别角色"):
                try:
                    ref_img = self._load_image(char_info['image_path'])
                    similarity = self.compare_images(char_img, ref_img)
                    scores.append((char_info, similarity))
                except Exception as e:
                    logger.warning(f"处理角色 {char_id} 时出错: {e}")
                    continue

            if not scores:
                return None, 0

            # 选择相似度最高的结果
            best_match = max(scores, key=lambda x: x[1])
            if best_match[1] > self.similarity_threshold:
                return best_match
            return None, best_match[1]

        except Exception as e:
            logger.error(f"角色识别失败: {e}")
            return None, 0

    def _merge_overlapping_boxes(self, boxes: List[Tuple], overlap_thresh: float = 0.3) -> List[Tuple]:
        """合并重叠的框"""
        if not boxes:
            return boxes

        boxes = np.array(boxes)
        pick = []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 0] + boxes[:, 2]
        y2 = boxes[:, 1] + boxes[:, 3]

        area = (x2 - x1) * (y2 - y1)
        idxs = np.argsort(y2)

        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)

            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])

            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            overlap = (w * h) / area[idxs[:last]]

            idxs = np.delete(idxs, np.concatenate(([last],
                                                   np.where(overlap > overlap_thresh)[0])))

        return boxes[pick].tolist()

    def detect_character_boxes(self, image_path: Union[str, Path],
                               output_path: Optional[Union[str, Path]] = None) -> Tuple[List, np.ndarray, List]:
        """检测角色框位置"""
        try:
            # 加载图片
            img = self._load_image(image_path)
            logger.info(f"成功读取图片，大小: {img.shape}")

            # 复制原图用于展示
            display_img = img.copy()

            # 转换到HSV色彩空间
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # 合并多个颜色范围的掩码
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in self.color_ranges:
                color_mask = cv2.inRange(hsv, lower, upper)
                mask = cv2.bitwise_or(mask, color_mask)

            # 形态学操作
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.morph_kernel,
                                    iterations=self.close_iterations)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.morph_kernel,
                                    iterations=self.open_iterations)
            mask = cv2.dilate(mask, self.morph_kernel, iterations=1)

            # 保存掩码图像用于调试
            if output_path:
                mask_debug_path = Path(output_path).parent / "mask_debug.png"
                self._save_image(mask, mask_debug_path)

            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 提取有效的角色框
            character_boxes = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if self.min_area < area < self.max_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = float(w) / h
                    if self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]:
                        character_boxes.append((x, y, w, h))

            # 合并重叠框并排序
            character_boxes = self._merge_overlapping_boxes(character_boxes)
            character_boxes.sort(key=lambda box: (box[1] // 50, box[0]))

            # 识别结果
            identified_results = []

            # 在图像上标注检测结果
            for i, (x, y, w, h) in enumerate(character_boxes, 1):
                # 裁剪角色图片
                char_img = img[y:y + h, x:x + w]

                # 识别角色
                char_info, similarity = self.identify_character(char_img)

                result = {
                    'position': i,
                    'box': (x, y, w, h),
                    'character': char_info['name'] if char_info else 'Unknown',
                    'similarity': similarity
                }
                identified_results.append(result)

                # 在图像上显示识别结果
                cv2.rectangle(display_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                label = f"#{i} {result['character']}"
                if similarity > 0:
                    label += f" ({similarity:.2f})"
                cv2.putText(display_img, label, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 显示总数
            cv2.putText(display_img, f"Total: {len(character_boxes)} characters",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 保存结果图像
            if output_path:
                output_path = self._normalize_path(output_path)
                self._save_image(display_img, output_path)
                logger.info(f"已保存检测结果到: {output_path}")

                # 保存识别结果到JSON
                json_path = output_path.parent / 'recognition_results.json'
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(identified_results, f, ensure_ascii=False, indent=2)
                logger.info(f"识别结果已保存到 {json_path}")

            return character_boxes, display_img, identified_results

        except Exception as e:
            logger.error(f"检测失败: {str(e)}", exc_info=True)
            return [], None, []


def main():
    """主函数"""
    try:
        # 使用 Path 对象处理路径
        base_dir = Path(__file__).parent
        character_data_path = base_dir / 'pcr_db.json'

        if not character_data_path.exists():
            logger.error("找不到角色数据库文件")
            return

        with open(character_data_path, 'r', encoding='utf-8') as f:
            character_data = json.load(f)

            # 标准化角色数据中的图片路径
            for char_id, char_info in character_data.items():
                if 'image_path' in char_info:
                    char_info['image_path'] = str(base_dir / char_info['image_path'])

        logger.info(f"成功加载角色数据库，包含 {len(character_data)} 个角色")

        # 设置输入输出路径
        input_path = base_dir / "screenshot.png"
        output_path = base_dir / "detected_boxes.png"

        # 创建检测器并处理
        detector = CharacterGridDetector(character_data)
        boxes, result_img, identified_results = detector.detect_character_boxes(input_path, output_path)

        if not boxes:
            logger.warning("未检测到任何角色框！")
            return

        # 打印识别结果
        print("\n角色识别结果:")
        print("-" * 50)
        for result in identified_results:
            print(f"位置 #{result['position']}: {result['character']}", end='')
            if result['similarity'] > 0:
                print(f" (相似度: {result['similarity']:.2f})")
            else:
                print(" (未识别)")
        print("-" * 50)

    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()