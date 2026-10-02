"""
Empirical Accuracy and Metrics Evaluation Script for VitharaNet-Scratch.
Computes test metrics across all three multi-task heads.
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import torch
import numpy as np
from torch.utils.data import DataLoader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.vitharanet import VitharaNetScratch
from src.dataset import WoundScratchDataset
from src.loss import MultiTaskWoundLoss


def run_comprehensive_evaluation():
    checkpoint_path = os.path.join(BASE_DIR, "models", "vitharanet_scratch.pth")
    if not os.path.exists(checkpoint_path):
        checkpoint_path = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "vitharanet_scratch.pth"))
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = VitharaNetScratch(num_classes=3).to(device)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.eval()
    
    # Evaluate on clean unseen test distribution (500 samples)
    test_dataset = WoundScratchDataset(split='val', num_samples=500, augment=False)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
    
    total_samples = 0
    correct_sev = 0
    correct_infect = 0
    total_dice = 0.0
    total_iou = 0.0
    
    # Class-wise metrics
    class_correct = [0, 0, 0]
    class_total = [0, 0, 0]
    
    # Infection metrics
    tp_inf, fp_inf, tn_inf, fn_inf = 0, 0, 0, 0
    
    with torch.no_grad():
        for batch in test_loader:
            images = batch["image"].to(device)
            masks = batch["mask"].to(device)
            severities = batch["severity"].to(device)
            infections = batch["infection"].to(device)
            
            outputs = model(images)
            
            # 1. Severity Accuracy
            preds_sev = torch.argmax(outputs["severity_logits"], dim=1)
            correct_sev += (preds_sev == severities).sum().item()
            
            for i in range(len(severities)):
                label = severities[i].item()
                pred = preds_sev[i].item()
                class_total[label] += 1
                if label == pred:
                    class_correct[label] += 1
                    
            # 2. Infection Metrics
            preds_inf = (torch.sigmoid(outputs["infection_logits"]).view(-1) > 0.5).float()
            correct_infect += (preds_inf == infections).sum().item()
            
            for i in range(len(infections)):
                act = infections[i].item()
                pr = preds_inf[i].item()
                if act == 1 and pr == 1:
                    tp_inf += 1
                elif act == 0 and pr == 1:
                    fp_inf += 1
                elif act == 0 and pr == 0:
                    tn_inf += 1
                elif act == 1 and pr == 0:
                    fn_inf += 1
                    
            # 3. Segmentation Dice & IoU
            pred_mask = (torch.sigmoid(outputs["mask_logits"]) > 0.5).float()
            inter = (pred_mask * masks).sum(dim=(1, 2, 3)).cpu().numpy()
            union_dice = pred_mask.sum(dim=(1, 2, 3)).cpu().numpy() + masks.sum(dim=(1, 2, 3)).cpu().numpy()
            dice = (2.0 * inter + 1e-5) / (union_dice + 1e-5)
            
            union_iou = union_dice - inter
            iou = (inter + 1e-5) / (union_iou + 1e-5)
            
            total_dice += dice.sum()
            total_iou += iou.sum()
            total_samples += images.size(0)
            
    overall_sev_acc = (correct_sev / total_samples) * 100
    overall_inf_acc = (correct_infect / total_samples) * 100
    mean_dice = total_dice / total_samples
    mean_iou = total_iou / total_samples
    
    inf_sensitivity = (tp_inf / max(1, tp_inf + fn_inf)) * 100
    inf_specificity = (tn_inf / max(1, tn_inf + fp_inf)) * 100
    
    metrics_summary = {
        "overall_severity_accuracy": round(overall_sev_acc, 2),
        "normal_class_accuracy": round((class_correct[0] / max(1, class_total[0])) * 100, 2),
        "medium_class_accuracy": round((class_correct[1] / max(1, class_total[1])) * 100, 2),
        "urgent_class_accuracy": round((class_correct[2] / max(1, class_total[2])) * 100, 2),
        "infection_detection_accuracy": round(overall_inf_acc, 2),
        "infection_sensitivity": round(inf_sensitivity, 2),
        "infection_specificity": round(inf_specificity, 2),
        "segmentation_dice_coefficient": round(mean_dice, 4),
        "segmentation_mean_iou": round(mean_iou, 4)
    }
    
    print("\n" + "=" * 70)
    print("        📊 VITHARA-NET EMPIRICAL ACCURACY & PERFORMANCE REPORT")
    print("=" * 70)
    print(f"[*] Total Test Samples Evaluated : {total_samples}")
    print("\n--- 1. WOUND SEVERITY CLASSIFICATION (3-TIER) ---")
    print(f" -> Overall Severity Accuracy   : {overall_sev_acc:.2f}%")
    print(f" -> 'Normal' Class Accuracy     : {metrics_summary['normal_class_accuracy']:.2f}%")
    print(f" -> 'Medium' Class Accuracy     : {metrics_summary['medium_class_accuracy']:.2f}%")
    print(f" -> 'Urgent' Class Accuracy     : {metrics_summary['urgent_class_accuracy']:.2f}%")
    
    print("\n--- 2. INFECTION & ERYTHEMA DETECTION ---")
    print(f" -> Infection Accuracy          : {overall_inf_acc:.2f}%")
    print(f" -> Infection Sensitivity       : {inf_sensitivity:.2f}% (True Positive Recall)")
    print(f" -> Infection Specificity       : {inf_specificity:.2f}% (True Negative Rate)")
    
    print("\n--- 3. WOUND SEGMENTATION & AREA ESTIMATION ---")
    print(f" -> Soft Dice Similarity Coeff  : {mean_dice:.4f} (~{mean_dice*100:.1f}%)")
    print(f" -> Mean Intersection-over-Union: {mean_iou:.4f} (~{mean_iou*100:.1f}%)")
    print("=" * 70 + "\n")
    
    return metrics_summary


if __name__ == "__main__":
    run_comprehensive_evaluation()
