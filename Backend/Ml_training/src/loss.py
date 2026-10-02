"""
Custom Loss Functions for VitharaNet-Scratch Multi-Task Learning.
Includes:
- Multi-Class Focal Loss (handles class imbalance for Urgent/necrotic wounds)
- Soft Dice Loss (ensures crisp wound boundary segmentation)
- Joint Multi-Task Loss with dynamic task weighting
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """
    Multi-Class Focal Loss to address extreme class imbalance:
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    """
    def __init__(self, alpha=None, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha  # Tensor of class weights if provided
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = ((1.0 - pt) ** self.gamma) * ce_loss
        
        if self.alpha is not None:
            if self.alpha.device != inputs.device:
                self.alpha = self.alpha.to(inputs.device)
            at = self.alpha.gather(0, targets.data.view(-1))
            focal_loss = at * focal_loss
            
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        return focal_loss


class DiceLoss(nn.Module):
    """Soft Dice Loss for Binary Segmentation."""
    def __init__(self, smooth=1e-5):
        super(DiceLoss, self).__init__()
        self.smooth = smooth

    def forward(self, logits, targets):
        probs = torch.sigmoid(logits)
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)
        
        intersection = (probs_flat * targets_flat).sum()
        dice = (2.0 * intersection + self.smooth) / (probs_flat.sum() + targets_flat.sum() + self.smooth)
        return 1.0 - dice


class MultiTaskWoundLoss(nn.Module):
    """
    Combined loss for simultaneous optimization of:
    1. Severity Classification (Focal Loss)
    2. Wound Segmentation (Dice Loss + BCE Loss)
    3. Infection Detection (Binary Cross-Entropy Loss)
    """
    def __init__(self, class_weights=None, gamma=2.0, w_sev=1.0, w_dice=1.5, w_bce_mask=0.8, w_infect=1.2):
        super(MultiTaskWoundLoss, self).__init__()
        self.focal_sev = FocalLoss(alpha=class_weights, gamma=gamma)
        self.dice_mask = DiceLoss()
        self.bce_mask = nn.BCEWithLogitsLoss()
        self.bce_infect = nn.BCEWithLogitsLoss()
        
        self.w_sev = w_sev
        self.w_dice = w_dice
        self.w_bce_mask = w_bce_mask
        self.w_infect = w_infect

    def forward(self, predictions, targets):
        # 1. Severity Loss
        loss_sev = self.focal_sev(predictions["severity_logits"], targets["severity"])
        
        # 2. Mask Segmentation Loss
        loss_dice = self.dice_mask(predictions["mask_logits"], targets["mask"])
        loss_bce_m = self.bce_mask(predictions["mask_logits"], targets["mask"])
        loss_seg = (self.w_dice * loss_dice) + (self.w_bce_mask * loss_bce_m)
        
        # 3. Infection Detection Loss
        loss_infect = self.bce_infect(predictions["infection_logits"].view(-1), targets["infection"].float())
        
        # Total Weighted Multi-Task Loss
        total_loss = (self.w_sev * loss_sev) + loss_seg + (self.w_infect * loss_infect)
        
        return {
            "total_loss": total_loss,
            "loss_severity": loss_sev,
            "loss_dice": loss_dice,
            "loss_mask_bce": loss_bce_m,
            "loss_infection": loss_infect
        }
