"""
CropPulse – Standalone Disease Model Inference CLI
Allows developers and agronomists to test image classification and Grad-CAM from the command line.
"""

import sys
import argparse
from PIL import Image
import torch

from backend.ai.disease.preprocessing import preprocess_image
from backend.ai.disease.model import build_disease_model
from backend.ai.disease.model_manager import DISEASE_CLASSES, DISEASE_CLASSES_DISPLAY
from backend.ai.disease.explainability import generate_gradcam_explanation


def run_inference(image_path: str, model_path: str, output_heatmap: str = None):
    """Run CLI inference on a single image."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load image
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    input_tensor, pil_image = preprocess_image(image_bytes)
    input_tensor = input_tensor.to(device)

    # Load model
    model = build_disease_model(num_classes=len(DISEASE_CLASSES), pretrained=False).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    # Predict
    with torch.inference_mode():
        logits = model(input_tensor)
        probs = torch.softmax(logits, dim=-1)[0]

    top_probs, top_indices = torch.topk(probs, k=3)
    top_class = DISEASE_CLASSES[top_indices[0].item()]

    print(f"\n🌾 Detection Results:")
    print(f"Top Prediction: {DISEASE_CLASSES_DISPLAY.get(top_class, top_class)}")
    print(f"Confidence: {top_probs[0].item() * 100:.2f}%\n")

    for i in range(3):
        cls_key = DISEASE_CLASSES[top_indices[i].item()]
        print(f"  {i+1}. {DISEASE_CLASSES_DISPLAY.get(cls_key, cls_key)}: {top_probs[i].item() * 100:.2f}%")

    if output_heatmap:
        target_layer = model.get_features_layer()
        with torch.enable_grad():
            img_bytes, _ = generate_gradcam_explanation(
                model=model,
                target_layer=target_layer,
                input_tensor=input_tensor.clone(),
                original_pil=pil_image,
                class_idx=top_indices[0].item(),
            )
        with open(output_heatmap, "wb") as f:
            f.write(img_bytes)
        print(f"\n🔥 Grad-CAM heatmap saved to: {output_heatmap}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CropPulse Disease Detection CLI")
    parser.add_argument("--image", required=True, help="Path to leaf image")
    parser.add_argument("--model", default="./ai_models/saved_models/disease_model.pth", help="Path to .pth checkpoint")
    parser.add_argument("--heatmap", default=None, help="Optional output path for Grad-CAM overlay")
    args = parser.parse_args()

    run_inference(args.image, args.model, args.heatmap)
