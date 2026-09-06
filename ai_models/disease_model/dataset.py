"""
CropPulse – PyTorch Dataset & DataLoader
Handles PlantVillage folder structure with Train/Validation/Test split and augmentations.
"""

import os
from typing import Tuple, Optional
import torch
from torch.utils.data import DataLoader, random_split
from torchvision.datasets import ImageFolder
import torchvision.transforms as T

from ai_models.disease_model.config import TrainingConfig


def get_transforms(img_size: int = 224) -> Tuple[T.Compose, T.Compose]:
    """Return train and validation/test transforms."""
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]

    train_tf = T.Compose([
        T.Resize((img_size, img_size)),
        T.RandomHorizontalFlip(),
        T.RandomVerticalFlip(),
        T.RandomRotation(15),
        T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        T.ToTensor(),
        T.Normalize(mean=mean, std=std),
    ])

    val_tf = T.Compose([
        T.Resize((img_size, img_size)),
        T.ToTensor(),
        T.Normalize(mean=mean, std=std),
    ])

    return train_tf, val_tf


def create_dataloaders(
    config: TrainingConfig,
) -> Tuple[DataLoader, DataLoader, Optional[DataLoader], list]:
    """
    Load dataset from folder and split into Train (70%), Val (15%), Test (15%).
    """
    if not os.path.exists(config.data_dir):
        raise FileNotFoundError(f"Dataset directory not found: {config.data_dir}")

    train_tf, val_tf = get_transforms(config.img_size)

    # Load root dataset
    full_dataset = ImageFolder(root=config.data_dir, transform=train_tf)
    classes = full_dataset.classes

    total_size = len(full_dataset)
    train_size = int(0.70 * total_size)
    val_size = int(0.15 * total_size)
    test_size = total_size - train_size - val_size

    generator = torch.Generator().manual_seed(42)
    train_data, val_data, test_data = random_split(
        full_dataset, [train_size, val_size, test_size], generator=generator
    )

    train_loader = DataLoader(
        train_data,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_data,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    test_loader = DataLoader(
        test_data,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    return train_loader, val_loader, test_loader, classes
