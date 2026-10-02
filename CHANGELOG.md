# Changelog

## 0.1.0 — unreleased

First version. Includes the fixes of the adversarial review of 2026-10-02:

- A detected domestic context is reported (`CTX-DOMESTIC`, warning, in text, JSON and
  SARIF); `--context exchange` with the same country twice gives a 50012 warning.
- The domestic mode cites the OECD User Guide ("[For domestic reporting this element
  would be the domestic Country Code.]"); 80001 is no longer skipped in domestic files,
  it is a warning there.
- A valid IBAN in print format (spaces, lower case) is a 60000 warning, not an error.
- A parser resource limit is `TOOL-001` with exit 2, not a 50007.
- SARIF URIs are percent-encoded (paths with spaces).
- The "zero errors" notice is only printed when there are no errors.
- `NOTICE` for the bundled OECD XSDs; licence expression `Apache-2.0 AND
  LicenseRef-OECD`. ruff and mypy pinned in the dev extras.
- release.yml runs the full test matrix before building, and uses
  attest-build-provenance v4.2.2.
- The reviewer's files are kept as regression fixtures (`tests/fixtures/review/`).

- CLI `crs-lint <files…> [--schema-version auto|2.0|3.0] [--format text|json|sarif]
  [--strict] [--context auto|exchange|domestic]`, exit codes 0/1/2.
- XSD validation (OECD code 50007) with the official schemas v2.0 and v3.0 bundled.
- 41 OECD CRS Status Message codes implemented: 50007-50012, 60000-60023, 80000, 80001,
  80004-80011, 80015; plus `UG-VERSION` and `UG-TIMESTAMP` from the User Guide.
- Each finding cites the OECD code, the literal rule and the document and PDF page.
- Exchange/domestic context: 50008, 60011 and 60012 only between Competent
  Authorities; 80001 as a warning in domestic files.
- Safe parsing: DOCTYPE refused, no DTD, no entities, no network.
- GitHub Action (composite, installs from its own code) and SARIF output with lines.
- 48 synthetic fixtures: one valid file per schema version, one domestic file and one
  per rule.
