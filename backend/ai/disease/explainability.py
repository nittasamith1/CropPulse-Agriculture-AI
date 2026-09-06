"""
CropPulse – PyTorch Grad-CAM Explainability Module
Generates visual saliency heatmaps highlighting leaf regions that drove disease detection.
"""

import io
import base64
from typing import Optional, Tuple
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import cv2


class GradCAM:
    """
    Gradient-weighted Class Activation Mapping (Grad-CAM) for PyTorch models.
    Targets the final convolutional layer of EfficientNet-B0.
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None

        # Register forward and backward hooks
        self._fwd_handle = self.target_layer.register_forward_hook(self._save_activation)
        self._bwd_handle = self.target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, input, output):
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate_heatmap(
        self,
        input_tensor: torch.Tensor,
        class_idx: Optional[int] = None,
    ) -> np.ndarray:
        """
        Generate raw Grad-CAM 2D heatmap [0.0, 1.0] for the given class index.
        """
        self.model.zero_grad()
        output = self.model(input_tensor)

        if class_idx is None:
            class_idx = output.argmax(dim=-1).item()

        score = output[0, class_idx]
        score.backward(retain_graph=True)

        # Global average pooling on gradients across spatial dimensions (H, W)
        pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3])  # Shape: (Channels,)

        # Multiply each channel activation by its gradient weight
        activations = self.activations[0]  # Shape: (Channels, H, W)
        for i in range(activations.size(0)):
            activations[i] *= pooled_gradients[i]

        # Saliency map is the ReLU of channel sum
        heatmap = torch.sum(activations, dim=0).cpu().numpy()
        heatmap = np.maximum(heatmap, 0)

        # Normalize to [0, 1]
        max_val = np.max(heatmap)
        if max_val > 0:
            heatmap /= max_val
        else:
            heatmap = np.zeros_like(heatmap)

        return heatmap

    def overlay_on_image(
        self,
        original_pil: Image.Image,
        heatmap: np.ndarray,
        alpha: float = 0.45,
    ) -> Image.Image:
        """
        Resize heatmap to match the original image and blend with COLORMAP_JET.
        """
        orig_w, orig_h = original_pil.size
        orig_cv = cv2.cvtColor(np.array(original_pil), cv2.COLOR_RGB2BGR)

        # Resize heatmap to original image dimensions
        resized_heatmap = cv2.resize(heatmap, (orig_w, orig_h))
        heatmap_uint8 = np.uint8(255 * resized_heatmap)

        # Apply colormap
        colored_heatmap = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

        # Blend
        overlay = cv2.addWeighted(colored_heatmap, alpha, orig_cv, 1 - alpha, 0)
        overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

        return Image.fromarray(overlay_rgb)

    def close(self):
        """Clean up hooks."""
        self._fwd_handle.remove()
        self._bwd_handle.remove()


def generate_gradcam_explanation(
    model: nn.Module,
    target_layer: nn.Module,
    input_tensor: torch.Tensor,
    original_pil: Image.Image,
    class_idx: Optional[int] = None,
) -> Tuple[bytes, str]:
    """
    Helper function to generate a Grad-CAM image overlay as JPEG bytes and base64 string.
    """
    grad_cam = GradCAM(model=model, target_layer=target_layer)
    try:
        heatmap = grad_cam.generate_heatmap(input_tensor, class_idx=class_idx)
        overlay_pil = grad_cam.overlay_on_image(original_pil, heatmap)

        buffer = io.BytesIO()
        overlay_pil.save(buffer, format="JPEG", quality=85)
        image_bytes = buffer.getvalue()
        b64_str = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{b64_str}"

        return image_bytes, data_uri
    finally:
        grad_cam.close()
