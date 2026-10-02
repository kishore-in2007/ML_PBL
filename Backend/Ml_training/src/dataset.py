"""
Dataset loader and scratch augmentations for VitharaNet.
Supports real DFUC2022 / Wound image datasets and synthetic generation for self-contained testing.
"""

import os
import glob
import random
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import torch
from torch.utils.data import Dataset


class WoundScratchDataset(Dataset):
    """
    Custom Dataset for Multi-Task Wound Monitoring:
    - Input: RGB Wound Image (256 x 256)
    - Output 1: Binary Segmentation Ground Truth (1 x 256 x 256)
    - Output 2: Severity Label (0=Normal, 1=Medium, 2=Urgent)
    - Output 3: Infection Label (0=Clean, 1=Infected / Erythema / Pus)
    """
    def __init__(self, root_dir=None, split='train', img_size=(256, 256), augment=True, num_samples=300):
        self.root_dir = root_dir
        self.split = split
        self.img_size = img_size
        self.augment = augment
        self.samples = []
        
        if root_dir and os.path.exists(root_dir):
            self._load_from_directory()
        else:
            # Generate reproducible dataset samples for development/verification
            self._generate_synthetic_dataset(num_samples)

    def _load_from_directory(self):
        """Loads images and matching masks if directory is supplied."""
        img_extensions = ('*.png', '*.jpg', '*.jpeg')
        img_paths = []
        for ext in img_extensions:
            img_paths.extend(glob.glob(os.path.join(self.root_dir, self.split, "images", ext)))
            if not img_paths:
                img_paths.extend(glob.glob(os.path.join(self.root_dir, ext)))
                
        for p in img_paths:
            base = os.path.splitext(os.path.basename(p))[0]
            # Try to find corresponding mask
            mask_p = os.path.join(self.root_dir, self.split, "masks", f"{base}.png")
            if not os.path.exists(mask_p):
                mask_p = os.path.join(self.root_dir, "masks", f"{base}.png")
            
            # Label heuristics or metadata if available
            fname = os.path.basename(p).lower()
            if "urgent" in fname or "severe" in fname or "infect" in fname:
                sev = 2
                infect = 1
            elif "medium" in fname or "mild" in fname or "concern" in fname:
                sev = 1
                infect = random.choice([0, 1])
            else:
                sev = 0
                infect = 0
                
            self.samples.append({
                "image_path": p,
                "mask_path": mask_p if os.path.exists(mask_p) else None,
                "severity": sev,
                "infection": infect
            })

    def _generate_synthetic_dataset(self, num_samples):
        """Generates realistic structured synthetic wound samples for scratch verification."""
        for i in range(num_samples):
            # Balanced class distribution
            if i % 3 == 0:
                sev = 0  # Normal
                infect = 0
            elif i % 3 == 1:
                sev = 1  # Medium
                infect = 0 if i % 2 == 0 else 1
            else:
                sev = 2  # Urgent
                infect = 1
                
            self.samples.append({
                "synthetic_id": i,
                "severity": sev,
                "infection": infect
            })

    def _apply_augmentations(self, img, mask):
        """Scratch data augmentation using PIL (No third-party black-box libraries)."""
        # Random Horizontal Flip
        if random.random() > 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
            mask = mask.transpose(Image.FLIP_LEFT_RIGHT)
            
        # Random Vertical Flip
        if random.random() > 0.5:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            mask = mask.transpose(Image.FLIP_TOP_BOTTOM)
            
        # Random Rotation (-25 to +25 degrees)
        angle = random.uniform(-25, 25)
        img = img.rotate(angle, resample=Image.BILINEAR)
        mask = mask.rotate(angle, resample=Image.NEAREST)
        
        # Random Color / Brightness Jitter
        if random.random() > 0.3:
            factor = random.uniform(0.8, 1.2)
            img = ImageEnhance.Brightness(img).enhance(factor)
        if random.random() > 0.3:
            factor = random.uniform(0.8, 1.2)
            img = ImageEnhance.Color(img).enhance(factor)
        if random.random() > 0.3:
            factor = random.uniform(0.8, 1.2)
            img = ImageEnhance.Contrast(img).enhance(factor)
            
        return img, mask

    def _create_synthetic_sample(self, sev, infect):
        """Creates synthetic wound image & ground-truth mask with distinct visual features."""
        # Base skin tone
        skin_r = random.randint(180, 230)
        skin_g = random.randint(140, 190)
        skin_b = random.randint(120, 160)
        
        img_arr = np.ones((self.img_size[0], self.img_size[1], 3), dtype=np.uint8)
        img_arr[:, :, 0] = skin_r
        img_arr[:, :, 1] = skin_g
        img_arr[:, :, 2] = skin_b
        
        # Create wound geometry
        mask_arr = np.zeros((self.img_size[0], self.img_size[1]), dtype=np.uint8)
        cx = self.img_size[1] // 2 + random.randint(-20, 20)
        cy = self.img_size[0] // 2 + random.randint(-20, 20)
        
        if sev == 0:  # Normal (clean, small pink incision)
            rx, ry = random.randint(15, 30), random.randint(8, 15)
            wound_color = [180, 70, 80]  # Healthy granulation pink/red
        elif sev == 1:  # Medium (moderate ulcer, surrounding redness)
            rx, ry = random.randint(35, 55), random.randint(25, 45)
            wound_color = [160, 40, 50]  # Deeper red
        else:  # Urgent (large, deep, necrotic or purulent yellow/dark)
            rx, ry = random.randint(60, 85), random.randint(50, 75)
            wound_color = [120, 30, 40] if infect == 0 else [140, 120, 30]  # Exudate yellow/brown
            
        y, x = np.ogrid[:self.img_size[0], :self.img_size[1]]
        dist = ((x - cx)**2) / (rx**2 + 1e-5) + ((y - cy)**2) / (ry**2 + 1e-5)
        wound_indices = dist <= 1.0
        
        # Perilesional erythema (red halo around wound for infection)
        if infect == 1:
            halo_indices = (dist > 1.0) & (dist <= 2.2)
            img_arr[halo_indices, 0] = np.clip(img_arr[halo_indices, 0].astype(int) + 50, 0, 255)
            img_arr[halo_indices, 1] = np.clip(img_arr[halo_indices, 1].astype(int) - 30, 0, 255)
            img_arr[halo_indices, 2] = np.clip(img_arr[halo_indices, 2].astype(int) - 30, 0, 255)
            
        img_arr[wound_indices] = wound_color
        mask_arr[wound_indices] = 255
        
        img = Image.fromarray(img_arr)
        mask = Image.fromarray(mask_arr)
        
        # Add slight texture/blur
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.2)))
        return img, mask

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        
        if "synthetic_id" in item:
            img, mask = self._create_synthetic_sample(item["severity"], item["infection"])
        else:
            img = Image.open(item["image_path"]).convert("RGB").resize(self.img_size)
            if item["mask_path"] and os.path.exists(item["mask_path"]):
                mask = Image.open(item["mask_path"]).convert("L").resize(self.img_size)
            else:
                # Fallback to circular center mask if raw mask is absent
                mask = Image.new("L", self.img_size, 0)
                
        if self.augment and self.split == 'train':
            img, mask = self._apply_augmentations(img, mask)
            
        # Convert to Tensors
        img_np = np.array(img, dtype=np.float32) / 255.0  # Normalize to [0, 1]
        # Standardize: Mean=0.5, Std=0.5 -> [-1, 1]
        img_np = (img_np - 0.5) / 0.5
        img_tensor = torch.from_numpy(img_np).permute(2, 0, 1).float()
        
        mask_np = np.array(mask, dtype=np.float32) / 255.0
        mask_np = (mask_np > 0.5).astype(np.float32)
        mask_tensor = torch.from_numpy(mask_np).unsqueeze(0).float()
        
        sev_tensor = torch.tensor(item["severity"], dtype=torch.long)
        infect_tensor = torch.tensor(item["infection"], dtype=torch.float)
        
        return {
            "image": img_tensor,
            "mask": mask_tensor,
            "severity": sev_tensor,
            "infection": infect_tensor
        }
