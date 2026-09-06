"""
CropPulse – Disease Model Training Configuration
"""

import os
from dataclasses import dataclass


@dataclass
class TrainingConfig:
    # Dataset
    data_dir: str = "./datasets/disease/dataset"
    num_classes: int = 38
    img_size: int = 224
    batch_size: int = 32
    num_workers: int = 2

    # Training Hyperparameters
    epochs: int = 15
    learning_rate: float = 1e-4
    weight_decay: float = 1e-4
    dropout_rate: float = 0.3
    freeze_epochs: int = 3  # Feature extraction freeze before fine-tuning

    # Optimizer & Scheduler
    lr_min: float = 1e-6
    patience_early_stopping: int = 5

    # Paths
    output_dir: str = "./ai_models/saved_models"
    model_save_path: str = "./ai_models/saved_models/disease_model.pth"
    history_save_path: str = "./ai_models/saved_models/disease_training_history.json"
