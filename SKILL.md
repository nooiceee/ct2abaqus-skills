---
name: ct2abaqus-skills
description: Convert uploaded CT/MRI volumes and anatomical segmentations into auditable Abaqus volume meshes and CAE previews. Use for DICOM, NIfTI, NRRD or Slicer image-to-model reconstruction, including segmentation preparation when only images are available.
---

# CT/MRI → Abaqus

Deliver an actual image-derived geometry mesh, its provenance/quality record, and a CAE when Abaqus/CAE is available. Explain the achieved level: image inspection, candidate segmentation, reviewed segmentation, volume mesh, CAE import, or mechanical model. Geometry import does not imply a load-ready or validated prediction model.

## Execute

1. Locate the uploads and installed 3D Slicer/Python; discover paths or configure them. Check memory, use a fresh output directory, preserve sources and running jobs. Missing open tools can be installed in an isolated location within the user's task. SolidWorks is optional.
2. Read [the workflow](references/workflow.md). Unpack safely, identify one physical image series and its scale/direction. Resolve ambiguous series, mixed subjects, missing spacing or inconsistent modality. Screenshots alone do not establish calibrated 3D geometry.
3. Choose the entry:
   - **Supplied segmentation:** preserve names, physical positions and reference image. Select relevant structures. Disclose supplied vs new labels and any resampling.
   - **Raw CT:** create an explicitly unreviewed threshold/component candidate and Slicer scene, then a geometry prototype when possible. Thresholds are starting engineering choices. Components are not anatomical identities. Correct fused joints, holes and small bones; request only specific unresolved anatomical decisions.
   - **Raw MRI:** create a manual/assisted segmentation workspace. Use appropriate tools or verified models, never CT HU thresholds. Without nonempty labels, retain `NEEDS_SEGMENTATION` and the workspace rather than fabricate a mesh.
4. Configure [the example](assets/config.example.json) with absolute paths. From external Python with `numpy` and `gmsh`, run `python scripts/run_pipeline.py --config /absolute/path/config.json`. It invokes Slicer application Python, meshes labels, writes geometry-only INP and optionally imports CAE. It does not submit analysis. Use the normal Slicer application with its main window hidden during batch work; no-main-window Segment Editor failed in the demonstrated Windows build.
5. Inspect actual reports/meshes: coordinates, label coverage, positivity, duplicates, closure, components, volume changes and quality distribution. Per-part checks do not prove collision-free interfaces. Preserve failures; do not move anatomy, fill joints or add Tie/Embedded constraints merely for meshing.
6. Give a short answer and paths to `manual_review.mrb`, `image_geometry.inp`, optional `image_geometry.cae`, and `STATUS.json`, with remaining reviews. Share the skill folder when requested, without patient data, software executables or solver credentials.

## Reuse and boundaries

- Read [configuration and outputs](references/configuration.md) for setup/resume, and [sources and verified scope](references/sources-and-validation.md) for APIs and limits.
- Retain label volumes and physical coordinates, not only STL. A display surface, volume mesh and assigned physical shell are distinct. Default outputs contain real C3D4/C3D8 with no material, contact, BC or analysis step.
- Tetra meshing is preferred; an unsuccessful tetra reconstruction may fall back to explicitly reported voxel mesh only if configured. Voxel geometry is blocky and is not a converged contact mesh.
- For a complete mechanical model, separately establish anatomy-specific materials, joints, skin, PA/ligaments/tendons, interfaces, reference state, loads and validation. Do not transplant old subject coordinates or attachments. This skill does not authorize FE jobs, remote-host operations or paid resources.
