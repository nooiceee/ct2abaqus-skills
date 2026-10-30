# Sources and demonstrated limits

- Slicer Python context: https://slicer.readthedocs.io/en/latest/developer_guide/python_faq.html
- CLI and DICOM: https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html
- Segmentation: https://slicer.readthedocs.io/en/latest/user_guide/modules/segmenteditor.html
- Coordinates: https://slicer.readthedocs.io/en/latest/user_guide/coordinate_systems.html
- Gmsh STL remeshing: https://gmsh.info/doc/texinfo/#t13
- Abaqus import: https://docs.software.vt.edu/abaqusv2025/English/SIMACAEKERRefMap/simaker-c-modelpyc.htm
- Akrami2018 MRI→Mimics→SolidWorks: https://pmc.ncbi.nlm.nih.gov/articles/PMC5845092/

SolidWorks is optional. STL is a surface; converting it to STEP does not automatically recover smooth editable anatomy. Actual volume meshes can enter Abaqus as orphan meshes.

The source project demonstrated CT→28bone volumes and MRI→bone/muscle surfaces plus two volume regions. It reused published segmentations, not a validated universal automatic segmentation. CT: Fischer2023/VSD/BoneHub, https://doi.org/10.1038/s41597-023-02669-z and https://huggingface.co/datasets/BoneHub/vsd-feet-seg (CC BY-NC-SA4.0). MRI: https://doi.org/10.22452/RD/5T6TZ7 (CC0); its MRI re-export had a CT modality tag. No software/data/model binaries are bundled.

The release-test record states which generic branches ran. Syntax checking is not functional testing. Synthetic cases test transforms, occupancy and pipeline mechanics; they do not validate human segmentation. Open-data demonstrations do not establish clinical accuracy, convergence or solve cost.

Actual generic-helper release checks: [release-tests.json](release-tests.json). These are conversion/import tests, not finite element loading tests.
