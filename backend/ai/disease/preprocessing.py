"""
CropPulse – PyTorch Disease Preprocessing Pipeline
Prepares raw image bytes / PIL Images for EfficientNet-B0 inference and training.
"""

import io
from typing import Tuple
from PIL import Image
import torch
import torchvision.transforms as T


# Standard ImageNet normalization parameters
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Inference preprocessing pipeline
inference_transform = T.Compose([
    T.Resize((224, 224), interpolation=T.InterpolationMode.BILINEAR),
    T.ToTensor(),
    T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])

# Training data augmentation pipeline
training_transform = T.Compose([
    T.RandomResizedCrop(224, scale=(0.8, 1.0)),
    T.RandomHorizontalFlip(),
    T.RandomVerticalFlip(),
    T.RandomRotation(15),
    T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    T.ToTensor(),
    T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])


def preprocess_image(image_bytes: bytes) -> Tuple[torch.Tensor, Image.Image]:
    """
    Decode image bytes, convert to RGB, resize, and normalize to a PyTorch tensor.

    Args:
        image_bytes: Raw bytes from uploaded image.

    Returns:
        tuple: (batch_tensor [1, 3, 224, 224], pil_image_rgb)
    """
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = inference_transform(pil_image)
    batch_tensor = tensor.unsqueeze(0)  # Shape: (1, 3, 224, 224)
    return batch_tensor, pil_image
