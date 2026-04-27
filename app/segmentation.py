import os
import torch
import torch.nn.functional as F
import nibabel as nib
import numpy as np
import ants
from monai.networks.nets import UNet

def load_model(model_path, device='cpu'):
    model = UNet(
        spatial_dims=3,
        in_channels=4,
        out_channels=4,
        channels=(32, 64, 128, 256, 512),
        strides=(2, 2, 2, 2),
        num_res_units=0,
    )
    checkpoint = torch.load(model_path, map_location=device)
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.to(device)
    model.eval()
    return model

def register_images(fixed_path, moving_paths):
    fixed = ants.image_read(fixed_path)
    registered_images = [fixed]
    for path in moving_paths:
        moving = ants.image_read(path)
        reg = ants.registration(fixed=fixed, moving=moving, type_of_transform='Rigid')
        registered_images.append(reg['warpedmovout'])
    return registered_images

def preprocess_ants(ants_images):
    processed = []
    for img in ants_images:
        data = img.numpy()
        data = (data - np.mean(data)) / (np.std(data) + 1e-8)
        processed.append(data)
    return np.stack(processed, axis=0)

def pad_to_divisible(tensor, divisor=16):
    _, _, D, H, W = tensor.shape
    pad_D = (divisor - D % divisor) % divisor
    pad_H = (divisor - H % divisor) % divisor
    pad_W = (divisor - W % divisor) % divisor
    return F.pad(tensor, (0, pad_W, 0, pad_H, 0, pad_D)), (D, H, W)

def run_inference(model, input_volume, device='cpu'):
    input_tensor = torch.tensor(input_volume, dtype=torch.float32).unsqueeze(0).to(device)
    padded_tensor, orig_shape = pad_to_divisible(input_tensor)
    with torch.no_grad():
        output = model(padded_tensor)
    pred = torch.argmax(output, dim=1).squeeze(0)
    mask = pred.cpu().numpy()
    D, H, W = orig_shape
    mask = mask[:D, :H, :W]
    return mask
