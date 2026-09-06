"""
CropPulse – PyTorch Disease Model Training Pipeline
Trains EfficientNet-B0 transfer learning model with data augmentation,
learning rate scheduling, checkpointing, and early stopping.
"""

import os
import json
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from loguru import logger

from ai_models.disease_model.config import TrainingConfig
from ai_models.disease_model.dataset import create_dataloaders
from ai_models.disease_model.model import build_disease_model
from ai_models.disease_model.evaluate import evaluate_model


def train_disease_pipeline(config: TrainingConfig = None):
    """Execute complete PyTorch disease model training and evaluation."""
    if config is None:
        config = TrainingConfig()

    os.makedirs(config.output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"🌿 Starting Disease Model Training on {device}...")

    # Dataloaders
    try:
        train_loader, val_loader, test_loader, classes = create_dataloaders(config)
    except FileNotFoundError as e:
        logger.error(f"Cannot start training: {e}")
        return

    logger.info(f"Classes: {len(classes)}, Train batches: {len(train_loader)}, Val batches: {len(val_loader)}")

    # Model architecture with frozen backbone initially
    model = build_disease_model(
        num_classes=len(classes),
        pretrained=True,
        dropout_rate=config.dropout_rate,
        freeze_base=True,
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=config.epochs, eta_min=config.lr_min)

    best_val_f1 = 0.0
    patience_counter = 0
    history = []

    for epoch in range(1, config.epochs + 1):
        # Unfreeze base layers for fine-tuning after initial freeze epochs
        if epoch == config.freeze_epochs + 1:
            logger.info("🔓 Unfreezing EfficientNet-B0 backbone for fine-tuning...")
            for param in model.backbone.features.parameters():
                param.requires_grad = True
            # Adjust learning rate for fine-tuning
            for param_group in optimizer.param_groups:
                param_group["lr"] = config.learning_rate * 0.2

        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            preds = outputs.argmax(dim=-1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)

        scheduler.step()

        train_loss = running_loss / total
        train_acc = correct / total

        # Validation
        val_metrics = evaluate_model(model, val_loader, device, classes)
        val_f1 = val_metrics["f1_score"]
        val_acc = val_metrics["accuracy"]

        logger.info(
            f"Epoch [{epoch}/{config.epochs}] | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
            f"Val Loss: {val_metrics['eval_loss']:.4f} Acc: {val_acc:.4f} F1: {val_f1:.4f}"
        )

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": val_metrics["eval_loss"],
            "val_acc": val_acc,
            "val_f1": val_f1,
        })

        # Checkpointing
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            patience_counter = 0
            torch.save(model.state_dict(), config.model_save_path)
            logger.success(f"💾 Checkpoint saved to {config.model_save_path} (Val F1: {val_f1:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= config.patience_early_stopping:
                logger.warning(f"⏹️ Early stopping triggered at epoch {epoch}")
                break

    # Save training history
    with open(config.history_save_path, "w") as f:
        json.dump(history, f, indent=2)

    # Final evaluation on Test Set
    if test_loader is not None and os.path.exists(config.model_save_path):
        logger.info("🧪 Evaluating best checkpoint on Test Set...")
        model.load_state_dict(torch.load(config.model_save_path, map_location=device))
        test_metrics = evaluate_model(model, test_loader, device, classes)
        logger.success(f"🎉 Final Test Accuracy: {test_metrics['accuracy']:.4f}, Test F1: {test_metrics['f1_score']:.4f}")

    logger.info("✅ Disease model training pipeline complete.")


if __name__ == "__main__":
    train_disease_pipeline()
