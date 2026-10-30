# Validation record and scope

This records **conversion and import checks**, not finite element loading, clinical accuracy or mesh convergence.

## Executed integration checks

Initial environment: Windows 11, external Python 3.13, Slicer 5.12.4, Abaqus/CAE 2025. [Machine-readable record](../references/release-tests.json).

| Case | Actual outcome |
|---|---|
| Synthetic image + supplied labels, from an independent copied installation | 3 parts; 1,991 C3D4 + 374 C3D8; actual CAE import verified |
| Raw synthetic calibrated CT | 987 C3D8; candidate segmentation retained for review |
| Synthetic DICOM CT series | Same 987-voxel occupancy and physical volume as its volume-file counterpart |
| Unlabeled MRI-mode fixture | Manual review scene; `NEEDS_SEGMENTATION`; no invented INP |
| Open-data calcaneus label + CT | 29,253 C3D4; actual CAE import verified |

The exported INP was independently reread for node references and positive signed determinants. MRB archive CRCs passed. The synthetic fixture has a negative-determinant image transform, disconnected components and a small part that exercises explicit voxel fallback. Two tetra attempts exceeded the configured voxel-volume difference screen; the fallback and reasons were retained rather than called a successful tetra result.

Archive checks also rejected path traversal and stopped for ambiguous scalar-volume selection. No finite element analysis was submitted in these checks.

## What CI checks

CI on Linux/Windows uses small synthetic arrays and the Python standard test framework. It checks affine voxel geometry, positive orientation, element-budget stopping and archive/selection behavior, plus Python syntax. It does **not** install Slicer/Abaqus, use a commercial license or claim those integration checks have rerun on every commit.

```bash
python -m unittest discover -s tests -v
```

## Important limits

- The open-data demonstration reused published segmentation. It did not validate automatic anatomical segmentation from an arbitrary new scan.
- Tetra/voxel volume differences are relative to label occupancy, not measured human anatomical error.
- Per-part closure and positive volumes do not rule out inter-part intersections. Actual interface review remains necessary.
- CT and MRI examples came from different subjects and were kept separate.
- No automated material assignment, PA/ligament model, joint interaction, reference-state calibration or standing boundary condition was validated here.
- No pressure prediction, independent experiment, quasi-static criterion or compute-time target was validated.
- Other OS/Slicer/Abaqus versions need their own startup/import checks.

Data/software citations and license distinctions: [sources](../references/sources-and-validation.md). No original scan, patient model or proprietary software is included in the repository.
