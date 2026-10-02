"""
VitharaNet-Scratch: Custom Multi-Task Convolutional Architecture
Trained 100% from Scratch (No pre-trained weights or transfer learning).
Designed for Academic PBL Review & Clinical Decision Support.

Outputs:
1. Wound Segmentation Mask (1 x H x W) - Pixel boundary & area estimation.
2. Wound Severity (3 classes: 0=Normal, 1=Medium, 2=Urgent).
3. Infection Risk Score (0.0 to 1.0) - Perilesional redness & bacterial risk.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBlock(nn.Module):
    """Double Convolution Block with BatchNorm and LeakyReLU."""
    def __init__(self, in_channels, out_channels):
        super(ConvBlock, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.1, inplace=True)
        )

    def forward(self, x):
        return self.conv(x)


class DownBlock(nn.Module):
    """Downscaling block: MaxPool followed by ConvBlock."""
    def __init__(self, in_channels, out_channels):
        super(DownBlock, self).__init__()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.conv = ConvBlock(in_channels, out_channels)

    def forward(self, x):
        return self.conv(self.pool(x))


class UpBlock(nn.Module):
    """Upscaling block: Transpose Conv followed by concatenation with skip connection and ConvBlock."""
    def __init__(self, in_channels, skip_channels, out_channels):
        super(UpBlock, self).__init__()
        self.up = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=2, stride=2)
        self.conv = ConvBlock(out_channels + skip_channels, out_channels)

    def forward(self, x, skip):
        x_up = self.up(x)
        # Pad if needed due to odd dimensions
        diff_y = skip.size()[2] - x_up.size()[2]
        diff_x = skip.size()[3] - x_up.size()[3]
        if diff_y != 0 or diff_x != 0:
            x_up = F.pad(x_up, [diff_x // 2, diff_x - diff_x // 2,
                                diff_y // 2, diff_y - diff_y // 2])
        x_cat = torch.cat([skip, x_up], dim=1)
        return self.conv(x_cat)


class VitharaNetScratch(nn.Module):
    """
    Multi-Branch Deep Network built from Scratch:
    - Backbone: 4-stage Hierarchical Feature Extractor (32 -> 64 -> 128 -> 256 channels)
    - Branch 1 (Segmentation): Skip-connected U-Net Decoder (Outputs 1x256x256 binary mask logits)
    - Branch 2 (Severity Classification): Global Pooling + Dense Layers (Outputs 3 classes: Normal, Medium, Urgent)
    - Branch 3 (Infection Assessment): Dedicated Dense Head (Outputs 1 infection probability logit)
    """
    def __init__(self, num_classes=3, in_channels=3):
        super(VitharaNetScratch, self).__init__()
        
        # --- ENCODER BACKBONE (From Scratch) ---
        self.enc1 = ConvBlock(in_channels, 32)      # Output: 32 x 256 x 256
        self.enc2 = DownBlock(32, 64)               # Output: 64 x 128 x 128
        self.enc3 = DownBlock(64, 128)              # Output: 128 x 64 x 64
        self.enc4 = DownBlock(128, 256)             # Output: 256 x 32 x 32
        
        # Bottleneck
        self.bottleneck = nn.Sequential(
            nn.MaxPool2d(kernel_size=2, stride=2),   # Output: 256 x 16 x 16
            ConvBlock(256, 512),                    # Output: 512 x 16 x 16
            nn.Dropout2d(0.3)
        )
        
        # --- BRANCH 1: SEGMENTATION DECODER ---
        self.dec4 = UpBlock(512, 256, 256)          # Output: 256 x 32 x 32
        self.dec3 = UpBlock(256, 128, 128)          # Output: 128 x 64 x 64
        self.dec2 = UpBlock(128, 64, 64)            # Output: 64 x 128 x 128
        self.dec1 = UpBlock(64, 32, 32)             # Output: 32 x 256 x 256
        self.mask_head = nn.Conv2d(32, 1, kernel_size=1)  # Output: 1 x 256 x 256
        
        # --- BRANCH 2 & 3: CLASSIFICATION & INFECTION BACKBONE ---
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.shared_fc = nn.Sequential(
            nn.Linear(512, 256),
            nn.LayerNorm(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3)
        )
        
        # Severity Head (Normal=0, Medium=1, Urgent=2)
        self.severity_head = nn.Linear(128, num_classes)
        
        # Infection Detection Head (0=No Infection, 1=Infection/Erythema/Exudate)
        self.infection_head = nn.Linear(128, 1)
        
        # Initialize all layers from scratch using Kaiming Normal
        self._init_weights()

    def _init_weights(self):
        """Kaiming/He Normal initialization for training from complete scratch."""
        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.ConvTranspose2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, (nn.BatchNorm2d, nn.BatchNorm1d)):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x):
        # 1. Feature Extraction (Encoder)
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)
        
        # 2. Bottleneck
        b = self.bottleneck(e4)
        
        # 3. Segmentation Branch (U-Net with Skip Connections)
        d4 = self.dec4(b, e4)
        d3 = self.dec3(d4, e3)
        d2 = self.dec2(d3, e2)
        d1 = self.dec1(d2, e1)
        mask_logits = self.mask_head(d1)  # [B, 1, H, W]
        
        # 4. Classification & Infection Heads
        latent = self.global_pool(b).view(b.size(0), -1)  # [B, 512]
        feat = self.shared_fc(latent)                     # [B, 128]
        
        severity_logits = self.severity_head(feat)        # [B, 3]
        infection_logits = self.infection_head(feat)      # [B, 1]
        
        return {
            "mask_logits": mask_logits,
            "severity_logits": severity_logits,
            "infection_logits": infection_logits
        }

    def get_parameter_count(self):
        """Returns total and trainable parameter count for presentation logs."""
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {"total_parameters": total, "trainable_parameters": trainable}


if __name__ == "__main__":
    model = VitharaNetScratch()
    dummy_input = torch.randn(2, 3, 256, 256)
    out = model(dummy_input)
    param_info = model.get_parameter_count()
    print("VitharaNet-Scratch Architecture Verified:")
    print(f"  Input Shape          : {dummy_input.shape}")
    print(f"  Mask Logits Shape    : {out['mask_logits'].shape}")
    print(f"  Severity Logits Shape: {out['severity_logits'].shape}")
    print(f"  Infection Logits     : {out['infection_logits'].shape}")
    print(f"  Total Parameters     : {param_info['total_parameters']:,}")
