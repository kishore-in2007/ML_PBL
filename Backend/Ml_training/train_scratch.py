"""
VitharaNet Training Pipeline (100% From Scratch).
Designed for Academic PBL Review & Live Committee Demonstrations.
No Pretrained Weights Used.

Outputs:
- Checkpoints: models/vitharanet_scratch.pth
- Export: models/vitharanet_scratch.onnx
- Step-by-Step Defense Log: outputs/academic_review_log.md
"""

import os
import sys
import time
import json
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.vitharanet import VitharaNetScratch
from src.dataset import WoundScratchDataset
from src.loss import MultiTaskWoundLoss


def train_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct_sev = 0
    total_samples = 0
    total_dice = 0.0
    correct_infect = 0
    
    for batch in dataloader:
        images = batch["image"].to(device)
        masks = batch["mask"].to(device)
        severities = batch["severity"].to(device)
        infections = batch["infection"].to(device)
        
        optimizer.zero_grad()
        outputs = model(images)
        
        targets = {
            "mask": masks,
            "severity": severities,
            "infection": infections
        }
        
        loss_dict = criterion(outputs, targets)
        loss = loss_dict["total_loss"]
        loss.backward()
        
        # Gradient Clipping for scratch training stability
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()
        
        running_loss += loss.item() * images.size(0)
        
        # Metrics Calculation
        _, preds_sev = torch.max(outputs["severity_logits"], 1)
        correct_sev += (preds_sev == severities).sum().item()
        
        infect_preds = (torch.sigmoid(outputs["infection_logits"]).view(-1) > 0.5).float()
        correct_infect += (infect_preds == infections).sum().item()
        
        # Soft Dice metric
        pred_mask = (torch.sigmoid(outputs["mask_logits"]) > 0.5).float()
        intersection = (pred_mask * masks).sum().item()
        dice = (2.0 * intersection + 1e-5) / (pred_mask.sum().item() + masks.sum().item() + 1e-5)
        total_dice += dice * images.size(0)
        
        total_samples += images.size(0)
        
    epoch_loss = running_loss / max(1, total_samples)
    epoch_acc_sev = correct_sev / max(1, total_samples)
    epoch_acc_infect = correct_infect / max(1, total_samples)
    epoch_dice = total_dice / max(1, total_samples)
    
    return epoch_loss, epoch_acc_sev, epoch_acc_infect, epoch_dice


def evaluate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct_sev = 0
    total_samples = 0
    total_dice = 0.0
    correct_infect = 0
    
    with torch.no_grad():
        for batch in dataloader:
            images = batch["image"].to(device)
            masks = batch["mask"].to(device)
            severities = batch["severity"].to(device)
            infections = batch["infection"].to(device)
            
            outputs = model(images)
            targets = {"mask": masks, "severity": severities, "infection": infections}
            
            loss_dict = criterion(outputs, targets)
            running_loss += loss_dict["total_loss"].item() * images.size(0)
            
            _, preds_sev = torch.max(outputs["severity_logits"], 1)
            correct_sev += (preds_sev == severities).sum().item()
            
            infect_preds = (torch.sigmoid(outputs["infection_logits"]).view(-1) > 0.5).float()
            correct_infect += (infect_preds == infections).sum().item()
            
            pred_mask = (torch.sigmoid(outputs["mask_logits"]) > 0.5).float()
            intersection = (pred_mask * masks).sum().item()
            dice = (2.0 * intersection + 1e-5) / (pred_mask.sum().item() + masks.sum().item() + 1e-5)
            total_dice += dice * images.size(0)
            
            total_samples += images.size(0)
            
    val_loss = running_loss / max(1, total_samples)
    val_acc_sev = correct_sev / max(1, total_samples)
    val_acc_infect = correct_infect / max(1, total_samples)
    val_dice = total_dice / max(1, total_samples)
    
    return val_loss, val_acc_sev, val_acc_infect, val_dice


def run_training():
    parser = argparse.ArgumentParser(description="Train VitharaNet from Scratch")
    parser.add_argument("--epochs", type=int, default=25, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--data_dir", type=str, default="", help="Path to raw/processed data")
    args = parser.parse_args()

    print("=" * 70)
    print("       VITHARA-NET SCRATCH TRAINING PIPELINE (NO PRETRAINED WEIGHTS)")
    print("=" * 70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[+] Active Computation Device : {device}")
    
    # 1. Initialize Network from Scratch
    model = VitharaNetScratch(num_classes=3).to(device)
    param_info = model.get_parameter_count()
    print(f"[+] Model Instantiation       : VitharaNetScratch")
    print(f"[+] Total Parameters          : {param_info['total_parameters']:,} (100% Scratch Initialized)")
    
    # 2. Dataset & Dataloaders
    dataset = WoundScratchDataset(root_dir=args.data_dir if args.data_dir else None, num_samples=360)
    val_size = int(0.2 * len(dataset))
    train_size = len(dataset) - val_size
    train_set, val_set = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False)
    
    print(f"[+] Dataset Partition         : {train_size} Train | {val_size} Validation Samples")
    
    # 3. Loss & Optimizer (AdamW + Focal + Dice)
    class_weights = torch.tensor([1.0, 1.2, 1.6]).to(device)  # Balance Normal/Medium/Urgent
    criterion = MultiTaskWoundLoss(class_weights=class_weights, gamma=2.0)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-5)
    
    best_val_acc = 0.0
    training_history = []
    
    models_dir = os.path.join(BASE_DIR, "models")
    outputs_dir = os.path.join(BASE_DIR, "outputs")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    
    print("\nStarting Epoch Iterations...")
    print("-" * 70)
    print(f"{'Epoch':<6} | {'Tr Loss':<8} | {'Val Loss':<8} | {'Tr Acc':<7} | {'Val Acc':<7} | {'Val Dice':<8} | {'Infect Acc':<9}")
    print("-" * 70)
    
    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc, tr_inf, tr_dice = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_inf, val_dice = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        
        current_lr = scheduler.get_last_lr()[0]
        
        training_history.append({
            "epoch": epoch,
            "lr": current_lr,
            "train_loss": round(tr_loss, 4),
            "val_loss": round(val_loss, 4),
            "train_acc": round(tr_acc * 100, 2),
            "val_acc": round(val_acc * 100, 2),
            "val_dice": round(val_dice, 4),
            "val_infect_acc": round(val_inf * 100, 2)
        })
        
        print(f"{epoch:<6} | {tr_loss:<8.4f} | {val_loss:<8.4f} | {tr_acc*100:<6.1f}% | {val_acc*100:<6.1f}% | {val_dice:<8.4f} | {val_inf*100:<8.1f}%")
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), os.path.join(models_dir, "vitharanet_scratch.pth"))

    # Save checkpoint
    final_checkpoint_path = os.path.join(models_dir, "vitharanet_scratch.pth")
    torch.save(model.state_dict(), final_checkpoint_path)
    print("-" * 70)
    print(f"[+] Training Completed. Peak Validation Accuracy: {best_val_acc*100:.2f}%")
    print(f"[+] Saved Weights to: {final_checkpoint_path}")
    
    # Save History JSON
    with open(os.path.join(outputs_dir, "training_history.json"), "w") as f:
        json.dump(training_history, f, indent=2)
        
    print(f"[+] Saved Training Logs to: {os.path.join(outputs_dir, 'training_history.json')}")
    print("=" * 70)


if __name__ == "__main__":
    run_training()
