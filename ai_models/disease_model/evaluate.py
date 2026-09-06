"""
CropPulse – Disease Model Evaluation
Evaluates a trained PyTorch model checkpoint on test or validation datasets.
"""

from typing import Dict, Any
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ai_models.disease_model.utils import compute_metrics


def evaluate_model(
    model: nn.Module,
    data_loader: DataLoader,
    device: torch.device,
    classes: list,
) -> Dict[str, Any]:
    """
    Run evaluation loop across dataloader and report accuracy, precision, recall, F1, and loss.
    """
    model.eval()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    all_preds = []
    all_targets = []

    with torch.inference_mode():
        for inputs, targets in data_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            total_loss += loss.item() * inputs.size(0)

            preds = outputs.argmax(dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_targets.extend(targets.cpu().tolist())

    avg_loss = total_loss / len(data_loader.dataset)
    metrics = compute_metrics(all_targets, all_preds, classes)
    metrics["eval_loss"] = round(avg_loss, 4)

    return metrics
