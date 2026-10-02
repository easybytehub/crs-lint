"""Las reglas de negocio de la CRS Status Message que se pueden comprobar con el fichero.

**Sólo lo que la guía escribe.** Cada comprobación corresponde a un código de la Status
Message User Guide (o, en `UG-*`, a una frase con «must»/«will» de la XML Schema User
Guide) y se aplica tal como está escrita: ni más estricta (sería un falso positivo que
alguien «arreglaría» en un generador correcto) ni más laxa.

**Dos interpretaciones que conviene saber, y están en SPEC.md:**

- *Intercambio o declaración nacional.* Las reglas de «data sorting» (60011, 60012) y el
  formato de MessageRefID (50008) están escritas para mensajes entre autoridades
  competentes. Para la declaración nacional la propia OCDE dice que emisor y receptor
  son el país propio («[For domestic reporting this element would be the domestic
  Country Code.]», UG) y cada país fija su formato de identificadores (IRAS: año + NIF +
  …). Ahí esas tres reglas no se aplican; 80001 sí, pero como aviso, porque la guía dice
  «in all cases». Si el contexto se ha deducido (y no pedido), el informe lo dice con
  CTX-DOMESTIC: un intercambio mal etiquetado no puede salir limpio sin rastro.
- *Datos de prueba.* OECD10–13 son la versión de prueba de OECD0–3 (la guía los define
  uno a uno así), de modo que las reglas de estructura tratan OECD11 como OECD1, etc.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from lxml import etree

from crs_lint.catalogo import REGLAS
from crs_lint.hallazgos import Hallazgo, Severidad

_BASE = {
    "OECD0": 0, "OECD1": 1, "OECD2": 2, "OECD3": 3,
    "OECD10": 0, "OECD11": 1, "OECD12": 2, "OECD13": 3,
}
_PRUEBA = {"OECD10", "OECD11", "OECD12", "OECD13"}
_VERDADERO = {"true", "1"}


def nombre(el: etree._Element) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def hijos(el: etree._Element | None, local: str) -> list[etree._Element]:
    if el is None:
        return []
    return [c for c in el if isinstance(c.tag, str) and nombre(c) == local]


def hijo(el: etree._Element | None, local: str) -> etree._Element | None:
    encontrados = hijos(el, local)
    return encontrados[0] if encontrados else None


def texto(el: etree._Element | None, local: str) -> str | None:
    h = hijo(el, local)
    if h is None or h.text is None:
        return None
    return h.text.strip()


def descendientes(el: etree._Element, local: str) -> Iterator[etree._Element]:
    for d in el.iter():
        if isinstance(d.tag, str) and nombre(d) == local:
            yield d


def _primero(
    a: etree._Element | None, b: etree._Element | None
) -> etree._Element | None:
    # No `a or b`: la verdad de un elemento de lxml depende de si tiene hijos (y avisa).
    return a if a is not None else b


def linea_de(el: etree._Element | None) -> int:
    """La línea del elemento en el fichero; 0 si no se sabe."""
    linea = el.sourceline if el is not None else None
    return linea if isinstance(linea, int) else 0


def _iban_estructura(s: str) -> bool:
    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}", s):
        return False
    reordenado = s[4:] + s[:4]
    numero = "".join(str(int(c, 36)) for c in reordenado)
    return int(numero) % 97 == 1


def iban_estado(valor: str) -> str:
    """`ok`, `impresion` o `invalido`, según ISO 13616 (país, control, BBAN, módulo 97).

    `impresion`: con espacios o minúsculas la estructura es correcta pero no es el
    formato electrónico. Es un aviso, no un error: la guía pide «the IBAN structured
    number format» y no dice nada de la presentación. La longitud por país no se
    comprueba: exigiría el registro de SWIFT.
    """
    if _iban_estructura(valor):
        return "ok"
    if _iban_estructura(valor.replace(" ", "").upper()):
        return "impresion"
    return "invalido"


def iban_valido(valor: str) -> bool:
    """Estructura correcta, en formato electrónico o de impresión."""
    return iban_estado(valor) != "invalido"


def isin_valido(valor: str) -> bool:
    """ISO 6166: dos letras, nueve alfanuméricos y un dígito de control (Luhn)."""
    s = valor.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", s):
        return False
    digitos = "".join(str(int(c, 36)) for c in s[:-1])
    total = 0
    for i, c in enumerate(reversed(digitos)):
        n = int(c)
        if i % 2 == 0:  # empezando por la derecha, sin contar el de control
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - total % 10) % 10 == int(s[-1])


@dataclass
class Vistos:
    """Identificadores ya vistos en los ficheros anteriores de la misma ejecución."""

    mensajes: dict[str, str] = field(default_factory=dict)
    documentos: dict[str, str] = field(default_factory=dict)


def contexto_de(raiz: etree._Element, pedido: str) -> str:
    """`exchange` o `domestic`. En `auto`, doméstico si el país emisor y el receptor son
    el mismo: es lo que piden las guías nacionales (IRAS: «SG» y «SG»)."""
    if pedido != "auto":
        return pedido
    ms = hijo(raiz, "MessageSpec")
    tc, rc = texto(ms, "TransmittingCountry"), texto(ms, "ReceivingCountry")
    return "domestic" if tc and rc and tc == rc else "exchange"


class _Revision:
    def __init__(
        self, raiz: etree._Element, fichero: str, version: str, contexto: str, hoy: date,
        vistos: Vistos, contexto_auto: bool = False,
    ) -> None:
        self.raiz = raiz
        self.fichero = fichero
        self.version = version
        self.contexto = contexto
        self.contexto_auto = contexto_auto
        self.hoy = hoy
        self.vistos = vistos
        self.hallazgos: list[Hallazgo] = []
        ms = hijo(raiz, "MessageSpec")
        self.ms = ms
        self.tc = texto(ms, "TransmittingCountry")
        self.rc = texto(ms, "ReceivingCountry")
        self.mti = texto(ms, "MessageTypeIndic")

    def marca(
        self, regla_id: str, detalle: str, el: etree._Element | None = None,
        severidad: Severidad | None = None,
    ) -> None:
        regla = REGLAS[regla_id]
        if self.version not in regla.versiones:
            return
        if regla.solo_intercambio and self.contexto != "exchange":
            return
        self.hallazgos.append(
            regla.hallazgo(
                detalle, version=self.version, fichero=self.fichero, linea=linea_de(el),
                severidad=severidad,
            )
        )

    # --- cabecera ----------------------------------------------------------------------
    def cabecera(self, version_raiz: str) -> None:
        declarada = self.raiz.get("version")
        if declarada != version_raiz:
            self.marca(
                "UG-VERSION",
                f'CRS_OECD has version="{declarada}" in the namespace of schema '
                f"{version_raiz}; it must be \"{version_raiz}\".",
                self.raiz,
            )
        ms = self.ms
        if ms is None:
            return
        if self.tc and self.tc == self.rc:
            if self.contexto == "domestic" and self.contexto_auto:
                self.marca(
                    "CTX-DOMESTIC",
                    f"TC=RC={self.tc}: treated as domestic; 50008/60011/60012 not applied and "
                    "80001 only as a warning; use --context exchange for a Competent "
                    "Authority message.",
                    hijo(ms, "ReceivingCountry"),
                )
            elif self.contexto == "exchange":
                self.marca(
                    "OECD-50012",
                    f"An exchange between Competent Authorities with TransmittingCountry and "
                    f"ReceivingCountry both {self.tc}.",
                    hijo(ms, "ReceivingCountry"),
                )
        for c in hijos(ms, "CorrMessageRefId"):
            self.marca("OECD-80007", f"MessageSpec has CorrMessageRefId '{c.text}'.", c)
        ts = hijo(ms, "Timestamp")
        if ts is not None and ts.text:
            m = re.search(r"T\d{2}:\d{2}:\d{2}\.(\d+)", ts.text)
            if m and len(m.group(1)) != 3:
                self.marca(
                    "UG-TIMESTAMP",
                    f"Timestamp '{ts.text.strip()}' has {len(m.group(1))} digits of fraction "
                    "of seconds; the User Guide format is yyyy-MM-DD'T'hh:mm:ss.nnn.",
                    ts,
                )
        self._message_ref_id(ms)

    def _message_ref_id(self, ms: etree._Element) -> None:
        mri_el = hijo(ms, "MessageRefId")
        mri = texto(ms, "MessageRefId")
        if mri is None or mri_el is None:
            return
        anterior = self.vistos.mensajes.get(mri)
        if anterior is not None:
            self.marca(
                "OECD-50009",
                f"MessageRefId '{mri}' is also the MessageRefId of {anterior}.", mri_el,
            )
        else:
            self.vistos.mensajes[mri] = self.fichero
        if not self.tc or not self.rc:
            return
        m = re.fullmatch(rf"{re.escape(self.tc)}([0-9]{{4}}){re.escape(self.rc)}(.+)", mri)
        if m is None:
            self.marca(
                "OECD-50008",
                f"MessageRefId '{mri}' does not start with <sending country {self.tc}><year>"
                f"<receiving country {self.rc}> followed by a unique identifier.",
                mri_el,
            )
            return
        periodo = texto(ms, "ReportingPeriod")
        anio = periodo[:4] if periodo else ""
        if anio.isdigit() and m.group(1) not in (anio, str(int(anio) - 1)):
            self.marca(
                "OECD-50008",
                f"The year in MessageRefId '{mri}' is {m.group(1)}, but ReportingPeriod ends "
                f"on {periodo}: the year 'to which the data relates' is the year the period "
                "begins or ends.",
                mri_el, severidad=Severidad.AVISO,
            )

    # --- DocSpec -----------------------------------------------------------------------
    def docspecs(self) -> None:
        bases: list[int] = []
        pruebas: list[bool] = []
        propios: dict[str, int] = {}
        corregidos: dict[str, int] = {}
        for ds in descendientes(self.raiz, "DocSpec"):
            dti = texto(ds, "DocTypeIndic")
            drid_el = hijo(ds, "DocRefId")
            drid = texto(ds, "DocRefId")
            corr_el = hijo(ds, "CorrDocRefId")
            corr = texto(ds, "CorrDocRefId")
            base = _BASE.get(dti or "")
            if base is not None and dti is not None:
                bases.append(base)
                pruebas.append(dti in _PRUEBA)
            for c in hijos(ds, "CorrMessageRefId"):
                self.marca("OECD-80006", f"DocSpec has CorrMessageRefId '{c.text}'.", c)
            if base == 1 and corr is not None:
                self.marca(
                    "OECD-80004",
                    f"DocRefId '{drid}' is new data ({dti}) and has CorrDocRefId '{corr}'.",
                    corr_el,
                )
            if base in (2, 3) and corr is None:
                self.marca(
                    "OECD-80005",
                    f"DocRefId '{drid}' is a correction/deletion ({dti}) without CorrDocRefId.",
                    ds,
                )
            if drid is not None and drid_el is not None:
                if self.tc and not drid.startswith(self.tc):
                    nacional = self.contexto == "domestic"
                    self.marca(
                        "OECD-80001",
                        f"DocRefId '{drid}' does not start with the sending country code "
                        f"'{self.tc}'."
                        + (" Domestic file: the national format may differ." if nacional
                           else ""),
                        drid_el, severidad=Severidad.AVISO if nacional else None,
                    )
                if drid in propios:
                    self.marca(
                        "OECD-80000",
                        f"DocRefId '{drid}' is also used on line {propios[drid]} of this file.",
                        drid_el,
                    )
                else:
                    propios[drid] = linea_de(drid_el)
                    # Un Reporting FI reenviado (OECD0) conserva su DocRefId original: la
                    # guía lo muestra así en sus ejemplos de corrección.
                    if base != 0:
                        anterior = self.vistos.documentos.get(drid)
                        if anterior is not None:
                            self.marca(
                                "OECD-80000",
                                f"DocRefId '{drid}' is also used in {anterior}.", drid_el,
                            )
                        else:
                            self.vistos.documentos[drid] = self.fichero
            if corr is not None and corr_el is not None:
                if corr in corregidos:
                    self.marca(
                        "OECD-80011",
                        f"CorrDocRefId '{corr}' is also corrected/deleted on line "
                        f"{corregidos[corr]}.",
                        corr_el,
                    )
                else:
                    corregidos[corr] = linea_de(corr_el)
        self._mezclas(bases, pruebas)

    def _mezclas(self, bases: list[int], pruebas: list[bool]) -> None:
        if any(pruebas) and not all(pruebas):
            self.marca(
                "OECD-50010-50011",
                "The file has both test (OECD10-OECD13) and live (OECD0-OECD3) DocTypeIndic "
                "values: production rejects it with 50010 and a test environment with 50011.",
                self.raiz,
            )
        elif pruebas and all(pruebas):
            self.marca(
                "OECD-50010",
                "Every DocTypeIndic is test data (OECD10-OECD13): fine for an agreed test "
                "window, rejected with 50010 if sent to production.",
                self.raiz,
            )
        nuevos = 1 in bases
        correcciones = 2 in bases or 3 in bases
        ms_el = hijo(self.ms, "MessageTypeIndic") if self.ms is not None else None
        if nuevos and correcciones:
            self.marca(
                "OECD-80010",
                "The message mixes new records (OECD1/OECD11) with corrections or deletions "
                "(OECD2/OECD3/OECD12/OECD13).",
                ms_el,
            )
        elif self.mti == "CRS701" and correcciones:
            self.marca(
                "OECD-80010",
                "MessageTypeIndic is CRS701 (new information) but the message has "
                "corrections or deletions.",
                ms_el,
            )
        elif self.mti == "CRS702" and nuevos:
            self.marca(
                "OECD-80010",
                "MessageTypeIndic is CRS702 (corrections/deletions) but the message has new "
                "records.",
                ms_el,
            )

    # --- cuerpo ------------------------------------------------------------------------
    def cuerpos(self) -> None:
        cuerpos = hijos(self.raiz, "CrsBody")
        if not cuerpos and self.ms is not None:
            sci = hijo(self.ms, "SendingCompanyIN")
            if self.mti != "CRS703" or sci is not None:
                motivo = (
                    f"MessageTypeIndic is {self.mti}" if self.mti != "CRS703"
                    else "SendingCompanyIN is present"
                )
                self.marca("OECD-80015", f"There is no CrsBody and {motivo}.", self.ms)
        for cuerpo in cuerpos:
            self._cuerpo(cuerpo)

    def _cuerpo(self, cuerpo: etree._Element) -> None:
        rfi = hijo(cuerpo, "ReportingFI")
        if rfi is not None:
            paises = [c.text.strip() for c in hijos(rfi, "ResCountryCode") if c.text]
            if not paises:
                self.marca("OECD-60013", "ReportingFI has no ResCountryCode.", rfi)
            elif self.tc and self.tc not in paises:
                self.marca(
                    "OECD-60013",
                    f"ReportingFI ResCountryCode is {', '.join(paises)}; TransmittingCountry "
                    f"is {self.tc}.",
                    hijo(rfi, "ResCountryCode"),
                )
        grupos = hijos(cuerpo, "ReportingGroup")
        for extra in grupos[1:]:
            self.marca(
                "OECD-60007", f"CrsBody has {len(grupos)} ReportingGroup elements.", extra
            )
        cuentas: list[etree._Element] = []
        for g in grupos:
            for local, regla in (
                ("Sponsor", "OECD-60008"), ("Intermediary", "OECD-60009"),
                ("PoolReport", "OECD-60010"),
            ):
                for el in hijos(g, local):
                    self.marca(regla, f"ReportingGroup has a {local}.", el)
            cuentas += hijos(g, "AccountReport")

        base_fi = _BASE.get(texto(hijo(rfi, "DocSpec"), "DocTypeIndic") or "")
        if not cuentas and self.mti != "CRS703" and base_fi in (0, 1):
            self.marca(
                "OECD-60015",
                "No AccountReport, the ReportingFI is new or resent data and "
                f"MessageTypeIndic is {self.mti}, not CRS703 (nil).",
                rfi,
            )
        for ar in cuentas:
            base_ar = _BASE.get(texto(hijo(ar, "DocSpec"), "DocTypeIndic") or "")
            if base_ar == 0:
                self.marca(
                    "OECD-80008", "An AccountReport uses the Resend option (OECD0/OECD10).",
                    hijo(hijo(ar, "DocSpec"), "DocTypeIndic"),
                )
            if base_fi == 3 and base_ar is not None and base_ar != 3:
                self.marca(
                    "OECD-80009",
                    "The ReportingFI is deleted (OECD3/OECD13) but this AccountReport is not.",
                    hijo(hijo(ar, "DocSpec"), "DocTypeIndic"),
                )
            self._cuenta(ar)

    # --- AccountReport -----------------------------------------------------------------
    def _cuenta(self, ar: etree._Element) -> None:
        numero = hijo(ar, "AccountNumber")
        tipo_num = numero.get("AcctNumberType") if numero is not None else None
        valor = (numero.text or "").strip() if numero is not None else ""
        if tipo_num == "OECD601":
            estado = iban_estado(valor)
            if estado == "invalido":
                self.marca("OECD-60000", f"'{valor}' is not a valid IBAN.", numero)
            elif estado == "impresion":
                self.marca(
                    "OECD-60000",
                    f"'{valor}' is a valid IBAN in print format (spaces or lower case); the "
                    "electronic format has neither.",
                    numero, severidad=Severidad.AVISO,
                )
        if tipo_num == "OECD603" and not isin_valido(valor):
            self.marca("OECD-60001", f"'{valor}' is not a valid ISIN.", numero)

        saldo_el = hijo(ar, "AccountBalance")
        saldo_txt = texto(ar, "AccountBalance")
        saldo: Decimal | None = None
        if saldo_txt:
            try:
                saldo = Decimal(saldo_txt)
            except InvalidOperation:
                saldo = None  # el XSD ya lo señala
        if saldo is not None and saldo < 0:
            self.marca("OECD-60002", f"AccountBalance is {saldo_txt}.", saldo_el)
        cerrada = numero is not None and (numero.get("ClosedAccount") or "") in _VERDADERO
        if cerrada and saldo is not None and saldo != 0:
            self.marca(
                "OECD-60003", f"ClosedAccount is true and AccountBalance is {saldo_txt}.",
                saldo_el,
            )

        titular = hijo(ar, "AccountHolder")
        individuo = hijo(titular, "Individual")
        organizacion = hijo(titular, "Organisation")
        tipo_titular = texto(titular, "AcctHolderType")
        controladores = hijos(ar, "ControllingPerson")
        if individuo is not None and controladores:
            self.marca(
                "OECD-60016", "The Account Holder is an Individual and there is a "
                "ControllingPerson.", controladores[0],
            )
        if organizacion is not None and tipo_titular in ("CRS102", "CRS103") and controladores:
            self.marca(
                "OECD-60005", f"AcctHolderType is {tipo_titular} and there is a "
                "ControllingPerson.", controladores[0],
            )
        if organizacion is not None and tipo_titular == "CRS101" and not controladores:
            self.marca(
                "OECD-60006", "AcctHolderType is CRS101 and there is no ControllingPerson.",
                hijo(titular, "AcctHolderType"),
            )

        personas = [individuo] if individuo is not None else []
        personas += [p for c in controladores if (p := hijo(c, "Individual")) is not None]
        for p in personas:
            self._persona(p)
        self._clasificacion(individuo, organizacion, controladores)
        if self.version == "3.0":
            self._tipos_v3(ar, titular, tipo_num)

    def _persona(self, p: etree._Element) -> None:
        for n in hijos(p, "Name"):
            if n.get("nameType") == "OECD201":
                self.marca("OECD-60004", "A person Name has nameType OECD201.", n)
        for nac in descendientes(p, "BirthDate"):
            valor = (nac.text or "").strip()
            try:
                anio = date.fromisoformat(valor[:10]).year
            except ValueError:
                continue  # el XSD ya lo señala
            if anio < 1900 or anio > self.hoy.year:
                self.marca(
                    "OECD-60014",
                    f"BirthDate is {valor}: before 1900 or after {self.hoy.year}.", nac,
                )

    def _clasificacion(
        self, individuo: etree._Element | None, organizacion: etree._Element | None,
        controladores: list[etree._Element],
    ) -> None:
        rc = self.rc
        if not rc:
            return

        def residencias(parte: etree._Element | None) -> list[str]:
            return [c.text.strip() for c in hijos(parte, "ResCountryCode") if c.text]

        if individuo is not None and rc not in residencias(individuo):
            self.marca(
                "OECD-60011",
                f"The Individual Account Holder is resident in "
                f"{', '.join(residencias(individuo)) or '(none)'}; ReceivingCountry is {rc}.",
                _primero(hijo(individuo, "ResCountryCode"), individuo),
            )
        for c in controladores:
            ind = hijo(c, "Individual")
            if ind is not None and rc not in residencias(ind):
                self.marca(
                    "OECD-60011",
                    f"A Controlling Person is resident in "
                    f"{', '.join(residencias(ind)) or '(none)'}; ReceivingCountry is {rc}.",
                    _primero(hijo(ind, "ResCountryCode"), ind),
                )
        if organizacion is not None:
            todos = residencias(organizacion)
            for c in controladores:
                todos += residencias(hijo(c, "Individual"))
            if rc not in todos:
                self.marca(
                    "OECD-60012",
                    f"Neither the Entity Account Holder nor its Controlling Persons are "
                    f"resident in {rc} (found: {', '.join(todos) or 'none'}).",
                    organizacion,
                )

    def _tipos_v3(
        self, ar: etree._Element, titular: etree._Element | None, tipo_num: str | None
    ) -> None:
        tipo_el = hijo(ar, "AccountType")
        tipo = texto(ar, "AccountType")
        if tipo is None:
            return  # el XSD ya lo señala
        numero = hijo(ar, "AccountNumber")
        if tipo_num == "OECD606" and tipo != "CRS1101":
            self.marca("OECD-60017", f"AcctNumberType is OECD606 and AccountType is {tipo}.",
                       tipo_el)
        if tipo_num == "OECD601" and tipo != "CRS1101":
            self.marca("OECD-60018", f"AcctNumberType is OECD601 and AccountType is {tipo}.",
                       tipo_el)
        participaciones = hijos(titular, "EquityInterestType")
        if participaciones and tipo != "CRS1104":
            self.marca(
                "OECD-60019", f"EquityInterestType is provided and AccountType is {tipo}.",
                participaciones[0],
            )
        if tipo == "CRS1103":
            if tipo_num is None:
                self.marca(
                    "OECD-60020",
                    "AccountType is CRS1103 and AccountNumber has no AcctNumberType: 60020 "
                    "requires OECD605.", numero, severidad=Severidad.INCOMPLETO,
                )
            elif tipo_num != "OECD605":
                self.marca(
                    "OECD-60020", f"AccountType is CRS1103 and AcctNumberType is {tipo_num}.",
                    numero,
                )
        permitidos = {
            "CRS1101": ("OECD-60021", ("CRS502",)),
            "CRS1104": ("OECD-60022", ("CRS503", "CRS504")),
            "CRS1103": ("OECD-60023", ("CRS503", "CRS504")),
        }
        if tipo in permitidos:
            regla, validos = permitidos[tipo]
            for pago in hijos(ar, "Payment"):
                pt = texto(pago, "Type")
                if pt is not None and pt not in validos:
                    self.marca(
                        regla,
                        f"AccountType is {tipo} and the payment Type is {pt} "
                        f"(allowed: {' or '.join(validos)}).",
                        hijo(pago, "Type"),
                    )


def revisa(
    raiz: etree._Element, *, fichero: str, version: str, version_raiz: str, contexto: str,
    hoy: date, vistos: Vistos, contexto_auto: bool = False,
) -> list[Hallazgo]:
    """Todas las reglas de negocio sobre un CRS_OECD ya parseado.

    `version` decide qué reglas aplican y qué guía se cita; `version_raiz` es la que dice
    el espacio de nombres (para UG-VERSION). Robusto ante un documento que no pasa el
    XSD: lo que falta se salta, porque el XSD ya lo ha señalado.
    """
    r = _Revision(raiz, fichero, version, contexto, hoy, vistos, contexto_auto)
    r.cabecera(version_raiz)
    r.docspecs()
    r.cuerpos()
    return r.hallazgos
