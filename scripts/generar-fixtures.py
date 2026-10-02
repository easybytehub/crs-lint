"""Genera los ficheros de prueba de tests/fixtures: todos SINTÉTICOS.

Ningún dato real: la entidad es «Example Bank», los titulares son los nombres de
ejemplo que usan los formularios alemanes (Erika y Max Mustermann), los NIF son cadenas
de relleno y el IBAN y el ISIN son los ejemplos públicos de sus estándares
(DE89 3704 0044 0532 0130 00 y US0378331005), elegidos porque su dígito de control es
correcto.

Uno válido por versión de esquema (más uno de declaración nacional) y uno por regla que
falla. Cada fichero se escribe junto con lo que crs-lint debe decir de él en
`esperados.json`: el test compara exactamente ese conjunto de reglas, así que una regla
que se dispara de más o de menos rompe la suite.

Uso: python scripts/generar-fixtures.py   (idempotente; un test comprueba que lo
versionado coincide con lo que genera este script).
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path

from lxml import etree

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "tests" / "fixtures"

STF = "urn:oecd:ties:crsstf:v5"
CFC = "urn:oecd:ties:commontypesfatcacrs:v2"
FTC = "urn:oecd:ties:fatca:v1"
NS = {"2.0": "urn:oecd:ties:crs:v2", "3.0": "urn:oecd:ties:crs:v3"}


def _persona(v: str, nombre: str, apellido: str, pais: str, nacimiento: str) -> str:
    return f"""
        <crs:ResCountryCode>{pais}</crs:ResCountryCode>
        <crs:TIN issuedBy="{pais}">00000000000</crs:TIN>
        <crs:Name><crs:FirstName>{nombre}</crs:FirstName><crs:LastName>{apellido}</crs:LastName></crs:Name>
        <crs:Address><cfc:CountryCode>{pais}</cfc:CountryCode><cfc:AddressFree>Example street 1, Example city</cfc:AddressFree></crs:Address>
        <crs:BirthInfo><crs:BirthDate>{nacimiento}</crs:BirthDate></crs:BirthInfo>"""


def _docspec(tipo: str, ref: str) -> str:
    return (
        f"<crs:DocSpec><stf:DocTypeIndic>{tipo}</stf:DocTypeIndic>"
        f"<stf:DocRefId>{ref}</stf:DocRefId></crs:DocSpec>"
    )


def _cuenta(
    v: str, ref: str, numero: str, tipo_num: str, titular: str, saldo: str, pago: str,
    tipo_cuenta: str, controlador: str = "",
) -> str:
    v3 = v == "3.0"
    autocert = "<crs:SelfCert>CRS901</crs:SelfCert>" if v3 else ""
    extra = (
        f"<crs:DDProcedure>CRS1201</crs:DDProcedure><crs:AccountType>{tipo_cuenta}</crs:AccountType>"
        if v3 else ""
    )
    return f"""
      <crs:AccountReport>
        {_docspec("OECD1", ref)}
        <crs:AccountNumber AcctNumberType="{tipo_num}">{numero}</crs:AccountNumber>
        <crs:AccountHolder>{autocert}{titular}</crs:AccountHolder>{controlador}
        <crs:AccountBalance currCode="EUR">{saldo}</crs:AccountBalance>
        <crs:Payment><crs:Type>{pago}</crs:Type><crs:PaymentAmnt currCode="EUR">12.50</crs:PaymentAmnt></crs:Payment>
        {extra}
      </crs:AccountReport>"""


def mensaje(v: str, *, nacional: bool = False) -> str:
    """Un mensaje CRS_OECD válido: intercambio ES → DE, o declaración nacional ES → ES."""
    anio = "2025" if v == "2.0" else "2026"
    rc = "ES" if nacional else "DE"
    mri = f"{anio}A00000000{anio}0315001" if nacional else f"ES{anio}DE0000000001"
    # El DocRefId empieza por el país emisor también en lo nacional: la guía dice «in all
    # cases» (80001). El MessageRefId sí lleva formato nacional.
    pref = "ES"
    v3 = v == "3.0"
    individuo = f"<crs:Individual>{_persona(v, 'Erika', 'Mustermann', 'DE', '1980-05-17')}</crs:Individual>"
    cp_autocert = "<crs:SelfCert>CRS1001</crs:SelfCert>" if v3 else ""
    controlador = f"""
        <crs:ControllingPerson>
          <crs:Individual>{_persona(v, 'Max', 'Mustermann', 'DE', '1975-01-02')}</crs:Individual>
          <crs:CtrlgPersonType>CRS801</crs:CtrlgPersonType>{cp_autocert}
        </crs:ControllingPerson>"""
    organizacion = """<crs:Organisation>
          <crs:ResCountryCode>DE</crs:ResCountryCode>
          <crs:Name>Beispiel Holding GmbH</crs:Name>
          <crs:Address><cfc:CountryCode>DE</cfc:CountryCode><cfc:AddressFree>Example street 2, Example city</cfc:AddressFree></crs:Address>
        </crs:Organisation><crs:AcctHolderType>CRS101</crs:AcctHolderType>"""
    cuentas = [
        _cuenta(v, f"{pref}AR{anio}0001", "DE89370400440532013000", "OECD601", individuo,
                "1500.00", "CRS502", "CRS1101"),
        _cuenta(v, f"{pref}AR{anio}0002", "POL-0001", "OECD605", organizacion, "25000.00",
                "CRS504", "CRS1103", controlador),
    ]
    if v3:
        cuentas.append(_cuenta(v, f"{pref}AR{anio}0003", "EMONEY-0001", "OECD606", individuo,
                               "80.00", "CRS502", "CRS1101"))
        equity = "<crs:EquityInterestType>CRS401</crs:EquityInterestType>"
        cuentas.append(
            _cuenta(v, f"{pref}AR{anio}0004", "US0378331005", "OECD603", individuo,
                    "3000.00", "CRS503", "CRS1104").replace("<crs:AccountHolder>",
                                                             f"<crs:AccountHolder>{equity}")
        )
    else:
        cuentas.append(_cuenta(v, f"{pref}AR{anio}0003", "US0378331005", "OECD603", individuo,
                               "3000.00", "CRS503", ""))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<crs:CRS_OECD xmlns:crs="{NS[v]}" xmlns:stf="{STF}" xmlns:cfc="{CFC}" xmlns:ftc="{FTC}" version="{v}">
  <crs:MessageSpec>
    <crs:TransmittingCountry>ES</crs:TransmittingCountry>
    <crs:ReceivingCountry>{rc}</crs:ReceivingCountry>
    <crs:MessageType>CRS</crs:MessageType>
    <crs:MessageRefId>{mri}</crs:MessageRefId>
    <crs:MessageTypeIndic>CRS701</crs:MessageTypeIndic>
    <crs:ReportingPeriod>{anio}-12-31</crs:ReportingPeriod>
    <crs:Timestamp>{int(anio) + 1}-03-15T09:45:30.789</crs:Timestamp>
  </crs:MessageSpec>
  <crs:CrsBody>
    <crs:ReportingFI>
      <crs:ResCountryCode>ES</crs:ResCountryCode>
      <crs:IN issuedBy="ES">A00000000</crs:IN>
      <crs:Name>Example Bank, S.A.</crs:Name>
      <crs:Address><cfc:CountryCode>ES</cfc:CountryCode><cfc:AddressFree>Example street 3, Madrid</cfc:AddressFree></crs:Address>
      {_docspec("OECD1", f"{pref}FI{anio}0001")}
    </crs:ReportingFI>
    <crs:ReportingGroup>{"".join(cuentas)}
    </crs:ReportingGroup>
  </crs:CrsBody>
</crs:CRS_OECD>
"""


# --- Mutaciones: cada una rompe UNA regla ---------------------------------------------

Arbol = etree._Element


def _x(r: Arbol, xpath: str) -> list[Arbol]:
    ns = {"crs": etree.QName(r).namespace or "", "stf": STF, "cfc": CFC, "ftc": FTC}
    return list(r.xpath(xpath, namespaces=ns))  # type: ignore[arg-type]


def _1(r: Arbol, xpath: str) -> Arbol:
    encontrados = _x(r, xpath)
    assert len(encontrados) >= 1, xpath
    return encontrados[0]


def _e(r: Arbol, local: str, ns: str | None = None, text: str | None = None) -> Arbol:
    el = etree.Element(f"{{{ns or etree.QName(r).namespace}}}{local}")
    el.text = text
    return el


AR = "//crs:AccountReport"


def _ar(r: Arbol, n: int) -> Arbol:
    return _x(r, AR)[n - 1]


def _set(r: Arbol, xpath: str, valor: str) -> None:
    _1(r, xpath).text = valor


def _a_correccion(r: Arbol, tipo_ar: str, corr: str | None, quedan: int = 1) -> None:
    """Convierte el mensaje en una corrección: RFI reenviado y las primeras cuentas."""
    _set(r, "//crs:MessageTypeIndic", "CRS702")
    _set(r, "//crs:MessageRefId", "ES2026DE0000000002")
    _set(r, "//crs:ReportingFI/crs:DocSpec/stf:DocTypeIndic", "OECD0")
    for ar in _x(r, AR)[quedan:]:
        ar.getparent().remove(ar)  # type: ignore[union-attr]
    for i, ar in enumerate(_x(r, AR), start=1):
        _set(ar, "crs:DocSpec/stf:DocTypeIndic", tipo_ar)
        _set(ar, "crs:DocSpec/stf:DocRefId", f"ESAR2026C00{i}")
        if corr is not None:
            ds = _1(ar, "crs:DocSpec")
            ds.append(_e(r, "CorrDocRefId", STF, corr))


def _organizacion_separada(r: Arbol, otro: str) -> Arbol:
    """Una entidad (Sponsor/Intermediary) válida con su DocSpec."""
    org = copy.deepcopy(_1(r, "//crs:ReportingFI"))
    org.tag = f"{{{etree.QName(r).namespace}}}{otro}"
    _set(org, "crs:DocSpec/stf:DocRefId", f"ES{otro[:2].upper()}20260001")
    return org


def _m_60007(r: Arbol) -> None:
    grupo = _1(r, "//crs:ReportingGroup")
    nuevo = copy.deepcopy(grupo)
    for ar in _x(nuevo, "crs:AccountReport")[1:]:
        nuevo.remove(ar)
    _set(nuevo, "crs:AccountReport/crs:DocSpec/stf:DocRefId", "ESAR20260099")
    grupo.addnext(nuevo)


def _m_60008(r: Arbol) -> None:
    _1(r, "//crs:ReportingGroup").insert(0, _organizacion_separada(r, "Sponsor"))


def _m_60009(r: Arbol) -> None:
    _1(r, "//crs:ReportingGroup").insert(0, _organizacion_separada(r, "Intermediary"))


def _m_60010(r: Arbol) -> None:
    pool = etree.fromstring(f"""<crs:PoolReport xmlns:crs="{etree.QName(r).namespace}"
        xmlns:ftc="{FTC}" xmlns:stf="{STF}">
      <ftc:DocSpec><stf:DocTypeIndic>OECD1</stf:DocTypeIndic><stf:DocRefId>ESPR20260001</stf:DocRefId></ftc:DocSpec>
      <ftc:AccountCount>3</ftc:AccountCount>
      <ftc:AccountPoolReportType>FATCA201</ftc:AccountPoolReportType>
      <ftc:PoolBalance currCode="EUR">100.00</ftc:PoolBalance>
    </crs:PoolReport>""")
    _1(r, "//crs:ReportingGroup").append(pool)


def _m_60011(r: Arbol) -> None:
    ind = _1(_ar(r, 1), "crs:AccountHolder/crs:Individual")
    _set(ind, "crs:ResCountryCode", "FR")
    _set(ind, "crs:Address/cfc:CountryCode", "FR")


def _m_60012(r: Arbol) -> None:
    ar = _ar(r, 2)
    _set(ar, "crs:AccountHolder/crs:AcctHolderType", "CRS102")
    ar.remove(_1(ar, "crs:ControllingPerson"))
    _set(ar, "crs:AccountHolder/crs:Organisation/crs:ResCountryCode", "FR")


def _m_60015(r: Arbol) -> None:
    for ar in _x(r, AR):
        ar.getparent().remove(ar)  # type: ignore[union-attr]


def _m_60016(r: Arbol) -> None:
    cp = copy.deepcopy(_1(_ar(r, 2), "crs:ControllingPerson"))
    _1(_ar(r, 1), "crs:AccountHolder").addnext(cp)


def _m_80000(r: Arbol) -> None:
    _set(_ar(r, 3), "crs:DocSpec/stf:DocRefId", "ESAR20260001")


def _m_80004(r: Arbol) -> None:
    _1(_ar(r, 1), "crs:DocSpec").append(_e(r, "CorrDocRefId", STF, "ESAR20250001"))


def _m_80006(r: Arbol) -> None:
    _1(_ar(r, 1), "crs:DocSpec/stf:DocRefId").addnext(
        _e(r, "CorrMessageRefId", STF, "ES2025DE0000000001")
    )


def _m_80007(r: Arbol) -> None:
    _1(r, "//crs:MessageTypeIndic").addnext(_e(r, "CorrMessageRefId", text="ES2025DE00001"))


def _m_80009(r: Arbol) -> None:
    _a_correccion(r, "OECD2", "ESAR20250001")
    _set(r, "//crs:ReportingFI/crs:DocSpec/stf:DocTypeIndic", "OECD3")
    _set(r, "//crs:ReportingFI/crs:DocSpec/stf:DocRefId", "ESFI2026C001")
    _1(r, "//crs:ReportingFI/crs:DocSpec").append(_e(r, "CorrDocRefId", STF, "ESFI20250001"))


def _m_80010(r: Arbol) -> None:
    _set(_ar(r, 1), "crs:DocSpec/stf:DocTypeIndic", "OECD2")
    _1(_ar(r, 1), "crs:DocSpec").append(_e(r, "CorrDocRefId", STF, "ESAR20250001"))


def _m_80011(r: Arbol) -> None:
    _a_correccion(r, "OECD2", "ESAR20250001", quedan=2)


def _m_80015(r: Arbol) -> None:
    r.remove(_1(r, "crs:CrsBody"))


def _m_50010_50011(r: Arbol) -> None:
    _set(_ar(r, 1), "crs:DocSpec/stf:DocTypeIndic", "OECD11")


def _m_50010(r: Arbol) -> None:
    for dti in _x(r, "//stf:DocTypeIndic"):
        dti.text = dti.text.replace("OECD", "OECD1")  # type: ignore[union-attr]


def _m_50009(r: Arbol) -> None:
    for dr in _x(r, "//stf:DocRefId"):
        dr.text = (dr.text or "") + "B"


Mutacion = Callable[[Arbol], None]

CASOS: dict[str, tuple[str, Mutacion, list[str]]] = {
    "50007-schema": ("3.0", lambda r: _set(r, "//crs:AccountBalance", "abc"), ["OECD-50007"]),
    "50008-messagerefid": ("3.0", lambda r: _set(r, "//crs:MessageRefId", "MSG-000001"),
                           ["OECD-50008"]),
    "50009-same-messagerefid": ("3.0", _m_50009, []),
    "50010-test-data": ("3.0", _m_50010, ["OECD-50010"]),
    "50010-50011-test-and-live": ("3.0", _m_50010_50011, ["OECD-50010-50011"]),
    "60000-iban": ("3.0", lambda r: _set(_ar(r, 1), "crs:AccountNumber",
                                         "DE89370400440532013001"), ["OECD-60000"]),
    "60001-isin": ("3.0", lambda r: _set(_ar(r, 4), "crs:AccountNumber", "US0378331006"),
                   ["OECD-60001"]),
    "60002-negative-balance": ("3.0", lambda r: _set(_ar(r, 1), "crs:AccountBalance",
                                                     "-1.00"), ["OECD-60002"]),
    "60003-closed-with-balance": (
        "3.0", lambda r: _1(_ar(r, 1), "crs:AccountNumber").set("ClosedAccount", "true"),
        ["OECD-60003"]),
    "60004-name-type": (
        "3.0", lambda r: _1(_ar(r, 1), ".//crs:Name").set("nameType", "OECD201"),
        ["OECD-60004"]),
    "60005-cp-must-be-omitted": (
        "3.0", lambda r: _set(_ar(r, 2), "crs:AccountHolder/crs:AcctHolderType", "CRS102"),
        ["OECD-60005"]),
    "60006-cp-must-be-provided": (
        "3.0", lambda r: _ar(r, 2).remove(_1(_ar(r, 2), "crs:ControllingPerson")),
        ["OECD-60006"]),
    "60007-reporting-group": ("3.0", _m_60007, ["OECD-60007"]),
    "60008-sponsor": ("3.0", _m_60008, ["OECD-60008"]),
    "60009-intermediary": ("3.0", _m_60009, ["OECD-60009"]),
    "60010-pool-report": ("3.0", _m_60010, ["OECD-60010"]),
    "60011-person-rescountry": ("3.0", _m_60011, ["OECD-60011"]),
    "60012-organisation-rescountry": ("3.0", _m_60012, ["OECD-60012"]),
    "60013-fi-rescountry": (
        "3.0", lambda r: _set(r, "//crs:ReportingFI/crs:ResCountryCode", "PT"),
        ["OECD-60013"]),
    "60014-birthdate": ("3.0", lambda r: _set(_ar(r, 1), ".//crs:BirthDate", "1850-01-01"),
                        ["OECD-60014"]),
    "60015-no-account-report": ("3.0", _m_60015, ["OECD-60015"]),
    "60016-individual-with-cp": ("3.0", _m_60016, ["OECD-60016"]),
    "60017-emoney-not-depository": (
        "3.0", lambda r: _set(_ar(r, 3), "crs:AccountType", "CRS1102"), ["OECD-60017"]),
    "60018-iban-not-depository": (
        "3.0", lambda r: _set(_ar(r, 1), "crs:AccountType", "CRS1102"), ["OECD-60018"]),
    "60019-equity-interest-type": (
        "3.0", lambda r: _1(_ar(r, 1), "crs:AccountHolder").insert(
            0, _e(r, "EquityInterestType", text="CRS401")), ["OECD-60019"]),
    "60020-insurance-account-number": (
        "3.0", lambda r: _1(_ar(r, 2), "crs:AccountNumber").set("AcctNumberType", "OECD602"),
        ["OECD-60020"]),
    "60021-depository-payment": (
        "3.0", lambda r: _set(_ar(r, 1), "crs:Payment/crs:Type", "CRS501"), ["OECD-60021"]),
    "60022-investment-entity-payment": (
        "3.0", lambda r: _set(_ar(r, 4), "crs:Payment/crs:Type", "CRS502"), ["OECD-60022"]),
    "60023-insurance-payment": (
        "3.0", lambda r: _set(_ar(r, 2), "crs:Payment/crs:Type", "CRS502"), ["OECD-60023"]),
    "80000-docrefid-twice": ("3.0", _m_80000, ["OECD-80000"]),
    "80001-docrefid-format": (
        "3.0", lambda r: _set(_ar(r, 1), "crs:DocSpec/stf:DocRefId", "XXAR20260001"),
        ["OECD-80001"]),
    "80004-corrdocrefid-on-new-data": ("3.0", _m_80004, ["OECD-80004"]),
    "80005-missing-corrdocrefid": ("3.0", lambda r: _a_correccion(r, "OECD2", None),
                                   ["OECD-80005"]),
    "80006-docspec-corrmessagerefid": ("3.0", _m_80006, ["OECD-80006"]),
    "80007-messagespec-corrmessagerefid": ("3.0", _m_80007, ["OECD-80007"]),
    "80008-resend-account-report": ("3.0", lambda r: _a_correccion(r, "OECD0", None),
                                    ["OECD-80008"]),
    "80009-delete-fi-not-accounts": ("3.0", _m_80009, ["OECD-80009"]),
    "80010-new-and-corrected": ("3.0", _m_80010, ["OECD-80010"]),
    "80011-corrected-twice": ("3.0", _m_80011, ["OECD-80011"]),
    "80015-no-crsbody": ("3.0", _m_80015, ["OECD-80015"]),
    "ug-version-attribute": ("3.0", lambda r: r.set("version", "2.0"), ["UG-VERSION"]),
    "ug-timestamp-fraction": (
        "3.0", lambda r: _set(r, "//crs:Timestamp", "2027-03-15T09:45:30.7"),
        ["UG-TIMESTAMP"]),
    "60000-iban-print-format": ("3.0", lambda r: _set(_ar(r, 1), "crs:AccountNumber",
                                                      "DE89 3704 0044 0532 0130 00"),
                                ["OECD-60000"]),
    "v2-60000-iban": ("2.0", lambda r: _set(_ar(r, 1), "crs:AccountNumber",
                                            "DE89370400440532013001"), ["OECD-60000"]),
    "v2-60021-not-in-v2": (
        "2.0", lambda r: _set(_ar(r, 1), "crs:Payment/crs:Type", "CRS501"), []),
}


def _escribe(ruta: Path, raiz: Arbol) -> None:
    etree.indent(raiz, space="  ")
    texto = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    ruta.write_bytes(texto)


def genera(destino: Path = DESTINO) -> dict[str, list[str]]:
    destino.mkdir(parents=True, exist_ok=True)
    parser = etree.XMLParser(remove_blank_text=True)
    esperados: dict[str, list[str]] = {}
    for nombre, v, nacional, reglas in (
        ("valid-2.0", "2.0", False, []), ("valid-3.0", "3.0", False, []),
        # Detectado como nacional (ES → ES): lo dice con CTX-DOMESTIC; con
        # --context domestic, explícito, sale limpio.
        ("valid-domestic-3.0", "3.0", True, ["CTX-DOMESTIC"]),
    ):
        _escribe(destino / f"{nombre}.xml",
                 etree.fromstring(mensaje(v, nacional=nacional).encode(), parser))
        esperados[f"{nombre}.xml"] = reglas
    for nombre, (v, mutar, reglas) in CASOS.items():
        raiz = etree.fromstring(mensaje(v).encode(), parser)
        mutar(raiz)
        _escribe(destino / f"{nombre}.xml", raiz)
        esperados[f"{nombre}.xml"] = sorted(reglas)
    (destino / "expected.json").write_text(
        json.dumps(esperados, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return esperados


if __name__ == "__main__":
    print(f"{len(genera())} fixtures in {DESTINO}")
