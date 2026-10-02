"""El catálogo de reglas: código oficial de la OCDE, frase literal y fuente con página.

**Ninguna regla sin texto de la OCDE detrás.** Cada entrada cita literalmente la
*Validation description* de la CRS Status Message User Guide (los códigos 5xxxx, 6xxxx
y 8xxxx que la administración receptora devuelve), o, en las dos reglas `UG-*`, la frase
de la CRS XML Schema User Guide que dice «must»/«will». Lo que la guía no escribe no es
regla, y lo que exige datos de la administración (envíos anteriores) no está aquí: está
listado en `FUERA_DE_ALCANCE` con su motivo.

Las páginas son las del PDF (la que muestra el visor), no las impresas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from crs_lint.hallazgos import Hallazgo, Severidad

SM3 = (
    "OECD (2025), Common Reporting Standard Status Message XML Schema: User Guide for Tax "
    "Administrations (Version 3.0), https://doi.org/10.1787/6c08db84-en"
)
SM2 = (
    "OECD (2019), Common Reporting Standard Status Message XML Schema: User Guide for Tax "
    "Administrations, Version 2.0 – June 2019"
)
UG3 = (
    "OECD (2024), Amended Common Reporting Standard XML Schema: User Guide for Tax "
    "Administrations, Version 4.0 – October 2024 (CRS XML Schema v3.0)"
)
UG2 = (
    "OECD (2019), Common Reporting Standard XML Schema: User Guide for Tax Administrations, "
    "Version 3.0 – June 2019 (CRS XML Schema v2.0)"
)

NACIONAL = (
    "[For domestic reporting this element would be the domestic Country Code.] — UG, "
    "TransmittingCountry and ReceivingCountry (UG v3.0 schema: PDF p. 10; v2.0: PDF p. 12)"
)

AMBAS = ("2.0", "3.0")
SOLO_V3 = ("3.0",)


@dataclass(frozen=True)
class Regla:
    id: str
    codigos: tuple[str, ...]
    severidad: Severidad
    titulo: str
    literal: str
    paginas: dict[str, str]
    """Versión de esquema → «documento, p. N» donde está la frase."""
    versiones: tuple[str, ...] = AMBAS
    solo_intercambio: bool = False
    """Sólo para mensajes entre autoridades competentes (TransmittingCountry ≠
    ReceivingCountry). En la declaración nacional el formato lo fija cada país."""
    base_de_rechazo: bool = False
    """La Status Message User Guide la incluye en el «common approach»: puede motivar el
    rechazo del fichero entero, no sólo del registro."""
    notas: str = field(default="")

    def cita(self, version: str) -> str:
        donde = self.paginas.get(version) or next(iter(self.paginas.values()))
        return f'"{self.literal}" — {donde}'

    def hallazgo(
        self,
        detalle: str,
        *,
        version: str,
        fichero: str = "",
        linea: int = 0,
        severidad: Severidad | None = None,
    ) -> Hallazgo:
        return Hallazgo(
            regla=self.id,
            severidad=severidad or self.severidad,
            titulo=self.titulo,
            detalle=detalle,
            codigos=self.codigos,
            cita=self.cita(version),
            fichero=fichero,
            linea_xml=linea,
        )


def _sm(p3: int | None, p2: int | None) -> dict[str, str]:
    paginas: dict[str, str] = {}
    if p2 is not None:
        paginas["2.0"] = f"{SM2}, PDF p. {p2}"
    if p3 is not None:
        paginas["3.0"] = f"{SM3}, PDF p. {p3}"
    return paginas


def _ug(p3: int, p2: int) -> dict[str, str]:
    return {"2.0": f"{UG2}, PDF p. {p2}", "3.0": f"{UG3}, PDF p. {p3}"}


E, W = Severidad.ERROR, Severidad.AVISO

_REGLAS = [
    # --- Errores de fichero (50 000 – 59 999) ------------------------------------------
    Regla(
        "OECD-50007", ("50007",), E, "Failed Schema Validation",
        "The referenced file failed validation against the CRS XML Schema.",
        _sm(27, 32),
    ),
    Regla(
        "OECD-50008", ("50008",), E, "Invalid MessageRefID format",
        "The structure of the MessageRefID is not in the correct format, as set out in the "
        "CRS User Guide. The CRS User guide indicates that the MessageRefID can contain "
        "whatever information the sender uses to allow identification of the particular "
        "report but must start with the sending country code as the first element for "
        "Competent Authority to Competent Authority transmission, then the year to which the "
        "data relates, then the receiving country code before a unique identifier (e.g. "
        "FR2013CA123456789).",
        _sm(27, 32), solo_intercambio=True,
        notas="Not applied to domestic files, where the OECD itself makes both countries the "
        "domestic one: " + NACIONAL + ". The national format of MessageRefID is set by each "
        "administration.",
    ),
    Regla(
        "OECD-50009", ("50009",), E, "MessageRefID has already been used",
        "The referenced file has a duplicate MessageRefID value that was received on a "
        "previous file.",
        _sm(28, 33),
        notas="Only checked among the files given in the same run; earlier submissions are "
        "known only to the receiving administration.",
    ),
    Regla(
        "OECD-50010", ("50010",), W, "File Contains Test Data for Production Environment",
        "The referenced file contains one or more records with a DocTypeIndic value in the "
        "range OECD10-OECD13, indicating test data. As a result, the receiving Competent "
        "Authority cannot accept this file as a valid CRS file submission.",
        _sm(28, 33),
        notas="Warning, not error: whether the file goes to production or to a test "
        "environment is not in the file.",
    ),
    Regla(
        "OECD-50010-50011", ("50010", "50011"), E, "Test and live records mixed",
        "OECD10 – OECD13 should only be used during previously agreed-upon testing periods "
        "or after a bilateral discussion where both parties agree to testing. This is to "
        "help eliminate the possibility that test data could be co-mingled with “live” data.",
        _ug(28, 29),
        notas="A file mixing OECD0-3 and OECD10-13 is rejected in either environment: with "
        "50010 in production and with 50011 in a test environment.",
    ),
    Regla(
        "OECD-50012", ("50012",), W,
        "The received message is not meant to be received by the indicated jurisdiction",
        "The records contained in the CRS payload file are not meant for the receiving "
        "Competent Authority, but should have been provided to another jurisdiction.",
        _sm(29, 34), solo_intercambio=True,
        notas="Only one case is decidable from the file: a message declared as an exchange "
        "(--context exchange) whose TransmittingCountry equals its ReceivingCountry. Warning: "
        "the code is the receiver's judgement.",
    ),
    # --- Registro: datos CRS (60 000 – 69 999) ------------------------------------------
    Regla(
        "OECD-60000", ("60000",), E, "Account Number IBAN",
        "The Account Number must follow the IBAN structured number format when the Account "
        "Number type= OECD601 – IBAN.",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60001", ("60001",), E, "Account Number ISIN",
        "The Account Number must follow the ISIN structured number format when the Account "
        "Number type= OECD603 – ISIN.",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60002", ("60002",), E, "Account Balance",
        "The account balance entered was less than zero. This amount must be greater than or "
        "equal to zero.",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60003", ("60003",), E, "Account Balance and Closed account",
        "The Account Balance must be zero if account was indicated as closed in the account "
        "closed attribute.",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60004", ("60004",), E, "Person.Name type invalid",
        "Name type selected is invalid, i.e. corresponds to the value not used for CRS: "
        "OECD201= SMFAliasOrOther",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60005", ("60005",), E, "Controlling Person must be omitted",
        'When the Account Holder is an Organisation and the "Account Holder Type" is CRS102 '
        'or CRS103, the "Controlling Person " must be omitted. (CRS102= CRS Reportable '
        "Person; CRS103= Passive Non-Financial Entity that is a CRS Reportable Person)",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60006", ("60006",), E, "Controlling Person must be provided",
        'When the Account Holder is an Organisation and the "Account Holder Type" is CRS101, '
        'the "Controlling Person" must be provided. (CRS101= Passive Non-Financial Entity '
        "with - one or more controlling person that is a Reportable Person)",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60007", ("60007",), E, "Reporting Group",
        "The Reporting Group cannot be repeated.", _sm(30, 35), base_de_rechazo=True,
    ),
    Regla(
        "OECD-60008", ("60008",), E, "Sponsor",
        "Sponsor cannot be provided.", _sm(30, 35), base_de_rechazo=True,
    ),
    Regla(
        "OECD-60009", ("60009",), E, "Intermediary",
        "Intermediary cannot be provided", _sm(30, 35), base_de_rechazo=True,
    ),
    Regla(
        "OECD-60010", ("60010",), E, "Pool Report",
        "Pool Report cannot be provided.", _sm(30, 35), base_de_rechazo=True,
    ),
    Regla(
        "OECD-60011", ("60011",), E, "Verify data sorting Person ResCountry Code",
        "When the Person is a Controlling Person or an Individual Account Holder, at least "
        "one of the according ResCountryCodes must match the Message Receiving Country Code",
        _sm(30, 35), solo_intercambio=True, base_de_rechazo=True,
        notas="Applied to each Controlling Person, as written. Consistent with the UG on "
        "Controlling Persons: 'However, only information of the Reportable Persons of each "
        "Reportable Jurisdiction (including information of the Passive NFE and other "
        "associated data) should be included in the report.' (UG v3.0 schema: PDF p. 23; "
        "v2.0: PDF p. 24). Not applied to domestic files: " + NACIONAL + ".",
    ),
    Regla(
        "OECD-60012", ("60012",), E, "Verify data sorting Organisation ResCountry Code",
        "At least one of either the Entity Account Holder ResCountryCode or Controlling "
        "Person ResCountryCode must match the Message Receiving Country Code.",
        _sm(30, 35), solo_intercambio=True, base_de_rechazo=True,
        notas="Not applied to domestic files: " + NACIONAL + ".",
    ),
    Regla(
        "OECD-60013", ("60013",), E, "Verify data sorting ReportingFI.ResCountry Code",
        "ReportingFI.ResCountryCode should always be provided and it must match the Message "
        "Sending Country Code",
        _sm(30, 35),
    ),
    Regla(
        "OECD-60014", ("60014",), E, "BirthDate",
        "Date of birth should be in a valid range (e.g. not before 1900 and not after the "
        "current year).",
        _sm(30, 35), base_de_rechazo=True,
    ),
    Regla(
        "OECD-60015", ("60015",), E, "AccountReport",
        "AccountReport can only be omitted if ReportingFI is being corrected/deleted or, if "
        "there is nil reporting. If the ReportingFI indicates new data or resent, then "
        "AccountReport must be provided.",
        _sm(31, 36), base_de_rechazo=True,
    ),
    Regla(
        "OECD-60016", ("60016",), E, "Controlling Person must be omitted (individual holder)",
        'When the Account Holder is an individual, the "Controlling Person" must be omitted.',
        _sm(31, 36),
    ),
    Regla(
        "OECD-60017", ("60017",), E, "Specified Electronic Money Product",
        "A Specified Electronic Money Product (AccountNumber is OECD606) must be a Depository "
        "Account (AccountType is CRS1101).",
        _sm(31, None), versiones=SOLO_V3,
    ),
    Regla(
        "OECD-60018", ("60018",), E, "IBAN",
        "An International Bank Account Number (AccountNumber is OECD601) must be a "
        "Depository Account (AccountType is CRS1101).",
        _sm(31, None), versiones=SOLO_V3,
    ),
    Regla(
        "OECD-60019", ("60019",), E, "Equity Interest Type",
        "If the Equity Interest Type is provided, the AccountType must be Debt or Equity "
        "Interest in Investment Entity (AccountType is CRS1104).",
        _sm(31, None), versiones=SOLO_V3,
    ),
    Regla(
        "OECD-60020", ("60020",), E, "Cash Value Insurance Contract or Annuity Contract",
        "A Cash Value Insurance Contract or Annuity Contract (AccountType is CRS1103) can "
        "only be “Other Any other type of account number e.g. insurance contract” "
        "(AccountNumber is OECD605).",
        _sm(31, None), versiones=SOLO_V3,
    ),
    Regla(
        "OECD-60021", ("60021",), E, "Payment Type When the Account Type is Depository Account",
        "When the Account Type is a Depository Account (AccountType is CRS1101), the payment "
        "type must be Interest (Type is CRS502).",
        _sm(31, None), versiones=SOLO_V3,
    ),
    Regla(
        "OECD-60022", ("60022",), E,
        "Payment Type When the Account Type is Debt or Equity Interest in Investment Entity",
        "When the Account Type is a Debt or Equity Interest in Investment Entity (AccountType "
        "is CRS1104), the payment type must be Gross Proceeds/Redemptions or Other – CRS "
        "(Type is CRS503 or CRS504).",
        _sm(31, None), versiones=SOLO_V3,
    ),
    Regla(
        "OECD-60023", ("60023",), E,
        "Payment Type When the Account Type is Cash Value Insurance Contract or Annuity "
        "Contract",
        "When the Account Type is a Cash Value Insurance Contract or Annuity Contract "
        "(AccountType is CRS1103), the payment type must be Gross Proceeds/Redemptions or "
        "Other – CRS (Type is CRS503 or CRS504).",
        _sm(31, None), versiones=SOLO_V3,
    ),
    # --- Registro: proceso de corrección (80 000 – 89 999) ------------------------------
    Regla(
        "OECD-80000", ("80000",), E, "DocRefID already used",
        "The DocRefID is already used for another record.", _sm(32, 36),
        base_de_rechazo=True,
        notas="Checked inside each file and among the files given in the same run; earlier "
        "submissions are known only to the receiving administration.",
    ),
    Regla(
        "OECD-80001", ("80001",), E, "DocRefID format",
        "The structure of the DocRefID is not in the correct format, as set out in the User "
        "Guide.",
        _sm(32, 36), base_de_rechazo=True,
        notas="The User Guide format: the DocRefID 'must in all cases start with the country "
        "code of the sending jurisdiction' (UG v3.0 schema: PDF p. 29; v2.0: PDF p. 30). "
        "'In all cases' covers domestic files too, but there national formats exist (IRAS "
        "starts with the year), so in a domestic file it is a warning.",
    ),
    Regla(
        "OECD-80004", ("80004",), E, "CorrDocRefId for new data",
        "The initial element specifies a CorrDocRefId.", _sm(32, 36), base_de_rechazo=True,
    ),
    Regla(
        "OECD-80005", ("80005",), E, "Missing CorrDocRefId",
        "The corrected element does not specify any CorrDocRefId.", _sm(32, 36),
        base_de_rechazo=True,
    ),
    Regla(
        "OECD-80006", ("80006",), E, "DocSpec.CorrMessageRefID",
        "The CorrMessageRefID is forbidden within the DocSpec_Type.", _sm(32, 36),
    ),
    Regla(
        "OECD-80007", ("80007",), E, "MessageSpec.CorrMessageRefID",
        "The CorrMessageRefID is forbidden within the Message Header.", _sm(32, 36),
    ),
    Regla(
        "OECD-80008", ("80008",), E, "Resend option",
        "The Resend option may only be used with respect to the Reporting FI element.",
        _sm(32, 36), base_de_rechazo=True,
    ),
    Regla(
        "OECD-80009", ("80009",), E, "Delete ReportingFI",
        "The Reporting FI cannot be deleted without deleting all related Account Reports.",
        _sm(32, 36), base_de_rechazo=True,
        notas="Checked against the Account Reports of the same message; reports sent in "
        "earlier messages are not visible from the file.",
    ),
    Regla(
        "OECD-80010", ("80010",), E, "Message TypeIndic",
        "A message can contain either new records (OECD1) or corrections/deletions (OECD2 "
        "and OECD3), but should not contain a mixture of both.",
        _sm(32, 36), base_de_rechazo=True,
        notas="Also checked against MessageTypeIndic, from the UG on that element: 'Messages "
        "must contain all new or all corrected/deleted data, or advise that there is no data "
        "to report.' and 'CRS702 = The message contains corrections/deletions for previously "
        "sent information' (UG v3.0 schema: PDF p. 11; v2.0: PDF p. 13). So CRS701 with "
        "OECD2/OECD3 and CRS702 with OECD1 are reported here too.",
    ),
    Regla(
        "OECD-80011", ("80011",), E, "CorrDocRefID twice in same message",
        "The same DocRefID cannot be corrected or deleted twice in the same message.",
        _sm(32, 36), base_de_rechazo=True,
    ),
    Regla(
        "OECD-80015", ("80015",), E, "CrsBody",
        "The CrsBody can be omitted only when the MessageTypeIndic is CRS703 (Nil reporting) "
        "and the SendingCompanyIN is omitted, i.e. only in the case of Nil reporting between "
        "Competent Authorities. In all other case, the CrsBody must be provided.",
        _sm(32, 37), base_de_rechazo=True,
    ),
    # --- User Guide, sin código en la Status Message -------------------------------------
    Regla(
        "UG-VERSION", (), E, "Root version attribute",
        "For the CRS schema version 2.0, the version attribute must be set to the value "
        "“2.0”. / For the CRS schema version 3.0, the version attribute must be set to the "
        "value “3.0”.",
        _ug(27, 28),
        notas="No Status Message code: the XSD types the attribute as a 1-10 character "
        "string, so a wrong value passes schema validation.",
    ),
    Regla(
        "UG-TIMESTAMP", (), W, "Timestamp fractions of seconds",
        "Fractions of seconds may be used (in such a case the milliseconds will be provided "
        "in 3 digits, see “.nnn” in the format above).",
        _ug(12, 14),
    ),
    Regla(
        "CTX-DOMESTIC", (), W, "Treated as domestic reporting",
        "[For domestic reporting this element would be the domestic Country Code.]",
        _ug(10, 12),
        notas="Emitted only when the context was detected (TransmittingCountry equals "
        "ReceivingCountry), never with an explicit --context domestic: an exchange "
        "mislabelled with the same country twice must not pass silently.",
    ),
    # --- La herramienta ------------------------------------------------------------------
    Regla(
        "FMT-001", (), E, "Not a CRS XML document",
        "The root element must be CRS_OECD in the namespace urn:oecd:ties:crs:v2 or "
        "urn:oecd:ties:crs:v3.",
        {"2.0": "crs-lint", "3.0": "crs-lint"},
    ),
    Regla(
        "FMT-002", (), E, "Document refused",
        "crs-lint does not process DTDs or entity declarations: a CRS message never needs "
        "them, and accepting them lets a ten-line XML exhaust the memory of the process.",
        {"2.0": "crs-lint", "3.0": "crs-lint"},
    ),
    Regla(
        "FMT-003", (), E, "File could not be read",
        "The file does not exist, is not a regular file or could not be read.",
        {"2.0": "crs-lint", "3.0": "crs-lint"},
    ),
]

_REGLAS.append(
    Regla(
        "TOOL-001", (), E, "Resource limit of crs-lint",
        "crs-lint parses without libxml2's XML_PARSE_HUGE: a single text node over 10 MB or "
        "a nesting deeper than 256 levels stops the parse. This is a limit of the tool, not "
        "an OECD error.",
        {"2.0": "crs-lint", "3.0": "crs-lint"},
    )
)

REGLAS: dict[str, Regla] = {r.id: r for r in _REGLAS}

FUERA_DE_ALCANCE: dict[str, str] = {
    "50001": "Failed Download — transport (CTS), not the XML content.",
    "50002": "Failed Decryption — transport (CTS), not the XML content.",
    "50003": "Failed Decompression — transport (CTS), not the XML content.",
    "50004": "Failed Signature Check — transport (CTS), not the XML content.",
    "50005": "Failed Threat Scan — needs the receiver's scanner.",
    "50006": "Failed Virus Scan — needs the receiver's scanner.",
    "50009": "MessageRefID already used — earlier files are known only to the receiver "
    "(checked among the files of the same run).",
    "50012": "Message not meant for the receiving jurisdiction — needs the receiver's "
    "judgement of where each record belongs (only the case TransmittingCountry = "
    "ReceivingCountry in an exchange is checked).",
    "50013": "Incorrect AES key size — transport (CTS), not the XML content.",
    "80000": "DocRefID already used — earlier records are known only to the receiver "
    "(checked inside each file and among the files of the same run).",
    "80002": "CorrDocRefId unknown — needs the receiver's record of earlier submissions.",
    "80003": "CorrDocRefId no longer valid — needs the receiver's record of earlier "
    "corrections.",
    "80012": "Two Reporting Periods — a message has a single ReportingPeriod; the period of "
    "each record is not in the file.",
    "80013": "Resend option, unknown DocRefID — needs the receiver's record of earlier "
    "submissions.",
    "80014": "Resend option, DocRefID no longer valid — needs the receiver's record of "
    "earlier corrections.",
    "90000-90002": "TIN structure, algorithm and semantic — 'reserved for future use' in the "
    "Status Message guide, and national: each jurisdiction has its own TIN rules.",
    "98000-98999": "Domestic error codes — defined by each jurisdiction.",
    "99999": "Custom error — agreed bilaterally or chosen by the receiver.",
}
