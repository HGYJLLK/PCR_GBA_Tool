
import sys
import os
import torch
from pathlib import Path
from PIL import Image

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from module.ocr.simple_cnn import SimpleCNNOCR

def main():
    # Path to finetuned model
    model_path = project_root / "module" / "ocr" / "timer_cnn_finetuned.pth"
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        return

    print(f"Loading model from {model_path}")
    ocr = SimpleCNNOCR(str(model_path))

    # Path to images
    img_dir = project_root / "training_data" / "manual_errors" / "images"
    if not img_dir.exists():
        print(f"Error: Image directory not found at {img_dir}")
        return

    images = sorted(list(img_dir.glob("*.png")))
    if not images:
        print("No images found.")
        return

    print(f"Found {len(images)} images. Testing first 10...")
    
    correct_count = 0
    total_count = 0

    # Also try to read labels.txt to check accuracy if available
    labels_map = {}
    labels_file = project_root / "training_data" / "manual_errors" / "labels.txt"
    if labels_file.exists():
        with open(labels_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    # Key: remove 'images/' prefix if present
                    key = parts[0].replace("images/", "")
                    # Value: remove spaces
                    val = parts[1].replace(" ", "")
                    labels_map[key] = val

    for i, img_path in enumerate(images[:20]):
        try:
            img = Image.open(img_path)
        except Exception:
            continue
            
        # OCR
        pred_raw = ocr.recognize(img)
        pred = pred_raw.replace(" ", "")
        
        # Check label
        label = labels_map.get(img_path.name, "???")
        
        match_mark = "✔" if pred == label else "✘"
        if pred == label:
            correct_count += 1
        total_count += 1
        
        print(f"[{i+1:02d}] {img_path.name} -> Pred: {pred} | Truth: {label}  {match_mark}")

    if total_count > 0:
        print(f"\nAccuracy on sample: {correct_count}/{total_count} ({correct_count/total_count:.2%})")

if __name__ == "__main__":
    main()
