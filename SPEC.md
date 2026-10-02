# crs-lint — specification (v0.1)

Every rule below quotes **literally** the OECD text it implements, with the document
and the **PDF page** (the page number your PDF viewer shows, not the printed one).
`tests/test_reglas.py` fails if a rule of the catalogue is missing here or its literal
text differs.

## Sources

| Key | Document | Applies to |
|---|---|---|
| SM3 | OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en | CRS XML v3.0 (exchanges from 1 January 2027) |
| SM2 | OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019 | CRS XML v2.0 |
| UG3 | OECD (2024), Amended Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 4.0 – October 2024 (CRS XML Schema v3.0) | CRS XML v3.0 |
| UG2 | OECD (2019), Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 3.0 – June 2019 (CRS XML Schema v2.0) | CRS XML v2.0 |
| XSD | IRAS *CRS Filing* packages, see `src/crs_lint/esquemas/README.md` | both |

Codes 60000-60016 and 80000-80015 have the same number and wording in SM2 and SM3
(the 2025 edition only reflows the table). 60017-60023 are new in SM3 and refer to
elements (`AccountType`, `EquityInterestType`) that exist only in schema v3.0.

Licences: SM3 is CC BY 4.0. SM2, UG2 and UG3 are governed by the OECD Terms and
Conditions (www.oecd.org/termsandconditions); they are quoted briefly and with
attribution. The bundled XSDs are © OECD, see `NOTICE`.

## Interpretations (decided once, applied everywhere)

1. **Exchange vs domestic.** The Status Message governs exchanges between Competent
   Authorities. For domestic reporting the OECD itself sets both countries to the
   domestic one — UG, `TransmittingCountry` and `ReceivingCountry`: "[For domestic
   reporting this element would be the domestic Country Code.]" (UG3 PDF p. 10, UG2 PDF
   p. 12) — and identifiers follow a national format (IRAS: year + tax reference + …).
   In that *domestic* context 50008, 60011 and 60012 are not applied, and 80001 is a
   warning (the UG says "in all cases"). When the context is *detected*
   (`TransmittingCountry` = `ReceivingCountry`) rather than given, the report says so
   with `CTX-DOMESTIC`. `--context` overrides the detection; `--context exchange` with
   the same country twice gives a 50012 warning.
2. **Test codes.** OECD10-OECD13 are the test twins of OECD0-OECD3 (UG defines them one
   by one), so structural rules treat OECD11 as OECD1, and so on.
3. **No rule is stricter or looser than its text.** Where the text cannot be decided
   from the file, the finding is `undetermined` or the rule is listed as out of scope.
4. **Severities.** `error` = the receiver returns that code. `warning` = depends on
   something not in the file. `undetermined` = cannot be decided. Rules marked
   *rejection basis* are in SM's "common approach" list: they may get the whole file
   rejected, not only the record.

## Rules


### `OECD-50007` — Failed Schema Validation

- **OECD code:** 50007 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The referenced file failed validation against the CRS XML Schema."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 32; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 27
- **Check:** lxml/libxml2 validation against the XSD of the detected version (one finding per schema error, line included, capped at 50 per file). Not well-formed XML is also reported here, and so is a file whose namespace is not the version fixed with `--schema-version`.

### `OECD-50008` — Invalid MessageRefID format

- **OECD code:** 50008 · **severity:** error · **schema:** 2.0, 3.0 · **context:** exchange only
- **Literal:** "The structure of the MessageRefID is not in the correct format, as set out in the CRS User Guide. The CRS User guide indicates that the MessageRefID can contain whatever information the sender uses to allow identification of the particular report but must start with the sending country code as the first element for Competent Authority to Competent Authority transmission, then the year to which the data relates, then the receiving country code before a unique identifier (e.g. FR2013CA123456789)."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 32; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 27
- **Check:** Exchange context only. `MessageRefId` must match `<TransmittingCountry><4-digit year><ReceivingCountry><at least one character>`. A year that is neither the year of `ReportingPeriod` nor the one before (the period may start in the previous year) is a warning, not an error.
- **Note:** Not applied to domestic files, where the OECD itself makes both countries the domestic one: [For domestic reporting this element would be the domestic Country Code.] — UG, TransmittingCountry and ReceivingCountry (UG v3.0 schema: PDF p. 10; v2.0: PDF p. 12). The national format of MessageRefID is set by each administration.

### `OECD-50009` — MessageRefID has already been used

- **OECD code:** 50009 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The referenced file has a duplicate MessageRefID value that was received on a previous file."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 33; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 28
- **Check:** Only among the files given in the same run (the same path given twice counts once).
- **Note:** Only checked among the files given in the same run; earlier submissions are known only to the receiving administration.

### `OECD-50010` — File Contains Test Data for Production Environment

- **OECD code:** 50010 · **severity:** warning · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The referenced file contains one or more records with a DocTypeIndic value in the range OECD10-OECD13, indicating test data. As a result, the receiving Competent Authority cannot accept this file as a valid CRS file submission."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 33; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 28
- **Check:** Every `DocTypeIndic` in the file is OECD10-OECD13. Warning: the destination environment is not in the file.
- **Note:** Warning, not error: whether the file goes to production or to a test environment is not in the file.

### `OECD-50010-50011` — Test and live records mixed

- **OECD code:** 50010, 50011 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "OECD10 – OECD13 should only be used during previously agreed-upon testing periods or after a bilateral discussion where both parties agree to testing. This is to help eliminate the possibility that test data could be co-mingled with “live” data."
- **Source:** v2.0: OECD (2019), Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 3.0 – June 2019 (CRS XML Schema v2.0), PDF p. 29; v3.0: OECD (2024), Amended Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 4.0 – October 2024 (CRS XML Schema v3.0), PDF p. 28
- **Check:** The file has both OECD0-OECD3 and OECD10-OECD13 values.
- **Note:** A file mixing OECD0-3 and OECD10-13 is rejected in either environment: with 50010 in production and with 50011 in a test environment.

### `OECD-50012` — The received message is not meant to be received by the indicated jurisdiction

- **OECD code:** 50012 · **severity:** warning · **schema:** 2.0, 3.0 · **context:** exchange only
- **Literal:** "The records contained in the CRS payload file are not meant for the receiving Competent Authority, but should have been provided to another jurisdiction."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 34; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 29
- **Check:** Only with an explicit `--context exchange` and `TransmittingCountry` = `ReceivingCountry`: a message between Competent Authorities addressed to its own sender. Warning.
- **Note:** Only one case is decidable from the file: a message declared as an exchange (--context exchange) whose TransmittingCountry equals its ReceivingCountry. Warning: the code is the receiver's judgement.

### `OECD-60000` — Account Number IBAN

- **OECD code:** 60000 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The Account Number must follow the IBAN structured number format when the Account Number type= OECD601 – IBAN."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** `AcctNumberType="OECD601"`: ISO 13616 structure (2 letters, 2 check digits, 11-30 alphanumerics) and MOD 97-10 → error if it fails. A valid IBAN in print format (spaces or lower case) is a warning: the structure is right, the electronic format is not. Per-country lengths are not checked.

### `OECD-60001` — Account Number ISIN

- **OECD code:** 60001 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The Account Number must follow the ISIN structured number format when the Account Number type= OECD603 – ISIN."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** `AcctNumberType="OECD603"`: ISO 6166 structure (2 letters, 9 alphanumerics, 1 digit) and its Luhn check digit.

### `OECD-60002` — Account Balance

- **OECD code:** 60002 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The account balance entered was less than zero. This amount must be greater than or equal to zero."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** `AccountBalance` < 0.

### `OECD-60003` — Account Balance and Closed account

- **OECD code:** 60003 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The Account Balance must be zero if account was indicated as closed in the account closed attribute."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** `ClosedAccount` is `true`/`1` and `AccountBalance` ≠ 0.

### `OECD-60004` — Person.Name type invalid

- **OECD code:** 60004 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "Name type selected is invalid, i.e. corresponds to the value not used for CRS: OECD201= SMFAliasOrOther"
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** `nameType="OECD201"` on the `Name` of an individual account holder or of a controlling person.

### `OECD-60005` — Controlling Person must be omitted

- **OECD code:** 60005 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "When the Account Holder is an Organisation and the "Account Holder Type" is CRS102 or CRS103, the "Controlling Person " must be omitted. (CRS102= CRS Reportable Person; CRS103= Passive Non-Financial Entity that is a CRS Reportable Person)"
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** Organisation holder with `AcctHolderType` CRS102 or CRS103 and at least one `ControllingPerson`.

### `OECD-60006` — Controlling Person must be provided

- **OECD code:** 60006 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "When the Account Holder is an Organisation and the "Account Holder Type" is CRS101, the "Controlling Person" must be provided. (CRS101= Passive Non-Financial Entity with - one or more controlling person that is a Reportable Person)"
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** Organisation holder with `AcctHolderType` CRS101 and no `ControllingPerson`.

### `OECD-60007` — Reporting Group

- **OECD code:** 60007 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The Reporting Group cannot be repeated."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** More than one `ReportingGroup` in a `CrsBody`.

### `OECD-60008` — Sponsor

- **OECD code:** 60008 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "Sponsor cannot be provided."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** A `Sponsor` in a `ReportingGroup`.

### `OECD-60009` — Intermediary

- **OECD code:** 60009 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "Intermediary cannot be provided"
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** An `Intermediary` in a `ReportingGroup`.

### `OECD-60010` — Pool Report

- **OECD code:** 60010 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "Pool Report cannot be provided."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** A `PoolReport` in a `ReportingGroup`.

### `OECD-60011` — Verify data sorting Person ResCountry Code

- **OECD code:** 60011 · **severity:** error · **schema:** 2.0, 3.0 · **context:** exchange only · **rejection basis**
- **Literal:** "When the Person is a Controlling Person or an Individual Account Holder, at least one of the according ResCountryCodes must match the Message Receiving Country Code"
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** Exchange context only. The individual holder, and each controlling person, must have a `ResCountryCode` equal to `ReceivingCountry`. Applying it to each controlling person is the literal reading, and matches UG v3.0 schema, PDF p. 23: "However, only information of the Reportable Persons of each Reportable Jurisdiction (including information of the Passive NFE and other associated data) should be included in the report."
- **Note:** Applied to each Controlling Person, as written. Consistent with the UG on Controlling Persons: 'However, only information of the Reportable Persons of each Reportable Jurisdiction (including information of the Passive NFE and other associated data) should be included in the report.' (UG v3.0 schema: PDF p. 23; v2.0: PDF p. 24). Not applied to domestic files: [For domestic reporting this element would be the domestic Country Code.] — UG, TransmittingCountry and ReceivingCountry (UG v3.0 schema: PDF p. 10; v2.0: PDF p. 12).

### `OECD-60012` — Verify data sorting Organisation ResCountry Code

- **OECD code:** 60012 · **severity:** error · **schema:** 2.0, 3.0 · **context:** exchange only · **rejection basis**
- **Literal:** "At least one of either the Entity Account Holder ResCountryCode or Controlling Person ResCountryCode must match the Message Receiving Country Code."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** Exchange context only. Organisation holder: the union of its `ResCountryCode` and those of its controlling persons must include `ReceivingCountry`.
- **Note:** Not applied to domestic files: [For domestic reporting this element would be the domestic Country Code.] — UG, TransmittingCountry and ReceivingCountry (UG v3.0 schema: PDF p. 10; v2.0: PDF p. 12).

### `OECD-60013` — Verify data sorting ReportingFI.ResCountry Code

- **OECD code:** 60013 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "ReportingFI.ResCountryCode should always be provided and it must match the Message Sending Country Code"
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** `ReportingFI` has no `ResCountryCode`, or none equals `TransmittingCountry`. Applied in both contexts.

### `OECD-60014` — BirthDate

- **OECD code:** 60014 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "Date of birth should be in a valid range (e.g. not before 1900 and not after the current year)."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 35; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 30
- **Check:** `BirthDate` year before 1900 or after the current year (the year of the run).

### `OECD-60015` — AccountReport

- **OECD code:** 60015 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "AccountReport can only be omitted if ReportingFI is being corrected/deleted or, if there is nil reporting. If the ReportingFI indicates new data or resent, then AccountReport must be provided."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** A `CrsBody` with no `AccountReport`, a `ReportingFI` with OECD0/OECD1 (or OECD10/OECD11) and `MessageTypeIndic` other than CRS703.

### `OECD-60016` — Controlling Person must be omitted (individual holder)

- **OECD code:** 60016 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "When the Account Holder is an individual, the "Controlling Person" must be omitted."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** Individual holder and at least one `ControllingPerson`.

### `OECD-60017` — Specified Electronic Money Product

- **OECD code:** 60017 · **severity:** error · **schema:** 3.0 · **context:** any
- **Literal:** "A Specified Electronic Money Product (AccountNumber is OECD606) must be a Depository Account (AccountType is CRS1101)."
- **Source:** v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** v3.0. `AcctNumberType="OECD606"` and `AccountType` ≠ CRS1101.

### `OECD-60018` — IBAN

- **OECD code:** 60018 · **severity:** error · **schema:** 3.0 · **context:** any
- **Literal:** "An International Bank Account Number (AccountNumber is OECD601) must be a Depository Account (AccountType is CRS1101)."
- **Source:** v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** v3.0. `AcctNumberType="OECD601"` and `AccountType` ≠ CRS1101.

### `OECD-60019` — Equity Interest Type

- **OECD code:** 60019 · **severity:** error · **schema:** 3.0 · **context:** any
- **Literal:** "If the Equity Interest Type is provided, the AccountType must be Debt or Equity Interest in Investment Entity (AccountType is CRS1104)."
- **Source:** v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** v3.0. Any `EquityInterestType` and `AccountType` ≠ CRS1104.

### `OECD-60020` — Cash Value Insurance Contract or Annuity Contract

- **OECD code:** 60020 · **severity:** error · **schema:** 3.0 · **context:** any
- **Literal:** "A Cash Value Insurance Contract or Annuity Contract (AccountType is CRS1103) can only be “Other Any other type of account number e.g. insurance contract” (AccountNumber is OECD605)."
- **Source:** v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** v3.0. `AccountType` CRS1103 and `AcctNumberType` present and ≠ OECD605 (error); attribute absent (it is optional in the XSD): undetermined.

### `OECD-60021` — Payment Type When the Account Type is Depository Account

- **OECD code:** 60021 · **severity:** error · **schema:** 3.0 · **context:** any
- **Literal:** "When the Account Type is a Depository Account (AccountType is CRS1101), the payment type must be Interest (Type is CRS502)."
- **Source:** v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** v3.0. `AccountType` CRS1101 and a `Payment/Type` ≠ CRS502.

### `OECD-60022` — Payment Type When the Account Type is Debt or Equity Interest in Investment Entity

- **OECD code:** 60022 · **severity:** error · **schema:** 3.0 · **context:** any
- **Literal:** "When the Account Type is a Debt or Equity Interest in Investment Entity (AccountType is CRS1104), the payment type must be Gross Proceeds/Redemptions or Other – CRS (Type is CRS503 or CRS504)."
- **Source:** v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** v3.0. `AccountType` CRS1104 and a `Payment/Type` not CRS503/CRS504.

### `OECD-60023` — Payment Type When the Account Type is Cash Value Insurance Contract or Annuity Contract

- **OECD code:** 60023 · **severity:** error · **schema:** 3.0 · **context:** any
- **Literal:** "When the Account Type is a Cash Value Insurance Contract or Annuity Contract (AccountType is CRS1103), the payment type must be Gross Proceeds/Redemptions or Other – CRS (Type is CRS503 or CRS504)."
- **Source:** v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 31
- **Check:** v3.0. `AccountType` CRS1103 and a `Payment/Type` not CRS503/CRS504.

### `OECD-80000` — DocRefID already used

- **OECD code:** 80000 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The DocRefID is already used for another record."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** A `DocRefId` repeated inside the file, or already used by a file earlier in the same run. Across files, a resent Reporting FI (OECD0/OECD10) is exempt: the guide's correction examples resend it with its original `DocRefId`.
- **Note:** Checked inside each file and among the files given in the same run; earlier submissions are known only to the receiving administration.

### `OECD-80001` — DocRefID format

- **OECD code:** 80001 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any (warning in domestic files) · **rejection basis**
- **Literal:** "The structure of the DocRefID is not in the correct format, as set out in the User Guide."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** `DocRefId` must start with `TransmittingCountry` (UG v3.0 schema, PDF p. 29: 'must in all cases start with the country code of the sending jurisdiction'). Error in an exchange; warning in a domestic file, where national formats exist.
- **Note:** The User Guide format: the DocRefID 'must in all cases start with the country code of the sending jurisdiction' (UG v3.0 schema: PDF p. 29; v2.0: PDF p. 30). 'In all cases' covers domestic files too, but there national formats exist (IRAS starts with the year), so in a domestic file it is a warning.

### `OECD-80004` — CorrDocRefId for new data

- **OECD code:** 80004 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The initial element specifies a CorrDocRefId."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** `DocTypeIndic` OECD1/OECD11 with a `CorrDocRefId`.

### `OECD-80005` — Missing CorrDocRefId

- **OECD code:** 80005 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The corrected element does not specify any CorrDocRefId."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** `DocTypeIndic` OECD2/OECD3/OECD12/OECD13 without `CorrDocRefId`.

### `OECD-80006` — DocSpec.CorrMessageRefID

- **OECD code:** 80006 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The CorrMessageRefID is forbidden within the DocSpec_Type."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** `CorrMessageRefId` inside any `DocSpec`.

### `OECD-80007` — MessageSpec.CorrMessageRefID

- **OECD code:** 80007 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The CorrMessageRefID is forbidden within the Message Header."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** `CorrMessageRefId` in `MessageSpec`.

### `OECD-80008` — Resend option

- **OECD code:** 80008 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The Resend option may only be used with respect to the Reporting FI element."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** An `AccountReport` with OECD0/OECD10.

### `OECD-80009` — Delete ReportingFI

- **OECD code:** 80009 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The Reporting FI cannot be deleted without deleting all related Account Reports."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** `ReportingFI` with OECD3/OECD13 and an `AccountReport` of the same body that is not a deletion.
- **Note:** Checked against the Account Reports of the same message; reports sent in earlier messages are not visible from the file.

### `OECD-80010` — Message TypeIndic

- **OECD code:** 80010 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "A message can contain either new records (OECD1) or corrections/deletions (OECD2 and OECD3), but should not contain a mixture of both."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** New records (OECD1/11) together with corrections or deletions (OECD2/3/12/13); or `MessageTypeIndic` CRS701 with corrections/deletions; or CRS702 with new records (UG: 'Messages must contain all new or all corrected/deleted data').
- **Note:** Also checked against MessageTypeIndic, from the UG on that element: 'Messages must contain all new or all corrected/deleted data, or advise that there is no data to report.' and 'CRS702 = The message contains corrections/deletions for previously sent information' (UG v3.0 schema: PDF p. 11; v2.0: PDF p. 13). So CRS701 with OECD2/OECD3 and CRS702 with OECD1 are reported here too.

### `OECD-80011` — CorrDocRefID twice in same message

- **OECD code:** 80011 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The same DocRefID cannot be corrected or deleted twice in the same message."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 36; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** The same `CorrDocRefId` twice in the message.

### `OECD-80015` — CrsBody

- **OECD code:** 80015 · **severity:** error · **schema:** 2.0, 3.0 · **context:** any · **rejection basis**
- **Literal:** "The CrsBody can be omitted only when the MessageTypeIndic is CRS703 (Nil reporting) and the SendingCompanyIN is omitted, i.e. only in the case of Nil reporting between Competent Authorities. In all other case, the CrsBody must be provided."
- **Source:** v2.0: OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations, Version 2.0 – June 2019, PDF p. 37; v3.0: OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en, PDF p. 32
- **Check:** No `CrsBody` while `MessageTypeIndic` ≠ CRS703 or `SendingCompanyIN` is present.

### `UG-VERSION` — Root version attribute

- **OECD code:** — (no Status Message code) · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "For the CRS schema version 2.0, the version attribute must be set to the value “2.0”. / For the CRS schema version 3.0, the version attribute must be set to the value “3.0”."
- **Source:** v2.0: OECD (2019), Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 3.0 – June 2019 (CRS XML Schema v2.0), PDF p. 28; v3.0: OECD (2024), Amended Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 4.0 – October 2024 (CRS XML Schema v3.0), PDF p. 27
- **Check:** Root `version` attribute ≠ the version of the root namespace.
- **Note:** No Status Message code: the XSD types the attribute as a 1-10 character string, so a wrong value passes schema validation.

### `UG-TIMESTAMP` — Timestamp fractions of seconds

- **OECD code:** — (no Status Message code) · **severity:** warning · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "Fractions of seconds may be used (in such a case the milliseconds will be provided in 3 digits, see “.nnn” in the format above)."
- **Source:** v2.0: OECD (2019), Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 3.0 – June 2019 (CRS XML Schema v2.0), PDF p. 14; v3.0: OECD (2024), Amended Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 4.0 – October 2024 (CRS XML Schema v3.0), PDF p. 12
- **Check:** `Timestamp` with fractions of seconds that are not exactly 3 digits. Warning.

### `CTX-DOMESTIC` — Treated as domestic reporting

- **OECD code:** — (no Status Message code) · **severity:** warning · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "[For domestic reporting this element would be the domestic Country Code.]"
- **Source:** v2.0: OECD (2019), Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 3.0 – June 2019 (CRS XML Schema v2.0), PDF p. 12; v3.0: OECD (2024), Amended Common Reporting Standard XML Schema: User Guide for Tax Administrations, Version 4.0 – October 2024 (CRS XML Schema v3.0), PDF p. 10
- **Check:** Context detected as domestic because `TransmittingCountry` = `ReceivingCountry`. Reported as a warning in text, JSON and SARIF so that a mislabelled exchange cannot pass silently; an explicit `--context domestic` does not emit it.
- **Note:** Emitted only when the context was detected (TransmittingCountry equals ReceivingCountry), never with an explicit --context domestic: an exchange mislabelled with the same country twice must not pass silently.

### `FMT-001` — Not a CRS XML document

- **OECD code:** — (no Status Message code) · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The root element must be CRS_OECD in the namespace urn:oecd:ties:crs:v2 or urn:oecd:ties:crs:v3."
- **Source:** crs-lint (tool rule, not an OECD rule)
- **Check:** Root is not `CRS_OECD` in a CRS namespace (the AEAT modelo 289 envelope is recognised and named). Exit 2.

### `FMT-002` — Document refused

- **OECD code:** — (no Status Message code) · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "crs-lint does not process DTDs or entity declarations: a CRS message never needs them, and accepting them lets a ten-line XML exhaust the memory of the process."
- **Source:** crs-lint (tool rule, not an OECD rule)
- **Check:** A `<!DOCTYPE` in the first 8 KiB, read as latin-1, UTF-16LE and UTF-16BE. Exit 2.

### `FMT-003` — File could not be read

- **OECD code:** — (no Status Message code) · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "The file does not exist, is not a regular file or could not be read."
- **Source:** crs-lint (tool rule, not an OECD rule)
- **Check:** Missing, not a regular file, or unreadable. The other files are still checked. Exit 2.

### `TOOL-001` — Resource limit of crs-lint

- **OECD code:** — (no Status Message code) · **severity:** error · **schema:** 2.0, 3.0 · **context:** any
- **Literal:** "crs-lint parses without libxml2's XML_PARSE_HUGE: a single text node over 10 MB or a nesting deeper than 256 levels stops the parse. This is a limit of the tool, not an OECD error."
- **Source:** crs-lint (tool rule, not an OECD rule)
- **Check:** libxml2 stopped on a resource limit (`XML_ERR_RESOURCE_LIMIT` or a message asking for `XML_PARSE_HUGE`). Exit 2: the file was not checked, which is not the same as an invalid file.

## Out of scope in v0.1, and why

These codes exist in the Status Message guide but cannot be decided from the file (or
are not about its content). crs-lint never reports them, and says so here rather than
pretending a clean run covers them.

| Code | Why it is not checked |
|---|---|

| 50001 | Failed Download — transport (CTS), not the XML content. |
| 50002 | Failed Decryption — transport (CTS), not the XML content. |
| 50003 | Failed Decompression — transport (CTS), not the XML content. |
| 50004 | Failed Signature Check — transport (CTS), not the XML content. |
| 50005 | Failed Threat Scan — needs the receiver's scanner. |
| 50006 | Failed Virus Scan — needs the receiver's scanner. |
| 50009 | MessageRefID already used — earlier files are known only to the receiver (checked among the files of the same run). |
| 50012 | Message not meant for the receiving jurisdiction — needs the receiver's judgement of where each record belongs (only the case TransmittingCountry = ReceivingCountry in an exchange is checked). |
| 50013 | Incorrect AES key size — transport (CTS), not the XML content. |
| 80000 | DocRefID already used — earlier records are known only to the receiver (checked inside each file and among the files of the same run). |
| 80002 | CorrDocRefId unknown — needs the receiver's record of earlier submissions. |
| 80003 | CorrDocRefId no longer valid — needs the receiver's record of earlier corrections. |
| 80012 | Two Reporting Periods — a message has a single ReportingPeriod; the period of each record is not in the file. |
| 80013 | Resend option, unknown DocRefID — needs the receiver's record of earlier submissions. |
| 80014 | Resend option, DocRefID no longer valid — needs the receiver's record of earlier corrections. |
| 90000-90002 | TIN structure, algorithm and semantic — 'reserved for future use' in the Status Message guide, and national: each jurisdiction has its own TIN rules. |
| 98000-98999 | Domestic error codes — defined by each jurisdiction. |
| 99999 | Custom error — agreed bilaterally or chosen by the receiver. |

## Counted

The SM3 tables define 57 codes: 13 file errors (50001-50013), 24 record errors on CRS
data (60000-60023), 16 on the correction process (80000-80015), 3 reserved for future
use (90000-90002) and the custom 99999 (98000-98999 are left to each country).

- **Implemented: 41 codes** — 6 file (50007, 50008, 50009, 50010, 50011, 50012), all 24
  record codes 60000-60023, and 11 correction codes (80000, 80001, 80004, 80005, 80006,
  80007, 80008, 80009, 80010, 80011, 80015). Three are partial by nature: 50009 and
  80000 are checked inside the file and across the files of one run, not against
  earlier submissions; 50012 only in the one case the file can show.
- **Out of scope: 16 codes** — 7 file codes about transport or the receiver's scanners
  (50001-50006, 50013), 5 that need the receiver's records (80002, 80003, 80012, 80013,
  80014), 3 reserved for future use (90000-90002) and the custom 99999.
- Plus two User Guide rules without a code (`UG-VERSION`, `UG-TIMESTAMP`), the context
  notice `CTX-DOMESTIC`, and four tool rules (`FMT-001`…`FMT-003`, `TOOL-001`).
