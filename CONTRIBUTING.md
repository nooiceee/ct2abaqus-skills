# Contributing

Issues and pull requests are welcome. Use synthetic or properly shareable minimal data so another person can reproduce the behavior without accessing patient scans or a private workstation.

For bugs, include the release/commit, operating system, Python/Slicer/Abaqus versions, relevant non-identifying configuration, expected behavior, actual status/error and the smallest synthetic reproduction. Remove patient identifiers and local credentials from logs.

For code changes:

1. Keep source images, physical transforms and review states traceable.
2. Add a focused regression test when changing deterministic mesh/coordinate/archive logic.
3. Run `python -m unittest discover -s tests -v` and Python syntax checks.
4. For changes to Slicer/Abaqus APIs, state whether actual integration was run, on which versions, and what remains untested. Unit tests are not a replacement for application integration.
5. Explain geometric or physical changes explicitly. Do not hide meshing failures by moving anatomy, silently filling cavities or adding constraints.

The basic CI suite needs NumPy only and uses no FE solver. The existing release record is historical evidence; do not edit it to imply tests were rerun when they were not. Add a new dated record for new integration evidence.

Original contributions are submitted under the repository's MIT license. Do not contribute third-party software, restricted anatomy, scans or weights without an appropriate license and provenance. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
