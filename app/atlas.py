import os
import numpy as np
import nibabel as nib
import SimpleITK as sitk
from nilearn import datasets

ATLAS_DATA_DIR = "data/atlas"

# ── Functional groups (for risk map / A* cost) ────────────────
REGION_INDICES = {
    'motor':    [7, 17, 26],   # Precentral, Postcentral, Supplementary Motor
    'language': [5, 6, 10],    # Broca x2, Wernicke (MTG)
    'visual':   [22, 23],      # Lateral Occipital superior + inferior
}

# ── Individual cortical regions for 3D viewer ─────────────────
# atlas_value: (hex_color, scatter_opacity, display_name)
CORTICAL_DISPLAY = {
    7:  ('#3b82f6', 0.50, 'Precentral Gyrus (Motor Cortex)'),
    17: ('#93c5fd', 0.40, 'Postcentral Gyrus (Sensory Cortex)'),
    26: ('#1d4ed8', 0.45, 'Supplementary Motor Area'),
    5:  ('#10b981', 0.50, "Broca's Area – IFG triangularis"),
    6:  ('#059669', 0.50, "Broca's Area – IFG opercularis"),
    10: ('#6ee7b7', 0.45, "Wernicke's Area (Middle Temporal Gyrus)"),
    22: ('#a855f7', 0.50, 'Lateral Occipital Cortex sup. (Visual)'),
    23: ('#7c3aed', 0.45, 'Lateral Occipital Cortex inf. (Visual)'),
    3:  ('#f59e0b', 0.22, 'Superior Frontal Gyrus'),
    4:  ('#d97706', 0.22, 'Middle Frontal Gyrus'),
    29: ('#f472b6', 0.22, 'Superior Parietal Lobule'),
    30: ('#db2777', 0.22, 'Angular Gyrus (Inferior Parietal)'),
}

# ── Subcortical structures for 3D viewer ─────────────────────
# tuple-of-atlas-values: (hex_color, scatter_opacity, display_name)
SUBCORTICAL_DISPLAY = {
    (1, 12): ('#cbd5e1', 0.06, 'Cerebral White Matter'),
    (4, 15): ('#fde047', 0.40, 'Thalamus'),
    (9, 19): ('#fb923c', 0.40, 'Hippocampus'),
}

_cache = {}


def _parse_labels(labels_list):
    """Map atlas value (1-based) → region name, regardless of nilearn version."""
    if labels_list and labels_list[0].strip().lower() in ('background', ''):
        return {i: name for i, name in enumerate(labels_list[1:], start=1)}
    return {i: name for i, name in enumerate(labels_list, start=1)}


def ensure_atlas(progress_cb=None):
    if _cache.get('ready'):
        return _cache

    os.makedirs(ATLAS_DATA_DIR, exist_ok=True)

    if progress_cb:
        progress_cb("Downloading Harvard-Oxford cortical atlas...")

    ho_cort = datasets.fetch_atlas_harvard_oxford(
        'cort-maxprob-thr25-1mm',
        data_dir=ATLAS_DATA_DIR,
        symmetric_split=False
    )
    cort_img    = nib.load(ho_cort['maps'])
    cort_data   = cort_img.get_fdata().astype(np.int32)
    cort_labels = _parse_labels(list(ho_cort['labels']))

    # ── Functional group masks (risk map) ────────────────────
    mni_mask_paths = {}
    for region, indices in REGION_INDICES.items():
        mask = np.isin(cort_data, indices).astype(np.uint8)
        path = os.path.join(ATLAS_DATA_DIR, f'{region}_mask_mni.nii.gz')
        nib.save(nib.Nifti1Image(mask, cort_img.affine), path)
        mni_mask_paths[region] = path

    # ── Individual cortical display regions ──────────────────
    cort_display_paths = {}
    for val, (color, opacity, fallback_name) in CORTICAL_DISPLAY.items():
        name = cort_labels.get(val, fallback_name)
        mask = (cort_data == val).astype(np.uint8)
        path = os.path.join(ATLAS_DATA_DIR, f'cort_{val}.nii.gz')
        nib.save(nib.Nifti1Image(mask, cort_img.affine), path)
        cort_display_paths[val] = {'path': path, 'color': color, 'opacity': opacity, 'name': name}

    if progress_cb:
        progress_cb("Downloading Harvard-Oxford subcortical atlas...")

    ho_sub   = datasets.fetch_atlas_harvard_oxford(
        'sub-maxprob-thr25-1mm',
        data_dir=ATLAS_DATA_DIR,
        symmetric_split=False
    )
    sub_img  = nib.load(ho_sub['maps'])
    sub_data = sub_img.get_fdata().astype(np.int32)

    # ── Subcortical display regions ───────────────────────────
    sub_display_paths = {}
    for vals, (color, opacity, name) in SUBCORTICAL_DISPLAY.items():
        mask = np.isin(sub_data, list(vals)).astype(np.uint8)
        fname = f'sub_{"_".join(str(v) for v in vals)}.nii.gz'
        path  = os.path.join(ATLAS_DATA_DIR, fname)
        nib.save(nib.Nifti1Image(mask, sub_img.affine), path)
        sub_display_paths[name] = {'path': path, 'color': color, 'opacity': opacity}

    if progress_cb:
        progress_cb("Downloading MNI152 template...")

    mni_img  = datasets.load_mni152_template(resolution=1)
    mni_path = os.path.join(ATLAS_DATA_DIR, 'mni152_template.nii.gz')
    nib.save(mni_img, mni_path)

    _cache.update({
        'mni_path':           mni_path,
        'mni_mask_paths':     mni_mask_paths,
        'cort_display_paths': cort_display_paths,
        'sub_display_paths':  sub_display_paths,
        'ready': True,
    })
    return _cache


def register_atlas_to_patient(patient_t1_path, progress_cb=None):
    """
    Register MNI atlas to patient T1 space.

    Returns
    -------
    functional_masks : dict  {motor|language|visual → np.uint8 array}
        Used by risk-map and path planning.
    display_regions  : dict  {label_name → {mask, color, opacity}}
        15 individually labelled structures for the 3D viewer.
    """
    cache = ensure_atlas(progress_cb)

    if progress_cb:
        progress_cb("Registering MNI template to patient space (1–3 min)...")

    fixed  = sitk.ReadImage(patient_t1_path, sitk.sitkFloat32)
    moving = sitk.ReadImage(cache['mni_path'], sitk.sitkFloat32)

    initial_transform = sitk.CenteredTransformInitializer(
        fixed, moving,
        sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY
    )
    reg = sitk.ImageRegistrationMethod()
    reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    reg.SetMetricSamplingStrategy(reg.RANDOM)
    reg.SetMetricSamplingPercentage(0.01)
    reg.SetInterpolator(sitk.sitkLinear)
    reg.SetOptimizerAsGradientDescent(
        learningRate=1.0, numberOfIterations=100,
        convergenceMinimumValue=1e-6, convergenceWindowSize=10
    )
    reg.SetOptimizerScalesFromPhysicalShift()
    reg.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    reg.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    reg.SetInitialTransform(initial_transform, inPlace=False)
    final_transform = reg.Execute(fixed, moving)

    def _warp(nii_path):
        mask_sitk = sitk.ReadImage(nii_path, sitk.sitkFloat32)
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(fixed)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetTransform(final_transform)
        resampler.SetDefaultPixelValue(0)
        warped = resampler.Execute(mask_sitk)
        # SimpleITK → (z,y,x); flip to (x,y,z) matching nibabel
        arr = (sitk.GetArrayFromImage(warped) > 0.5).astype(np.uint8)
        return np.transpose(arr, (2, 1, 0))

    if progress_cb:
        progress_cb("Warping functional masks to patient space...")

    functional_masks = {
        region: _warp(path)
        for region, path in cache['mni_mask_paths'].items()
    }

    if progress_cb:
        progress_cb("Warping 15 labelled atlas regions to patient space...")

    display_regions = {}

    for val, meta in cache['cort_display_paths'].items():
        warped = _warp(meta['path'])
        if warped.sum() > 0:
            display_regions[meta['name']] = {
                'mask':    warped,
                'color':   meta['color'],
                'opacity': meta['opacity'],
            }

    for name, meta in cache['sub_display_paths'].items():
        warped = _warp(meta['path'])
        if warped.sum() > 0:
            display_regions[name] = {
                'mask':    warped,
                'color':   meta['color'],
                'opacity': meta['opacity'],
            }

    return functional_masks, display_regions
