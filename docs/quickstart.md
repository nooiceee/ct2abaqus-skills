# Quick start / 快速开始

## Prepare the tools

Install [3D Slicer](https://download.slicer.org/). Use the full application executable, not `PythonSlicer`: segmentation editing needs the application context. Set the executable in your JSON or the `SLICER_EXECUTABLE` environment variable. Full-app batch mode needs a graphical session even when its window is hidden.

Create an external Python venv and install `scripts/requirements.txt`. Use its interpreter for every command below. Do not install into Abaqus's Python.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r scripts/requirements.txt
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -r scripts/requirements.txt
```

Optional Abaqus/CAE must already be installed and licensed. Set `abaqus_command` to its normal launcher. The helpers never create an analysis Job.

## A. Image with an existing segmentation

Copy [the example configuration](../assets/config.example.json). Set `image`, `segmentation`, `output_dir`, and software paths. For a generic integer labelmap, provide `label_names`. For `.seg.nrrd`, existing names are retained.

```json
{
  "image": "/data/foot.nii.gz",
  "segmentation": "/data/foot.seg.nrrd",
  "selected_segments": ["Calcaneus_R"],
  "segmentation_reviewed": false,
  "output_dir": "/data/new_reconstruction",
  "slicer_executable": "/apps/Slicer/Slicer",
  "abaqus_command": null,
  "mesh_mode": "tet",
  "target_edge_mm": 1.5,
  "fallback_to_voxel": true,
  "geometry_only": true
}
```

The paths/names are examples, not a portable assumption about your scan. On Windows, JSON can use forward slashes such as `C:/Apps/Slicer/Slicer.exe`.

```bash
python scripts/run_pipeline.py --config /absolute/path/config.json
```

The output directory must be new. Do not set `segmentation_reviewed=true` merely because labels exist. Each face-connected component becomes a separate part with a parent-label mapping. No interface constraints are inferred.

## B. Raw CT without labels

Set `image` to a complete DICOM directory/ZIP or calibrated CT volume. Set `modality` to `CT` and `intensity_is_hu` to `true` only when source metadata/provenance support Hounsfield units. The default threshold is an engineering starting point.

The result is a candidate segmentation with neutral component names, a review scene and a possible mesh prototype. It retains `NEEDS_SEGMENTATION_REVIEW`. Thresholding can fuse bones or omit low-density/very small structures; cortex-only masks are not automatically whole-bone solid labels.

For several DICOM series, inspect the returned inventory and set `series_uid` in a new run. Do not merge acquisitions by filename. ZIPs with multiple scalar volumes require `archive_image_member`, or explicit image selection after unpacking.

## C. Raw MRI without labels

Set `modality` to `MRI`. The helper creates `manual_review.mrb` and `NEEDS_SEGMENTATION`; it does not apply a CT HU threshold. Segment in Slicer with manual/assisted tools, save `.seg.nrrd`, then use case A in a new output directory. Match labels to physical coordinates, not array indices.

## D. Try the synthetic fixture

```bash
python scripts/create_test_fixture.py --out /absolute/path/new_fixture
```

Use its `synthetic_CT.nrrd` and `labels.nrrd`, mapping labels `1`/`2` to neutral test names. The image has a negative-determinant direction matrix to exercise orientation handling. It is not a patient or anatomical validation case.

## Inspect the output

1. Open `manual_review.mrb` in Slicer and inspect source/labels in orthogonal views.
2. Read `STATUS.json`, `prepared.json` and `mesh_report.json`. A successful exit does not override missing parts or unreviewed anatomy.
3. Open `model/image_geometry.inp` in Abaqus, or use the actually generated CAE if available.
4. Check the manifest after applications have exited; CAE close/compaction can change the file bytes after `saveAs`.

For corrected labels, point to the updated segmentation in a **new output directory**. Preserve the original image, old outputs and reference-state decisions. Numerical analysis and complete mechanical definitions are outside this conversion command.
