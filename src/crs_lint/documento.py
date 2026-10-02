"""Leer un fichero CRS sin abrirle la puerta a nada, y validarlo contra el XSD oficial.

**El parseo es seguro por dos capas, no por una.** La primera es la de `verifactu-lint`:
antes de parsear se busca un DOCTYPE en el prólogo y, si lo hay, el fichero se rechaza.
Un mensaje CRS no declara entidades jamás, así que rechazar todo DOCTYPE no pierde ningún
fichero legítimo y cierra el *billion laughs* sin depender de internos del parser. La
segunda es el propio parser de lxml, configurado sin DTD, sin resolver entidades y sin
red: aunque la primera capa fallara, libxml2 no iría a buscar nada fuera.

**Los XSD van dentro del paquete y se cargan del disco**, con el mismo parser sin red.
Son copias literales de los que publica IRAS (ver `esquemas/README.md`), en un
directorio por versión: los dos paquetes traen un `CommonTypesFatcaCrs_v2.0.xsd` con el
mismo nombre y distinto contenido (el de la v3.0 añade OECD606), así que mezclarlos
validaría mal.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, cast

from lxml import etree

NS_CRS = {"urn:oecd:ties:crs:v2": "2.0", "urn:oecd:ties:crs:v3": "3.0"}
NS_POR_VERSION = {v: k for k, v in NS_CRS.items()}
RAIZ = "CRS_OECD"
XSD_PRINCIPAL = {"2.0": "CrsXML_v2.0.xsd", "3.0": "CrsXML_v3.0.xsd"}

# Raíces conocidas que no son un mensaje CRS de la OCDE pero lo envuelven: se reconocen
# para decir algo útil en vez de «no es CRS».
ENVOLTORIOS = {
    "urn:aeat:crsdac2:present:v20": (
        "This is the AEAT (Spain, modelo 289) presentation envelope, which wraps a CRS v2.0 "
        "message. National profiles are on the roadmap; for now, lint the CRS_OECD element "
        "on its own."
    ),
}

# La declaración de tipo de documento sólo puede ir en el prólogo, antes de la raíz.
_PROLOGO = 8192
MAX_ERRORES_XSD = 50


class Rechazado(Exception):
    """El documento no se procesa (DOCTYPE): ver FMT-002."""


class MalFormado(Exception):
    """No es XML bien formado. Es un hallazgo (50007), no un fallo de la herramienta."""

    def __init__(self, mensaje: str, linea: int) -> None:
        super().__init__(mensaje)
        self.linea = linea


class LimiteDeRecursos(Exception):
    """El parser se ha parado por un límite propio (sin XML_PARSE_HUGE): TOOL-001.

    No es un 50007: el fichero puede ser perfectamente válido; es esta herramienta la que
    no lo ha podido leer entero, y eso es la salida 2.
    """

    def __init__(self, mensaje: str, linea: int) -> None:
        super().__init__(mensaje)
        self.linea = linea


class NoEsCrs(Exception):
    """XML bien formado, pero no un CRS_OECD de la OCDE: ver FMT-001."""


@dataclass
class Documento:
    ruta: str
    raiz: etree._Element
    version_detectada: str
    """La versión que dice el espacio de nombres de la raíz."""


def _parser(*, huge_tree: bool = False) -> etree.XMLParser:
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=huge_tree,
        remove_comments=False,
    )


def _fallo_por_limite(crudo: bytes) -> bool:
    """¿El fallo de parseo era nuestro límite de tamaño y no un XML mal formado?

    libxml2 no lo informa igual en todas las plataformas: en el CI de Windows, lxml no devolvía
    ERR_RESOURCE_LIMIT ni mencionaba XML_PARSE_HUGE para un nodo de texto de más de 10 MB, y
    el fichero acababa como 50007. En vez de adivinar mensajes, se reintenta SOLO para
    clasificar, quitando únicamente los límites de tamaño: las entidades, la red y la DTD
    siguen desactivadas, y el DOCTYPE ya se ha rechazado antes, así que no abre ningún vector.
    """
    try:
        etree.fromstring(crudo, parser=_parser(huge_tree=True))
    except etree.XMLSyntaxError:
        return False
    return True


def _rechaza_doctype(crudo: bytes) -> None:
    """Busca un DOCTYPE en el prólogo en latin-1 y en UTF-16 (LE y BE).

    En latin-1 se ve el DOCTYPE de cualquier codificación compatible con ASCII; en UTF-16,
    el de las otras dos que libxml2 detecta por el BOM o por los primeros bytes. Mirar
    sólo una lectura dejaría pasar un *billion laughs* escrito en UTF-16.
    """
    inicio = crudo[:_PROLOGO]
    lecturas = (
        inicio.decode("latin-1"),
        inicio.decode("utf-16-le", errors="ignore"),
        inicio.decode("utf-16-be", errors="ignore"),
    )
    if any("<!DOCTYPE" in t for t in lecturas):
        raise Rechazado("The document declares a DOCTYPE")


def lee(ruta: Path) -> Documento:
    """Lee y parsea. `OSError` si no se puede leer; las demás excepciones, arriba."""
    crudo = ruta.read_bytes()
    _rechaza_doctype(crudo)
    try:
        raiz = etree.fromstring(crudo, parser=_parser())
    except etree.XMLSyntaxError as exc:
        linea = exc.lineno or 0
        mensaje = str(exc.msg or exc).splitlines()[0]
        codigo = cast(Any, exc).code  # lxml-stubs no declara `code`
        if (
            codigo == etree.ErrorTypes.ERR_RESOURCE_LIMIT
            or "XML_PARSE_HUGE" in mensaje
            or _fallo_por_limite(crudo)
        ):
            raise LimiteDeRecursos(mensaje, linea) from None
        raise MalFormado(mensaje, linea) from None
    # Segunda red: un DOCTYPE detrás de un comentario de más de 8 KiB no lo ve el
    # prólogo, pero sí el árbol (parseado ya sin DTD, sin entidades y sin red).
    if cast(Any, raiz.getroottree().docinfo).doctype:  # lxml-stubs no declara doctype
        raise Rechazado("The document declares a DOCTYPE")
    nombre = etree.QName(raiz)
    if nombre.namespace in ENVOLTORIOS:
        raise NoEsCrs(ENVOLTORIOS[nombre.namespace])
    if nombre.localname != RAIZ or nombre.namespace not in NS_CRS:
        raise NoEsCrs(
            f"The root element is {{{nombre.namespace or ''}}}{nombre.localname}; expected "
            f"{RAIZ} in urn:oecd:ties:crs:v2 or urn:oecd:ties:crs:v3"
        )
    return Documento(str(ruta), raiz, NS_CRS[nombre.namespace])


@functools.cache
def esquema(version: str) -> etree.XMLSchema:
    """El XSD oficial de la versión, compilado una sola vez por proceso."""
    paquete = resources.files("crs_lint") / "esquemas" / version / XSD_PRINCIPAL[version]
    with resources.as_file(paquete) as ruta:
        arbol = etree.parse(str(ruta), parser=_parser())
        return etree.XMLSchema(arbol)


@dataclass(frozen=True)
class ErrorXsd:
    linea: int
    mensaje: str


def valida_xsd(doc: Documento, version: str) -> tuple[list[ErrorXsd], int]:
    """Errores de esquema (como mucho `MAX_ERRORES_XSD`) y el total."""
    xsd = esquema(version)
    if xsd.validate(doc.raiz):
        return [], 0
    entradas: list[Any] = list(cast(Any, xsd.error_log))
    errores = [ErrorXsd(int(e.line or 0), str(e.message)) for e in entradas]
    return errores[:MAX_ERRORES_XSD], len(errores)
