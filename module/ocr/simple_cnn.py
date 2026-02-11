"""
Simple CNN model inference for timer recognition
Achieves 100% accuracy on timer values (0:00 to 1:30)
"""

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np
from pathlib import Path


class SimpleCNN(nn.Module):
    """Lightweight CNN for timer OCR"""
    def __init__(self, num_classes, seq_len):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4))
        )
        
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes * seq_len)
        )
        
        self.num_classes = num_classes
        self.seq_len = seq_len
    
    def forward(self, x):
        x = self.conv(x)
        x = self.fc(x)
        x = x.view(-1, self.seq_len, self.num_classes)
        return x


class SimpleCNNOCR:
    """Simple CNN-based OCR for timer recognition"""
    
    def __init__(self, model_path='timer_cnn_best.pth'):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Load char mappings
        self.char2idx = checkpoint['char2idx']
        self.idx2char = checkpoint['idx2char']
        self.max_len = checkpoint['max_len']
        
        # Initialize model
        self.model = SimpleCNN(
            num_classes=len(self.char2idx) + 1,
            seq_len=self.max_len
        ).to(self.device)
        
        # Load weights
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        # Transform
        self.transform = transforms.Compose([
            transforms.Resize((32, 64)),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])
        ])
        
        print(f"SimpleCNN OCR loaded (accuracy: {checkpoint['val_seq_acc']:.2f}%)")
    
    def init(self):
        """空的初始化方法，兼容CnOcrEngine接口"""
        pass
    
    def recognize(self, image):
        """
        Recognize text from image
        
        Args:
            image: PIL Image or numpy array
        
        Returns:
            str: Recognized text (e.g., "0:12", "1:30")
        """
        # Preprocess (Grayscale only)
        image = self._preprocess(image)
        
        # Transform
        img_tensor = self.transform(image).unsqueeze(0).to(self.device)
        
        # Inference
        with torch.no_grad():
            output = self.model(img_tensor)
            predictions = torch.argmax(output, dim=-1)[0]
        
        # Decode
        result = []
        for idx in predictions:
            idx = idx.item()
            if idx < len(self.char2idx):
                # idx2char keys might be int or str, handle both
                char = self.idx2char.get(idx) or self.idx2char.get(str(idx))
                if char:
                    result.append(char)
            else:
                break  # Stop at padding
        
        return ''.join(result)
    
    def _preprocess(self, image):
        """
        Preprocess image: Grayscale only (No thresholding as CNN learns better from raw gray)
        """
        import cv2
        import numpy as np
        
        # Convert PIL to Numpy
        if isinstance(image, Image.Image):
            img_np = np.array(image)
        else:
            img_np = image
            
        # Grayscale
        if len(img_np.shape) == 3:
            # Check RGB or BGR? PIL is usually RGB.
            # Handle both just in case, but assume RGB for now or use split
            # cv2.cvtColor requires numpy array
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
            
        # No thresholding! Training was done on Grayscale.
        # _, binary = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
        
        return Image.fromarray(gray)

    def atomic_ocr_for_single_lines(self, img_list, cand_alphabet=None):
        """
        批量识别单行文本 (兼容 CnOcrEngine接口)
        
        Args:
            img_list: numpy数组列表或PIL图片列表
            cand_alphabet: 候选字符集(忽略,SimpleCNN已优化)
        
        Returns:
            识别结果列表,每个元素是字符列表
        """
        results = []
        for img in img_list:
            text = self.recognize(img)
            # 返回字符列表格式以匹配CnOcrEngine
            results.append(list(text))
        return results


def main():
    """Test the OCR model"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_cnn.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Initialize OCR
    ocr = SimpleCNNOCR('timer_cnn_best.pth')
    
    # Load image
    image = Image.open(image_path)
    
    # Recognize
    result = ocr.recognize(image)
    print(f"Recognized: {result}")


if __name__ == "__main__":
    main()
