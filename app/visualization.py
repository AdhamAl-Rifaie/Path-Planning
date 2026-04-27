import io
import base64
import numpy as np
import pyvista as pv
import plotly.graph_objects as go
from skimage.measure import marching_cubes
from scipy.ndimage import binary_dilation, binary_erosion

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# ─────────────────────────────────────────────────────────────
# Mesh helpers
# ─────────────────────────────────────────────────────────────

def make_mesh_data(mask_array, affine):
    mask_dilated = binary_dilation(mask_array, iterations=1)
    if not np.any(mask_dilated):
        return None, None
    verts, faces, _, _ = marching_cubes(mask_dilated, level=0.5)
    verts_h  = np.hstack([verts, np.ones((len(verts), 1))])
    verts_mm = (affine @ verts_h.T).T[:, :3]
    return verts_mm, faces


def save_as_vtk(mask_array, affine, filename):
    verts, faces = make_mesh_data(mask_array, affine)
    if verts is None:
        return None
    faces_pv = np.hstack([np.full((len(faces), 1), 3), faces])
    mesh     = pv.PolyData(verts, faces_pv)
    mesh     = mesh.smooth(n_iter=100)
    mesh.save(filename)
    return filename


def save_path_vtk(path_coords, filename):
    if path_coords is None or len(path_coords) < 2:
        return None
    pts = np.array(path_coords, dtype=float)
    n   = len(pts)
    cells      = np.empty(n + 1, dtype=int)
    cells[0]   = n
    cells[1:]  = np.arange(n)
    mesh       = pv.PolyData()
    mesh.points = pts
    mesh.lines  = cells
    mesh.save(filename)
    return filename


# ─────────────────────────────────────────────────────────────
# Atlas overlap report (optional)
# ─────────────────────────────────────────────────────────────

def get_atlas_overlap(mask, atlas_img, labels_dict):
    atlas_data    = atlas_img.get_fdata()
    unique_labels = np.unique(atlas_data[mask > 0])
    overlaps      = []
    for label in unique_labels:
        if label == 0:
            continue
        name   = labels_dict.get(int(label), f"Unknown_{int(label)}")
        volume = int(np.sum((mask > 0) & (atlas_data == label)))
        overlaps.append({"label": name, "volume_voxels": volume})
    return overlaps


# ─────────────────────────────────────────────────────────────
# 2D view helpers
# ─────────────────────────────────────────────────────────────

def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=110,
                facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return b64


def _overlay_panel(ax, bg, masks_alpha, title):
    ax.imshow(bg, cmap='gray', origin='lower', aspect='auto')
    for data, cmap, alpha in masks_alpha:
        if data is not None and data.max() > 0:
            ax.imshow(data, cmap=cmap, alpha=alpha, origin='lower',
                      aspect='auto', vmin=0, vmax=1)
    ax.set_title(title, color='white', fontsize=9, pad=4)
    ax.axis('off')


def _generate_2d_views_html(masks_dict, functional_masks, t1_data):
    whole_tumor = masks_dict.get('Whole Tumor', np.zeros_like(t1_data, dtype=np.uint8))
    et_mask     = masks_dict.get('Enhancing Tumor', np.zeros_like(t1_data, dtype=np.uint8))
    edema_mask  = masks_dict.get('Edema', np.zeros_like(t1_data, dtype=np.uint8))
    ncr_mask    = masks_dict.get('Necrotic Core', np.zeros_like(t1_data, dtype=np.uint8))

    motor    = functional_masks.get('motor')    if functional_masks else None
    language = functional_masks.get('language') if functional_masks else None
    visual   = functional_masks.get('visual')   if functional_masks else None

    t1_norm = (t1_data - t1_data.min()) / (t1_data.max() - t1_data.min() + 1e-8)

    # Best axial slice: largest tumor cross-section
    z_idx = int(np.argmax(np.sum(whole_tumor, axis=(0, 1))))
    # Best coronal slice
    y_idx = int(np.argmax(np.sum(whole_tumor, axis=(0, 2))))

    bg_dark = '#0d1117'

    panels_def = [
        ("Tumor Regions",
         [(whole_tumor[:, :, z_idx].T, 'Reds', 0.55),
          (et_mask[:, :, z_idx].T,     'YlOrRd', 0.5),
          (ncr_mask[:, :, z_idx].T,    'hot', 0.45)]),
        ("Functional Cortex",
         [(motor[:, :, z_idx].T    if motor    is not None else None, 'Blues',   0.5),
          (language[:, :, z_idx].T if language is not None else None, 'Greens',  0.5),
          (visual[:, :, z_idx].T   if visual   is not None else None, 'Purples', 0.5)]),
        ("Full Overlay",
         [(motor[:, :, z_idx].T    if motor    is not None else None, 'Blues',   0.3),
          (language[:, :, z_idx].T if language is not None else None, 'Greens',  0.3),
          (visual[:, :, z_idx].T   if visual   is not None else None, 'Purples', 0.3),
          (whole_tumor[:, :, z_idx].T, 'Reds', 0.5)]),
    ]

    fig_ax, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor=bg_dark)
    fig_ax.patch.set_facecolor(bg_dark)
    for ax, (title, overlays) in zip(axes, panels_def):
        ax.set_facecolor(bg_dark)
        _overlay_panel(ax, t1_norm[:, :, z_idx].T, overlays, title)
    fig_ax.suptitle(f'Axial View  (z = {z_idx})', color='white', fontsize=11)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    axial_b64 = _fig_to_b64(fig_ax)

    # Coronal panels (slice along y)
    panels_cor = [
        ("Tumor Regions",
         [(whole_tumor[:, y_idx, :].T, 'Reds', 0.55),
          (et_mask[:, y_idx, :].T,     'YlOrRd', 0.5),
          (ncr_mask[:, y_idx, :].T,    'hot', 0.45)]),
        ("Functional Cortex",
         [(motor[:, y_idx, :].T    if motor    is not None else None, 'Blues',   0.5),
          (language[:, y_idx, :].T if language is not None else None, 'Greens',  0.5),
          (visual[:, y_idx, :].T   if visual   is not None else None, 'Purples', 0.5)]),
        ("Full Overlay",
         [(motor[:, y_idx, :].T    if motor    is not None else None, 'Blues',   0.3),
          (language[:, y_idx, :].T if language is not None else None, 'Greens',  0.3),
          (visual[:, y_idx, :].T   if visual   is not None else None, 'Purples', 0.3),
          (whole_tumor[:, y_idx, :].T, 'Reds', 0.5)]),
    ]

    fig_cor, axes2 = plt.subplots(1, 3, figsize=(15, 5), facecolor=bg_dark)
    fig_cor.patch.set_facecolor(bg_dark)
    for ax, (title, overlays) in zip(axes2, panels_cor):
        ax.set_facecolor(bg_dark)
        _overlay_panel(ax, t1_norm[:, y_idx, :].T, overlays, title)
    fig_cor.suptitle(f'Coronal View  (y = {y_idx})', color='white', fontsize=11)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    coronal_b64 = _fig_to_b64(fig_cor)

    html = f"""
<div class="views2d-wrap">
  <button class="views2d-toggle" onclick="
    var p=this.nextElementSibling;
    var open=p.style.display==='block';
    p.style.display=open?'none':'block';
    this.textContent=open?'▶  Show 2D Axial / Coronal Views':'▼  Hide 2D Views';
  ">▶  Show 2D Axial / Coronal Views</button>
  <div class="views2d-panel" style="display:none">
    <p class="views2d-hint">
      Motor cortex = <span style="color:#6ea8fe">blue</span> &nbsp;|&nbsp;
      Language = <span style="color:#5dce7b">green</span> &nbsp;|&nbsp;
      Visual = <span style="color:#c084fc">purple</span> &nbsp;|&nbsp;
      Tumor = <span style="color:#f87171">red</span>
    </p>
    <h3 class="views2d-sub">Axial (z = {z_idx})</h3>
    <img src="data:image/png;base64,{axial_b64}" style="width:100%;border-radius:6px;">
    <h3 class="views2d-sub" style="margin-top:20px">Coronal (y = {y_idx})</h3>
    <img src="data:image/png;base64,{coronal_b64}" style="width:100%;border-radius:6px;">
  </div>
</div>
"""
    return html


# ─────────────────────────────────────────────────────────────
# Main HTML builder
# ─────────────────────────────────────────────────────────────

_MESH_COLORS = {
    'Whole Tumor':     'red',
    'Edema':           'orange',
    'Enhancing Tumor': 'yellow',
    'Necrotic Core':   'purple',
}

_PATH_COLORS = ['lime', 'orange']


def create_interactive_html(masks_dict, affine, output_path,
                             functional_masks=None, display_regions=None,
                             paths=None, target_vox=None,
                             t1_data=None, t1ce_data=None):
    fig = go.Figure()

    # ── Brain surface ──────────────────────────────────────────
    if t1ce_data is not None:
        brain_mask     = t1ce_data > t1ce_data.mean() * 0.20
        brain_interior = binary_erosion(brain_mask, iterations=2)
        shell          = brain_mask & ~brain_interior
        surface        = np.array(np.where(shell)).T
        if len(surface) > 8000:
            surface = surface[np.random.choice(len(surface), 8000, replace=False)]
        fig.add_trace(go.Scatter3d(
            x=surface[:, 0], y=surface[:, 1], z=surface[:, 2],
            mode='markers',
            marker=dict(size=1.5, color='lightgray', opacity=0.22),
            name='Brain Surface',
            legendgroup='brain',
        ))

    # ── Individual labelled atlas regions ─────────────────────
    # Each region is its own trace so the Plotly legend shows its exact name
    # and users can toggle it on/off.
    if display_regions:
        for region_name, meta in display_regions.items():
            m = meta['mask']
            if m.sum() == 0:
                continue
            pts = np.array(np.where(m)).T
            # White matter gets sparse sampling (large structure, low opacity)
            max_pts = 300 if meta['opacity'] < 0.10 else 2000
            if len(pts) > max_pts:
                pts = pts[np.random.choice(len(pts), max_pts, replace=False)]
            fig.add_trace(go.Scatter3d(
                x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
                mode='markers',
                marker=dict(size=2, color=meta['color'], opacity=meta['opacity']),
                name=region_name,
                legendgroup='atlas',
                hovertemplate=f'<b>{region_name}</b><extra></extra>',
            ))

    # ── Tumor meshes ───────────────────────────────────────────
    for name, mask in masks_dict.items():
        verts, faces = make_mesh_data(mask, affine)
        if verts is None:
            continue
        fig.add_trace(go.Mesh3d(
            x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
            i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
            name=name,
            color=_MESH_COLORS.get(name, 'red'),
            opacity=0.6
        ))

    # ── Surgical paths ─────────────────────────────────────────
    if paths:
        for rank, (score, path) in enumerate(paths[:2]):
            arr   = np.array(path)
            color = _PATH_COLORS[rank]
            fig.add_trace(go.Scatter3d(
                x=arr[:, 0], y=arr[:, 1], z=arr[:, 2],
                mode='lines',
                line=dict(color=color, width=6),
                name=f'Path #{rank + 1}  (score {score:.2f})'
            ))
            entry = arr[0]
            fig.add_trace(go.Scatter3d(
                x=[entry[0]], y=[entry[1]], z=[entry[2]],
                mode='markers',
                marker=dict(size=7, color=color, symbol='circle'),
                name=f'Entry #{rank + 1}'
            ))

    # ── Surgical target ────────────────────────────────────────
    if target_vox is not None:
        fig.add_trace(go.Scatter3d(
            x=[target_vox[0]], y=[target_vox[1]], z=[target_vox[2]],
            mode='markers',
            marker=dict(size=9, color='red', symbol='diamond'),
            name='Surgical Target'
        ))

    fig.update_layout(
        title=dict(text='Integrated 3D Surgical Planning', font=dict(color='white')),
        paper_bgcolor='#0d1117',
        scene=dict(
            xaxis=dict(title='X', backgroundcolor='#0d1117', gridcolor='#333'),
            yaxis=dict(title='Y', backgroundcolor='#0d1117', gridcolor='#333'),
            zaxis=dict(title='Z', backgroundcolor='#0d1117', gridcolor='#333'),
        ),
        legend=dict(x=0, y=1, font=dict(color='white'), bgcolor='rgba(0,0,0,0.4)')
    )

    plotly_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # ── 2D collapsible views ───────────────────────────────────
    views_html = ''
    if t1_data is not None:
        try:
            views_html = _generate_2d_views_html(masks_dict, functional_masks, t1_data)
        except Exception:
            pass

    _write_combined_html(output_path, plotly_html, views_html)
    return output_path


def _write_combined_html(path, plotly_html, views_html):
    css = """
body { margin:0; background:#0d1117; color:#e6edf3; font-family:'Segoe UI',sans-serif; }
.container { max-width:1400px; margin:0 auto; padding:16px; }
.views2d-wrap { margin-top:24px; }
.views2d-toggle {
  background:#161b22; border:1px solid #30363d; color:#58a6ff;
  padding:10px 20px; border-radius:8px; cursor:pointer; font-size:14px;
  transition:background 0.2s;
}
.views2d-toggle:hover { background:#21262d; }
.views2d-panel { margin-top:16px; padding:16px; background:#161b22;
                 border:1px solid #30363d; border-radius:10px; }
.views2d-hint  { font-size:13px; color:#8b949e; margin-bottom:12px; }
.views2d-sub   { font-size:14px; color:#c9d1d9; margin:0 0 8px 0; }
"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Surgical Planning Viewer</title>
<style>{css}</style>
</head>
<body>
<div class="container">
{plotly_html}
{views_html}
</div>
</body>
</html>"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
