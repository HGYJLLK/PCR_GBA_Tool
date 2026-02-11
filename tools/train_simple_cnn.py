"""
Simple CNN Training for Timer Recognition
Only 11 characters (0-9 and :), should easily reach 100% accuracy
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import os
from pathlib import Path

# ========== Dataset ==========
class TimerDataset(Dataset):
    def __init__(self, data_dirs, transform=None):
        self.transform = transform
        self.samples = []
        
        # Load labels from all directories
        for data_dir in data_dirs:
            data_dir = Path(data_dir)
            labels_file = data_dir / "labels.txt"
            # Some datasets might use 'images' subfolder, some might be flat. 
            # Based on previous code: 
            # - manual_errors: labels.txt, images/ 
            # - timer_manual...: labels.txt, images/
            # We will assume images are in the same dir as labels.txt or in 'images' subdir
            # BUT: the labels.txt content usually has 'images/filename' or just 'filename'.
            # Let's inspect how previous code handled it.
            # Previous: img_path = self.img_dir / img_name
            # where img_dir was data_dir.
            # So if labels.txt has "images/debug_001.png", it joins data_dir/images/debug_001.png.
            
            if not labels_file.exists():
                print(f"Warning: Labels file not found at {labels_file}, skipping.")
                continue
                
            print(f"Loading data from {data_dir}")
            with open(labels_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split('\t')
                    if len(parts) != 2:
                        continue
                    img_name, label = parts
                    # Store (absolute_img_path, label)
                    img_path = data_dir / img_name
                    if not img_path.exists():
                         # Try adding 'images' if not already in path
                         if 'images' not in img_name:
                             img_path = data_dir / 'images' / img_name
                    
                    if img_path.exists():
                        self.samples.append((str(img_path), label))
                    else:
                        # print(f"Warning: Image not found: {img_path}")
                        pass
        
        if not self.samples:
            raise RuntimeError("No valid samples found in any of the provided directories!")

        # Create character to index mapping
        chars = set()
        for _, label in self.samples:
            chars.update(label)
        self.char2idx = {char: idx for idx, char in enumerate(sorted(chars))}
        self.idx2char = {idx: char for char, idx in self.char2idx.items()}
        self.max_len = max(len(label) for _, label in self.samples)
        
        print(f"Total dataset loaded: {len(self.samples)} samples")
        print(f"Characters: {sorted(self.char2idx.keys())}")
        print(f"Max sequence length: {self.max_len}")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        
        # Load image
        image = Image.open(img_path).convert('L')  # Grayscale
        if self.transform:
            image = self.transform(image)
        
        # Encode label
        label_encoded = [self.char2idx[c] for c in label]
        # Pad to max_len
        label_encoded += [len(self.char2idx)] * (self.max_len - len(label))
        
        return image, torch.tensor(label_encoded), torch.tensor(len(label))


# ========== Model ==========
class SimpleCNN(nn.Module):
    def __init__(self, num_classes, seq_len):
        super().__init__()
        # Convolutional layers
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
        
        # FC layers for sequence prediction
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


# ========== Training ==========
def train_model():
    import argparse
    
    parser = argparse.ArgumentParser(description="Train or Fine-tune OCR CNN")
    parser.add_argument("--data_dir", type=str, default=r"training_data/manual_errors", help="Directory containing labels.txt and images/")
    parser.add_argument("--base_model", type=str, default="module/ocr/timer_cnn_best.pth", help="Path to pretrained model to fine-tune from")
    parser.add_argument("--epochs", type=int, default=1000, help="Number of epochs")
    parser.add_argument("--patience", type=int, default=100, help="Early stopping patience")
    parser.add_argument("--lr", type=float, default=0.0001, help="Learning rate")
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    
    # Define data directories
    # 1. New manual errors
    new_data_dir = project_root / args.data_dir
    # 2. Original training data (hardcoded for now as it's outside project sometimes or fixed path)
    original_data_dir = Path(r"C:\Users\wdnmd\Desktop\PCR_GBA_Tool\train_data\timer_manual_20251129_143812")
    
    img_dirs = [new_data_dir, original_data_dir]
    
    # Hyperparameters
    batch_size = 32 # Smaller batch for small dataset
    epochs = args.epochs
    learning_rate = args.lr
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Data transforms with augmentation for small dataset
    transform = transforms.Compose([
        transforms.Resize((32, 64)), # Update to match model input size if needed, assuming 32x64 or similar based on model arch
        # Add augmentation to prevent overfitting on small dataset
        transforms.RandomApply([transforms.ColorJitter(brightness=0.2, contrast=0.2)], p=0.5),
        transforms.RandomAffine(degrees=2, translate=(0.02, 0.02), scale=(0.98, 1.02)),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5])
    ])
    
    # Load dataset
    dataset = TimerDataset(img_dirs, transform=transform)
    
    # Train/Val split (80/20 for small dataset)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42) # Fixed seed for reproducibility
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    # Model
    model = SimpleCNN(
        num_classes=len(dataset.char2idx) + 1,  # +1 for padding
        seq_len=dataset.max_len
    ).to(device)
    
    # Try to load pretrained model
    # Priority: 
    # 1. Command line argument
    # 2. Previously finetuned model (module/ocr/timer_cnn_finetuned.pth)
    # 3. Original best model in root (timer_cnn_best.pth)
    
    potential_paths = [
        project_root / args.base_model,
        project_root / "module" / "ocr" / "timer_cnn_finetuned.pth",
        project_root / "timer_cnn_best.pth"
    ]
    
    pretrained_path = None
    for p in potential_paths:
        if p.exists():
            pretrained_path = p
            break
            
    if pretrained_path:
        print(f"Loading pretrained model from {pretrained_path}")
        checkpoint = torch.load(pretrained_path, map_location=device)
        try:
            # Check for compatibility
            saved_char2idx = checkpoint.get('char2idx')
            if saved_char2idx and saved_char2idx != dataset.char2idx:
                 print("Warning: Character mapping mismatch!")
                 print(f"Saved: {saved_char2idx}")
                 print(f"Current: {dataset.char2idx}")
                 print("Proceeding carefully... (New characters might be initialized randomly or cause size mismatch)")
            
            model.load_state_dict(checkpoint['model_state_dict'], strict=False)
            print("Pretrained weights loaded successfully (strict=False)!")
        except Exception as e:
            print(f"Could not load pretrained weights: {e}")
            print("Training from scratch...")
    else:
        print(f"No pretrained model found in searched paths. Training from scratch...")
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss(ignore_index=len(dataset.char2idx))
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=10)
    
    print(f"\nTraining on {device}")
    print(f"Total samples: {len(dataset)}")
    print(f"Train samples: {train_size}, Val samples: {val_size}")
    
    best_val_acc = 0.0
    best_epoch = 0
    patience_counter = 0
    
    # Training loop
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for images, labels, lengths in train_loader:
            images = images.to(device)
            labels = labels.to(device)
            
            # Forward
            outputs = model(images)
            loss = criterion(outputs.reshape(-1, outputs.size(-1)), labels.reshape(-1))
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # Metrics
            train_loss += loss.item()
            predictions = torch.argmax(outputs, dim=-1)
            train_correct += ((predictions == labels) & (labels != len(dataset.char2idx))).sum().item()
            train_total += (labels != len(dataset.char2idx)).sum().item()
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        val_seq_correct = 0
        
        with torch.no_grad():
            for images, labels, lengths in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                
                outputs = model(images)
                loss = criterion(outputs.reshape(-1, outputs.size(-1)), labels.reshape(-1))
                
                val_loss += loss.item()
                predictions = torch.argmax(outputs, dim=-1)
                
                # Character accuracy
                val_correct += ((predictions == labels) & (labels != len(dataset.char2idx))).sum().item()
                val_total += (labels != len(dataset.char2idx)).sum().item()
                
                # Sequence accuracy
                for i in range(len(labels)):
                    # Handle padding index (dataset.char2idx length)
                    padding_idx = len(dataset.char2idx)
                    
                    pred_indices = predictions[i][:lengths[i]]
                    pred_str = ''.join([dataset.idx2char[p.item()] for p in pred_indices if p.item() != padding_idx])
                    
                    true_indices = labels[i][:lengths[i]]
                    true_str = ''.join([dataset.idx2char[l.item()] for l in true_indices if l.item() != padding_idx])
                    
                    if pred_str == true_str:
                        val_seq_correct += 1
        
        # Calculate metrics
        train_loss /= len(train_loader) if len(train_loader) > 0 else 1
        train_acc = 100 * train_correct / train_total if train_total > 0 else 0
        val_loss /= len(val_loader) if len(val_loader) > 0 else 1
        val_acc = 100 * val_correct / val_total if val_total > 0 else 0
        val_seq_acc = 100 * val_seq_correct / val_size if val_size > 0 else 0
        
        # Learning rate scheduling
        scheduler.step(val_loss)
        
        # Print progress
        print(f"Epoch [{epoch+1}/{epochs}] "
              f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}% | "
              f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%, "
              f"Seq Acc: {val_seq_acc:.2f}%")
        
        # Save best model
        if val_seq_acc >= best_val_acc: # Save even if equal to update latest
            best_val_acc = val_seq_acc
            best_epoch = epoch
            patience_counter = 0 # Reset patience
            save_path = project_root / 'module' / 'ocr' / 'timer_cnn_finetuned.pth'
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_seq_acc': val_seq_acc,
                'char2idx': dataset.char2idx,
                'idx2char': dataset.idx2char,
                'max_len': dataset.max_len,
            }, save_path)
            print(f"  -> Best model saved to {save_path}! Seq Acc: {best_val_acc:.2f}%")
        else:
            patience_counter += 1
            print(f"  -> No improvement. Patience: {patience_counter}/{args.patience}")
            
        # Early stopping
        if patience_counter >= args.patience:
            print(f"\nEarly stopping triggered! No improvement for {args.patience} epochs.")
            print(f"Best validation sequence accuracy: {best_val_acc:.2f}% at epoch {best_epoch+1}")
            break
            
    if patience_counter < args.patience:
        print(f"\nTraining complete (max epochs reached)! Best validation sequence accuracy: {best_val_acc:.2f}%")
    return model, dataset


if __name__ == "__main__":
    model, dataset = train_model()
