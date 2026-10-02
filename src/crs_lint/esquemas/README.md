# Official CRS XML schemas

Literal copies of the XSD packages published by the **Inland Revenue Authority of
Singapore (IRAS)** on its *CRS Filing* page, **unmodified**. IRAS redistributes the OECD
schemas as is: they carry the OECD target namespaces (`urn:oecd:ties:crs:v2`,
`urn:oecd:ties:crs:v3`) and nothing Singapore-specific. The same files are the ones used
by `phive-rules-crs`.

| Version | Package | SHA-256 of the zip |
|---|---|---|
| 2.0 | https://www.iras.gov.sg/docs/default-source/uploadedfiles/zip/crs-schema-v2-0.zip | `d770d7c426759691c57c89c41d808790f0f3b841e9cb61d514334c55ccb0a524` |
| 3.0 | https://www.iras.gov.sg/docs/default-source/uploadedfiles/zip/crs-xml-schema-3-0.zip | `a80cce2b2d0c6fe009de3a37edf3a2fbb0b4e0e0baa9f705bb6ea68e6538977e` |

Downloaded on **2026-10-02**. © OECD; subject to the OECD Terms and Conditions
(https://www.oecd.org/termsandconditions), not to crs-lint's Apache licence (see `NOTICE`). The v2.0 set is byte-for-byte what the Spanish AEAT ships
inside its modelo 289 package (`289_XSD_2.0_WSDL_2.0.1.zip`, compared ignoring
whitespace).

## Why one directory per version

Both packages contain a file called `CommonTypesFatcaCrs_v2.0.xsd`, and they are **not
the same file**: the v3.0 one adds the account number type `OECD606` (Specified
Electronic Money Product). Validating a v3.0 message with the v2.0 copy would reject
every e-money account.

## Why they are versioned and not downloaded on the fly

A schema fetched at run time turns any change by a third party into a surprise CI
failure, and the tool promises never to go to the network. Versioned, updating them is
an explicit change visible in a diff. `tests/test_proyecto.py` checks every file
against this table.

## File checksums

| SHA-256 | File |
|---|---|
| `a56b1b123d1bf560e3715def76a73a6f5e93329b6094510487380be95b4b6eff` | `2.0/CommonTypesFatcaCrs_v2.0.xsd` |
| `727a446aaad390de527b956ada05a1198943a5e2dc02c022c890aba3bd321bd1` | `2.0/CrsXML_v2.0.xsd` |
| `f842eca4f038cf3ee574f0820197c1448de69bc8200f926bb9d5c809417ebb97` | `2.0/FatcaTypes_v1.2.xsd` |
| `aeed6deaf56cbf93415e8e17387f5b400add48ad573c462fb546cdd64f721281` | `2.0/isocrstypes_v1.1.xsd` |
| `80d2eb328f6a68b8da15a27f06366cea088b321115d57ceb56dcc2106096bf4f` | `2.0/oecdcrstypes_v5.0.xsd` |
| `882d6cde408e915fc52b6ace3549a5cf4ddec161024f30f89b3ba400acbe6a80` | `3.0/CommonTypesFatcaCrs_v2.0.xsd` |
| `aa25e255e85f15cf46b889fda3c2df5c290456c8686cac2896b917a9e3bcf925` | `3.0/CrsXML_v3.0.xsd` |
| `b099b2cdeccc3d5cc0e22f13f312b313e077a59f0b6432d1ce9e7e189c411c72` | `3.0/FatcaTypes_v1.2.xsd` |
| `aeed6deaf56cbf93415e8e17387f5b400add48ad573c462fb546cdd64f721281` | `3.0/isocrstypes_v1.1.xsd` |
| `11db640c16a7202ca6274d1c6bf6f9134e9f4863af280927c15e9ae2baf47dac` | `3.0/oecdcrstypes_v5.0.xsd` |
