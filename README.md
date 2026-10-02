# crs-lint

<img alt="EasyxLab tool" src="https://raw.githubusercontent.com/easybytehub/crs-lint/main/.github/badge-tool.svg">

Offline linter for **OECD Common Reporting Standard XML** files — schema **v2.0** and
schema **v3.0** (CRS 2.0, used for exchanges from 1 January 2027). It checks the file
against the official XSD and, above all, against the **business rules** that today you
only discover when the administration sends back a CRS Status Message. Every finding
cites the **official OECD error code** (50007, 60011, 80010…) and the literal rule, with
the document and page it comes from.

```text
$ crs-lint report.xml
crs-lint · 1 file
  report.xml: schema 3.0 · exchange

ERROR        OECD-60017 (60017) [line 134]: Specified Electronic Money Product
             AcctNumberType is OECD606 and AccountType is CRS1102.
             citation: "A Specified Electronic Money Product (AccountNumber is OECD606)
             must be a Depository Account (AccountType is CRS1101)." — OECD (2025), Common
             Reporting Standard Status Message XML Schema: User Guide for Tax
             Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31

1 error · 0 warnings · 0 undetermined
```

A clean run ends with what it does and does not mean:

```text
$ crs-lint clean.xml
crs-lint · 1 file
  clean.xml: schema 3.0 · exchange

No findings.
0 errors · 0 warnings · 0 undetermined
Zero errors means these rules found nothing; it does not mean the administration will
accept the file. Checks that need the receiver's records (earlier submissions, TIN
registers) were not run.
```

With several files, each finding is labelled `[file:line]` instead of `[line N]`.

## Why

An XSD only says the file is well typed. The OECD CRS Status Message User Guide lists
the record errors a receiving administration returns — a depository account with a
dividend payment, an e-money product that is not a depository account, a correction
without `CorrDocRefId`, a message that mixes new and corrected records — and most of
them pass schema validation. The open-source CRS validators we found stop at the
XSD. crs-lint implements the rules that can be decided from the file, and says which ones
cannot.

## What it checks

- **Schema** (50007) with the official XSD of the detected version, bundled — never
  downloaded.
- **41 OECD Status Message codes**: file errors 50007-50012 (50012 partially), all
  record errors 60000-60023 (IBAN and ISIN structure, balances, holder types and
  controlling persons,
  data sorting by country, birth dates, the v3.0 account-type rules such as OECD606
  *Specified Electronic Money Product*) and the correction-process errors 80000, 80001,
  80004-80011 and 80015 (DocRefId uniqueness, CorrDocRefId, DocTypeIndic combinations,
  resend option, nil reporting).
- Two User Guide rules without a code: the root `version` attribute and the
  `Timestamp` milliseconds format.

The full list, with the literal OECD text and page of each rule, is in
[SPEC.md](SPEC.md).

## What it does not check

- Anything that needs the receiver's records: a `DocRefId` or `MessageRefId` used in an
  **earlier** submission (it does catch duplicates inside a file and across the files
  you pass in one run), an unknown or outdated `CorrDocRefId`, a resend of an unknown
  record.
- National TIN rules (OECD codes 90000-90002 are reserved for future use) and national
  profiles such as Spain's modelo 289 envelope or IRAS identifier formats.
- Transport: encryption, signature, compression (the CTS errors).

**A clean result does not mean the administration will accept the file.** It means
these rules found nothing.

## Install and use

`pip install crs-lint` will work once the package is published on PyPI. Until then,
install the wheel attached to a GitHub release, or from source:

```bash
pip install git+https://github.com/easybytehub/crs-lint
crs-lint reports/*.xml
crs-lint report.xml --schema-version 3.0 --format sarif > crs-lint.sarif
```

| Option | Meaning |
|---|---|
| `--schema-version auto\|2.0\|3.0` | `auto` reads it from the root namespace. A fixed version also asserts it: a v2.0 file under `--schema-version 3.0` is an error. |
| `--format text\|json\|sarif` | SARIF goes to GitHub code scanning, with the XML line of each finding. |
| `--strict` | Warnings also fail. |
| `--context auto\|exchange\|domestic` | See below. |

**Exit codes:** `0` no errors · `1` errors (or warnings with `--strict`) · `2` the tool
could not do its job (missing file, DTD refused, root that is not `CRS_OECD`, a
resource limit of the parser such as a text node over 10 MB — `TOOL-001` —, internal
error). Malformed XML is a finding (50007), not a 2.

### Exchange or domestic

The Status Message rules are written for messages between Competent Authorities. For a
Financial Institution filing with its own administration the OECD User Guide makes both
countries the domestic one — for `TransmittingCountry` and `ReceivingCountry` it says
"[For domestic reporting this element would be the domestic Country Code.]" (UG
v4.0, 2024, PDF p. 10) — and identifiers follow a national format (IRAS: year + tax
reference + …). In a domestic file crs-lint does not apply 50008, 60011 and 60012, and
reports 80001 (DocRefID must start with the sending country code "in all cases") as a
warning.

When the context is **detected** (same country twice) rather than given, the report
says so with a `CTX-DOMESTIC` warning, in every output format: an exchange mislabelled
with the same country twice must not pass silently. Pass `--context domestic` to state
it explicitly (and silence the notice), or `--context exchange` to apply every rule;
with the same country twice that also gives a 50012 warning.

## GitHub Action

```yaml
permissions:
  contents: read
  security-events: write   # upload-sarif needs it

# …in the job's steps:
- uses: easybytehub/crs-lint@4c8ac3beb6fd1eedd59b20e3f8d3e982bf300ed7  # v0.1.0
  with:
    files: |
      out/crs/*.xml
    schema-version: "3.0"
    fail: "false"            # keep going so the SARIF gets uploaded
- uses: github/codeql-action/upload-sarif@2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2  # v4.38.2
  if: always()
  with:
    sarif_file: crs-lint.sarif
```

The action installs crs-lint from its own code, not from PyPI: the commit you pin is the
code that runs.

## Safety

Read-only and offline. XML is parsed without DTDs, without entity resolution and without
network access, and any document that declares a `DOCTYPE` is refused before parsing (a
CRS message never needs one). Test fixtures are synthetic.

## Dates that matter

- **EU:** DAC8 amends DAC2 to bring in CRS 2.0 — data from 2026, first exchanges in 2027.
- **Singapore (IRAS):** CRS XML v3.0 mandatory from 1 January 2027.
- **OECD:** the v3.0 Status Message applies to exchanges from 1 January 2027.

## Licence

crs-lint is Apache-2.0. The bundled XSDs are © OECD, reproduced unmodified as
published by IRAS and subject to the OECD Terms and Conditions; they are bundled so the
tool works offline (see `NOTICE` and `src/crs_lint/esquemas/README.md`). Hence the
package licence expression `Apache-2.0 AND LicenseRef-OECD`. Made by EasyxLab, the research lab of EasyByte Hub S. Coop.
Mad. (Spain).

---

EasyxLab · a research lab by [EasyByte](https://easybyte.es)
