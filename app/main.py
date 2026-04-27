import os
import shutil
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import nibabel as nib
import numpy as np
from nilearn import datasets
import xml.etree.ElementTree as ET

from .segmentation import load_model, register_images, preprocess_ants, run_inference
from .visualization import create_interactive_html, save_as_vtk, get_atlas_overlap

app = FastAPI(title="Brain Tumor Segmentation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "data/uploads"
OUTPUT_DIR = "outputs"
MODEL_PATH = "models/StandardUNet_best.pth"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

model = None

@app.on_event("startup")
def startup_event():
    global model
    if os.path.exists(MODEL_PATH):
        model = load_model(MODEL_PATH)
        print("Model loaded successfully")
    else:
        print(f"Warning: Model not found at {MODEL_PATH}")

@app.post("/segment")
async def segment_brain(
    t1: UploadFile = File(...),
    t1ce: UploadFile = File(...),
    t2: UploadFile = File(...),
    flair: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    paths = {}
    for f in [t1, t1ce, t2, flair]:
        path = os.path.join(job_dir, f.filename)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        paths[f.filename] = path
    moving = [paths[t1.filename], paths[t2.filename], paths[flair.filename]]
    registered_ants = register_images(paths[t1ce.filename], moving)
    input_volume = preprocess_ants(registered_ants)
    mask = run_inference(model, input_volume)
    res_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(res_dir, exist_ok=True)
    ref_img = nib.load(paths[t1ce.filename])
    mask_nii = nib.Nifti1Image(mask.astype(np.uint8), ref_img.affine)
    mask_path = os.path.join(res_dir, "segmentation.nii.gz")
    nib.save(mask_nii, mask_path)
    masks_dict = {
        'Whole Tumor': (mask > 0).astype(np.uint8),
        'Edema': (mask == 2).astype(np.uint8),
        'Enhancing Tumor': (mask == 3).astype(np.uint8),
        'Necrotic Core': (mask == 1).astype(np.uint8)
    }
    html_path = os.path.join(res_dir, "visualization.html")
    create_interactive_html(masks_dict, ref_img.affine, html_path)
    vtk_paths = {}
    for name, m in masks_dict.items():
        fname = f"{name.lower().replace(' ', '_')}.vtk"
        vpath = os.path.join(res_dir, fname)
        save_as_vtk(m, ref_img.affine, vpath)
        vtk_paths[name] = f"/download/{job_id}/{fname}"
    return {
        "job_id": job_id,
        "visualization_url": f"/view/{job_id}",
        "downloads": {
            "segmentation_nii": f"/download/{job_id}/segmentation.nii.gz",
            "meshes": vtk_paths
        }
    }

@app.get("/view/{job_id}", response_class=HTMLResponse)
async def view_visualization(job_id: str):
    html_path = os.path.join(OUTPUT_DIR, job_id, "visualization.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return f.read()
    return "Visualization not found"

@app.get("/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    file_path = os.path.join(OUTPUT_DIR, job_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return {"error": "File not found"}
