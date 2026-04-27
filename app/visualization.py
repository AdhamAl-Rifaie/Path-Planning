import numpy as np
import pyvista as pv
import plotly.graph_objects as go
from skimage.measure import marching_cubes
from scipy.ndimage import binary_dilation
import nibabel as nib
import os

def make_mesh_data(mask_array, affine):
    mask_dilated = binary_dilation(mask_array, iterations=1)
    if not np.any(mask_dilated):
        return None, None
    verts, faces, _, _ = marching_cubes(mask_dilated, level=0.5)
    verts_h = np.hstack([verts, np.ones((len(verts), 1))])
    verts_mm = (affine @ verts_h.T).T[:, :3]
    return verts_mm, faces

def create_interactive_html(masks_dict, affine, output_path):
    fig = go.Figure()
    colors = {'Whole Tumor': 'red', 'Edema': 'orange', 'Enhancing Tumor': 'yellow', 'Necrotic Core': 'purple'}
    for name, mask in masks_dict.items():
        verts, faces = make_mesh_data(mask, affine)
        if verts is not None:
            fig.add_trace(go.Mesh3d(
                x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
                i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
                name=name, color=colors.get(name, 'blue'), opacity=0.5
            ))
    fig.update_layout(scene=dict(xaxis_title='X (mm)', yaxis_title='Y (mm)', zaxis_title='Z (mm)'))
    fig.write_html(output_path)
    return output_path

def save_as_vtk(mask_array, affine, filename):
    verts, faces = make_mesh_data(mask_array, affine)
    if verts is not None:
        faces_pv = np.hstack([np.full((len(faces), 1), 3), faces])
        mesh = pv.PolyData(verts, faces_pv)
        mesh = mesh.smooth(n_iter=100)
        mesh.save(filename)
        return filename
    return None

def get_atlas_overlap(mask, atlas_img, labels_dict):
    atlas_data = atlas_img.get_fdata()
    unique_labels = np.unique(atlas_data[mask > 0])
    overlaps = []
    for label in unique_labels:
        if label == 0: continue
        name = labels_dict.get(int(label), f"Unknown_{int(label)}")
        volume = np.sum((mask > 0) & (atlas_data == label))
        overlaps.append({"label": name, "volume_voxels": int(volume)})
    return overlaps
