"""
CropPulse – Disease Training Utilities & Metrics
Calculates Accuracy, Precision, Recall, F1-Score, and Confusion Matrix.
"""

from typing import Dict, Any
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix


def compute_metrics(y_true: list, y_pred: list, classes: list) -> Dict[str, Any]:
    """
    Compute comprehensive classification metrics.
    """
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(classes))))

    # Per-class metrics
    class_prec, class_rec, class_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0
    )

    per_class = {}
    for i, cls_name in enumerate(classes):
        per_class[cls_name] = {
            "precision": round(float(class_prec[i]), 4),
            "recall": round(float(class_rec[i]), 4),
            "f1": round(float(class_f1[i]), 4),
        }

    return {
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
    }
