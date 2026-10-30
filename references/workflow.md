# Workflow and decisions

## Intake

Use uploaded volumes, not screenshots. DICOM folders can contain multiple subjects/series; inventory before selecting one. Preserve spacing, direction, origin and IJK→RAS in mm. MRI re-export tags can disagree with source provenance; do not interpret MRI gray levels as HU because one tag says CT.

`run_pipeline.py` accepts a DICOM directory, NIfTI/NRRD volume, Slicer MRB or ZIP. ZIP paths are checked before extraction. A ZIP with one scalar-volume file selects it; otherwise its extracted directory is treated as DICOM. Large archives may be extracted separately. Multiple DICOM series yield an inventory and `NEEDS_SERIES_SELECTION`; select `series_uid` in a new run. No series are automatically merged.

## Segmentation

Supplied `.seg.nrrd` or labelmaps can be loaded with original names or `label_names`. MRB uses its image/segmentation nodes; select `image_node_name`/`segmentation_node_name` if ambiguous. Parent transforms are not silently dropped: harden in a separate confirmed copy or adapt before continuing.

Without labels, calibrated CT may use threshold/components as a candidate. Set `intensity_is_hu=true` only with source evidence. `fill_internal_holes` is false: filling marrow/cavities changes occupancy and requires an explicit choice. Components receive neutral names; touching bones can remain fused. Cortex-only labels differ from whole-bone solids. MRI without labels creates an editing workspace, not invented anatomy.

Use Paint/Draw/Erase, Grow from seeds or Fill between slices as appropriate. Contour interpolation does not independently inspect gray-level boundaries. Check orthogonal/oblique slices, save segmentation and source image. The helper exports each label on the source-image grid by nearest-neighbor resampling and records native/reference volume estimates. Finer or offset segmentations require review of this discretization; do not align arrays merely by their indices.

## Mesh and interfaces

Split face-connected components into parts while recording parent labels. A combined label with 14 components is not 14 already identified bones. Disable surface smoothing during export. Gmsh remeshes before C3D4 generation. Multiple boundary shells in one component are not guessed into a cavity hierarchy: reject tetra meshing and use configured voxel fallback if appropriate. This does not authorize filling holes.

Check closure, signed volumes, repeats, face incidence, gamma and volume change. Voxel fallback retains native occupancy using affine C3D8 but has stepped boundaries. Neither method automatically couples separate parts. Inspect interfaces and collisions separately; shared corners/one component do not prove correct mechanics. Do not assign every nonbone voxel one soft material or treat display shells as skin with known thickness.

## Completion

INP contains independent orphan-mesh parts, element sets and assembly. Optional CAE import verifies actual mesh counts. No materials, contacts, loads or analysis steps are added. Newer CAE databases may not open in older releases; retain INP and check the target version when needed.

Stop at actual geometry/import evidence. Prediction additionally needs physical interfaces, materials, reference state, loads, initialization, numerical validity and independent validation. Imported geometry or lower pressure alone is not physiological validation. The helpers never run FE analysis.
