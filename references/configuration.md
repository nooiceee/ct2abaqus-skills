# Configuration and outputs

The agent discovers software and prepares JSON; the user supplies images, not a long technical questionnaire.

## Software

- Full 3D Slicer application, tested5.12.4. Use `slicer_executable` or `SLICER_EXECUTABLE`, not `PythonSlicer`: the latter alone lacks a running MRML scene/Segment Editor.
- External Python3.10+, `numpy`, `gmsh` for tetra mode. Use a project venv; never install into Abaqus Python. See scripts/requirements.txt.
- Optional `abaqus_command`: CAE launcher with a normal license. Without it INP can still exist; record `CAE_NOT_RUN`. Software/licenses are not bundled.
- Windows/Linux/macOS paths are configurable. No F drive, account, remote machine or historical node numbering is required. Keep installation paths vendor-compatible.
- Release execution was checked on Windows11, Slicer5.12.4 and Abaqus2025. Other OS/version combinations need their own startup/import check. Full-app Slicer needs an appropriate graphical session; hiding its main window does not supply a display server on a headless Linux host.

## Fields

`image`: absolute volume/DICOM directory/MRB/ZIP. `segmentation`: optional segmentation or labelmap. `archive_image_member`/`archive_segmentation_member` select paths inside a ZIP when needed; multiple scalar files otherwise yield `NEEDS_IMAGE_FILE_SELECTION`. A unique `.seg.nrrd` in a ZIP is recognized. `label_names`: integer-string→name. `selected_segments`: names to include; empty means all nonempty labels, not that all are mechanically compatible. `image_node_name`/`segmentation_node_name` resolve MRB ambiguity. `series_uid` selects DICOM. `segmentation_reviewed` records actual review.

`output_dir` must not exist. Resume corrected labels into a new folder with original image and new segmentation. `timeout_seconds` defaults900 per application stage; diagnose instead of indefinitely restarting. Threads default2. No image data are uploaded by these scripts.

Automatic threshold requires `modality=CT` and `intensity_is_hu=true`. Threshold/component limits are recorded initial choices. Omitted components are reported. Raw MRI instead yields `NEEDS_SEGMENTATION` and a manual workspace.

`mesh_mode`: `tet`/`voxel`. `target_edge_mm`: a target, with actual edge statistics reported. `fallback_to_voxel` is explicit. `max_tet_volume_change_fraction=.05` is a candidate screen relative to label voxels, not a literature standard or anatomical error. `max_voxel_elements_per_part` bounds memory; exceeding it stops that part without silently coarsening. `geometry_only` stays true.

## Files

- `source_image.nrrd`, `segmentation.seg.nrrd`, `manual_review.mrb`: image/labels for review.
- `prepared.json`: input provenance, image transform, labels/components, resampling and review state.
- `surfaces/`, `masks/`: per-component STL and cropped mask, RAS/mm.
- `model/image_geometry.inp`: real C3D4/C3D8 only when at least one region succeeded.
- `model/image_geometry.cae`: only after optional actual import.
- `mesh_report.json`, `abaqus_import.json`, `STATUS.json`, logs, `manifest.json`: failures, actual counts and hashes.

Some parts can succeed while another fails: report `complete_requested_regions=false` and missing names. An auto-CT prototype keeps `NEEDS_SEGMENTATION_REVIEW` even if mesh/import succeeded. Per-part positivity is not a global collision test. Missing quantities stay missing, not zero. Analysis is always `NOT_RUN` here.
