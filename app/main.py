import os
import shutil
import uuid
import zipfile
import threading
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import nibabel as nib
import numpy as np

from .segmentation import load_model, register_images, preprocess_ants, run_inference
from .visualization import create_interactive_html, save_as_vtk, save_path_vtk
from .atlas import register_atlas_to_patient
from .riskmap import build_risk_map
from .pathplanning import plan_paths

app = FastAPI(title="Brain Tumor Pre-Surgery Planning API")

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
_jobs: dict = {}
_jobs_lock = threading.Lock()


@app.on_event("startup")
def startup_event():
    global model
    if os.path.exists(MODEL_PATH):
        model = load_model(MODEL_PATH)
        print("Model loaded successfully")
    else:
        print(f"Warning: model not found at {MODEL_PATH}")


# ─────────────────────────────────────────────────────────────
# Background pipeline
# ─────────────────────────────────────────────────────────────

def _set_status(job_id, status, progress="", result=None, error=""):
    with _jobs_lock:
        _jobs[job_id] = {
            "status":   status,
            "progress": progress,
            "result":   result or {},
            "error":    error,
        }


def _run_pipeline(job_id, saved_paths, res_dir):
    def cb(msg):
        _set_status(job_id, "processing", msg)

    try:
        cb("Loading MRI files...")
        ref_img    = nib.load(saved_paths['t1ce'])
        affine     = ref_img.affine
        voxel_dims = ref_img.header.get_zooms()
        voxel_vol  = float(voxel_dims[0]) * float(voxel_dims[1]) * float(voxel_dims[2])

        # ── Segmentation ──────────────────────────────────────
        cb("Registering MRI channels (ANTs)...")
        moving           = [saved_paths['t1'], saved_paths['t2'], saved_paths['flair']]
        registered_ants  = register_images(saved_paths['t1ce'], moving)
        input_volume     = preprocess_ants(registered_ants)

        cb("Running tumor segmentation (U-Net)...")
        if model is None:
            raise RuntimeError("Model not loaded — place StandardUNet_best.pth in models/")
        mask = run_inference(model, input_volume)

        # Save full segmentation NIfTI
        mask_nii  = nib.Nifti1Image(mask.astype(np.uint8), affine)
        mask_path = os.path.join(res_dir, "segmentation.nii.gz")
        nib.save(mask_nii, mask_path)

        masks_dict = {
            'Whole Tumor':     (mask > 0).astype(np.uint8),
            'Edema':           (mask == 2).astype(np.uint8),
            'Enhancing Tumor': (mask == 3).astype(np.uint8),
            'Necrotic Core':   (mask == 1).astype(np.uint8),
        }

        # Tumor volumes
        volumes = {}
        for name, m in masks_dict.items():
            volumes[name] = round(float(np.sum(m)) * voxel_vol / 1000, 2)  # cm³

        # ── Tumor VTK meshes ──────────────────────────────────
        cb("Generating tumor meshes...")
        vtk_paths = {}
        for name, m in masks_dict.items():
            fname = name.lower().replace(' ', '_') + '.vtk'
            vpath = os.path.join(res_dir, fname)
            result = save_as_vtk(m, affine, vpath)
            if result:
                vtk_paths[name] = fname

        # ── Atlas registration ────────────────────────────────
        functional_masks = {}
        display_regions  = {}
        try:
            functional_masks, display_regions = register_atlas_to_patient(
                saved_paths['t1'], progress_cb=cb
            )
        except Exception as e:
            cb(f"Atlas registration skipped ({e.__class__.__name__}) — continuing without cortex maps...")

        # ── Risk map ──────────────────────────────────────────
        cb("Building 3D risk map...")
        risk_map = build_risk_map(masks_dict, functional_masks)

        # ── Load T1/T1CE data for visualization ───────────────
        t1_data   = nib.load(saved_paths['t1']).get_fdata()
        t1ce_data = nib.load(saved_paths['t1ce']).get_fdata()

        # ── A* path planning ──────────────────────────────────
        scored_paths, target_vox = plan_paths(
            risk_map, t1ce_data,
            masks_dict['Enhancing Tumor'], masks_dict['Whole Tumor'],
            functional_masks,
            num_starts=30,
            progress_cb=cb
        )

        # ── Save path VTK files ───────────────────────────────
        path_vtk_files = {}
        for rank, (score, path) in enumerate(scored_paths[:2]):
            fname = f"surgical_path_{rank + 1}.vtk"
            fpath = os.path.join(res_dir, fname)
            if save_path_vtk(path, fpath):
                path_vtk_files[f"Path #{rank + 1}"] = fname

        # ── 3D + 2D visualization HTML ────────────────────────
        cb("Generating interactive 3D visualization...")
        html_path = os.path.join(res_dir, "visualization.html")
        create_interactive_html(
            masks_dict, affine, html_path,
            functional_masks=functional_masks or None,
            display_regions=display_regions or None,
            paths=scored_paths if scored_paths else None,
            target_vox=target_vox if scored_paths else None,
            t1_data=t1_data,
            t1ce_data=t1ce_data,
        )

        # ── ZIP bundle ────────────────────────────────────────
        cb("Packaging download files...")
        zip_path = os.path.join(res_dir, "surgical_planning.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(mask_path, "segmentation.nii.gz")
            for fname in list(vtk_paths.values()) + list(path_vtk_files.values()):
                fp = os.path.join(res_dir, fname)
                if os.path.exists(fp):
                    zf.write(fp, fname)

        # ── Done ──────────────────────────────────────────────
        result_payload = {
            "visualization_url": f"/view/{job_id}",
            "downloads": {
                "zip":           f"/download/{job_id}/surgical_planning.zip",
                "segmentation":  f"/download/{job_id}/segmentation.nii.gz",
                "tumor_meshes":  {k: f"/download/{job_id}/{v}" for k, v in vtk_paths.items()},
                "surgical_paths":{k: f"/download/{job_id}/{v}" for k, v in path_vtk_files.items()},
            },
            "volumes_cm3": volumes,
            "paths_found": len(scored_paths),
            "atlas_available": bool(functional_masks),
        }
        _set_status(job_id, "done", "Complete", result=result_payload)

    except Exception as exc:
        _set_status(job_id, "failed", error=str(exc))


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/segment")
async def segment_brain(
    t1:    UploadFile = File(...),
    t1ce:  UploadFile = File(...),
    t2:    UploadFile = File(...),
    flair: UploadFile = File(...),
):
    job_id  = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    res_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)

    saved_paths = {}
    for key, upload in [('t1', t1), ('t1ce', t1ce), ('t2', t2), ('flair', flair)]:
        ext  = '.nii.gz' if (upload.filename or '').endswith('.gz') else '.nii'
        dest = os.path.join(job_dir, f'{key}{ext}')
        with open(dest, 'wb') as buf:
            shutil.copyfileobj(upload.file, buf)
        saved_paths[key] = dest

    _set_status(job_id, "queued", "Queued")
    thread = threading.Thread(target=_run_pipeline, args=(job_id, saved_paths, res_dir), daemon=True)
    thread.start()

    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    with _jobs_lock:
        return _jobs.get(job_id, {"status": "not_found"})


@app.get("/view/{job_id}", response_class=HTMLResponse)
async def view_visualization(job_id: str):
    html_path = os.path.join(OUTPUT_DIR, job_id, "visualization.html")
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h2 style='color:white;font-family:sans-serif;padding:40px'>Visualization not ready yet.</h2>"


@app.get("/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    file_path = os.path.join(OUTPUT_DIR, job_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return {"error": "File not found"}
