"""
CropPulse – PyTorch Disease Detection Model Architecture
Deep Learning Transfer Learning for Plant Disease Classification.
Supports 38 PlantVillage disease classes with MobileNetV2 and EfficientNet-B0 backbones.
"""

from typing import Optional
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v2, efficientnet_b0, EfficientNet_B0_Weights


class CropDiseaseMobileNet(nn.Module):
    """
    MobileNetV2 transfer learning architecture for crop leaf disease detection.
    Pre-trained on 38 PlantVillage disease classes with high accuracy and low latency.
    """

    def __init__(self, num_classes: int = 38):
        super().__init__()
        self.num_classes = num_classes
        self.backbone = mobilenet_v2(num_classes=num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through MobileNetV2 backbone and classifier."""
        return self.backbone(x)

    def get_features_layer(self) -> nn.Module:
        """Return the target final convolutional layer for Grad-CAM explainability."""
        return self.backbone.features[-1]


class CropDiseaseEfficientNet(nn.Module):
    """
    EfficientNet-B0 transfer learning architecture for crop leaf disease detection.
    """

    def __init__(
        self,
        num_classes: int = 38,
        pretrained: bool = False,
        dropout_rate: float = 0.3,
        freeze_base: bool = False,
    ):
        super().__init__()
        self.num_classes = num_classes

        if pretrained:
            self.backbone = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
        else:
            self.backbone = efficientnet_b0(weights=None)

        if freeze_base:
            for param in self.backbone.features.parameters():
                param.requires_grad = False

        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.SiLU(inplace=True),
            nn.Dropout(p=dropout_rate / 2.0),
            nn.Linear(512, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through EfficientNet-B0 backbone and custom head."""
        return self.backbone(x)

    def get_features_layer(self) -> nn.Module:
        """Return the target final convolutional layer for Grad-CAM explainability."""
        return self.backbone.features[-1]


def build_disease_model(
    num_classes: int = 38,
    pretrained: bool = False,
    dropout_rate: float = 0.3,
    freeze_base: bool = False,
    architecture: str = "auto",
    state_dict: Optional[dict] = None,
) -> nn.Module:
    """Factory function to build and configure the disease model."""
    if architecture.lower() in ["mobilenet", "mobilenetv2", "mobilenet_v2"]:
        return CropDiseaseMobileNet(num_classes=num_classes)

    if architecture == "auto" and state_dict is not None:
        # Check if state_dict keys match MobileNetV2
        if any(k.startswith("classifier.1") or "conv_stem" in k for k in state_dict.keys()):
            return CropDiseaseMobileNet(num_classes=num_classes)

    if architecture.lower() in ["efficientnet", "efficientnet_b0"]:
        return CropDiseaseEfficientNet(
            num_classes=num_classes,
            pretrained=pretrained,
            dropout_rate=dropout_rate,
            freeze_base=freeze_base,
        )

    # Default to MobileNet architecture for high inference performance and low memory
    return CropDiseaseMobileNet(num_classes=num_classes)
