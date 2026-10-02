"""Cómo se presenta el informe: texto, JSON y SARIF (todo en inglés).

SARIF no está por completismo: es lo que GitHub ingiere en la pestaña Security, y aquí
cada resultado lleva la línea del XML donde está el problema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from crs_lint.catalogo import REGLAS
from crs_lint.hallazgos import Informe, Severidad

_NIVEL_SARIF = {
    Severidad.ERROR: "error",
    Severidad.AVISO: "warning",
    Severidad.INCOMPLETO: "note",
}
AVISO_LEGAL = (
    "Zero errors means these rules found nothing; it does not mean the administration will "
    "accept the file. Checks that need the receiver's records (earlier submissions, TIN "
    "registers) were not run."
)


def _plural(n: int, s: str, p: str) -> str:
    return f"{n} {s if n == 1 else p}"


def texto(informe: Informe, color: bool = True) -> str:
    rojo, amarillo, azul, gris, fin = (
        ("\033[31m", "\033[33m", "\033[34m", "\033[90m", "\033[0m") if color else ("",) * 5
    )
    tinte = {Severidad.ERROR: rojo, Severidad.AVISO: amarillo, Severidad.INCOMPLETO: azul}
    sangria = " " * 13
    lineas = [f"crs-lint · {_plural(len(informe.ficheros), 'file', 'files')}"]
    for f in informe.ficheros:
        v = informe.versiones.get(f)
        c = informe.contextos.get(f)
        if v:
            extra = ""
            if c == "domestic":
                extra = " (50008, 60011, 60012 not applied; 80001 only as a warning)"
            lineas.append(f"  {f}: schema {v} · {c}{extra}")
    lineas.append("")
    varios = len(informe.ficheros) > 1
    if not informe.hallazgos:
        lineas.append("No findings.")
    for h in informe.hallazgos:
        lineas.append(f"{tinte[h.severidad]}{h.linea(con_fichero=varios)}{fin}")
        lineas += [f"{sangria}{d}" for d in h.detalle.splitlines()]
        lineas.append(f"{gris}{sangria}citation: {h.cita}{fin}")
        lineas.append("")
    lineas.append(
        " · ".join(
            (
                _plural(len(informe.errores), "error", "errors"),
                _plural(len(informe.avisos), "warning", "warnings"),
                f"{len(informe.incompletos)} undetermined",
            )
        )
    )
    if not informe.errores:
        # Con errores sobra: decir «cero errores no es aceptación» al lado de un error
        # sólo confunde.
        lineas.append(f"{gris}{AVISO_LEGAL}{fin}")
    return "\n".join(lineas)


def como_json(informe: Informe) -> str:
    datos: dict[str, Any] = {
        "files": [
            {
                "path": f,
                "schema_version": informe.versiones.get(f),
                "context": informe.contextos.get(f),
            }
            for f in informe.ficheros
        ],
        "summary": {
            "errors": len(informe.errores),
            "warnings": len(informe.avisos),
            "undetermined": len(informe.incompletos),
        },
        "findings": [
            {
                "rule": h.regla,
                "oecd_codes": list(h.codigos),
                "severity": h.severidad.value,
                "title": h.titulo,
                "detail": h.detalle,
                "citation": h.cita,
                "file_rejection_basis": REGLAS[h.regla].base_de_rechazo,
                "file": h.fichero,
                "line": h.linea_xml or None,
            }
            for h in informe.hallazgos
        ],
        "notice": None if informe.errores else AVISO_LEGAL,
    }
    return json.dumps(datos, ensure_ascii=False, indent=2)


def _uri(fichero: str) -> str:
    """Relativa al directorio de trabajo (la raíz del checkout en CI, que es lo que GitHub
    sabe anclar); `file://` absoluta si el fichero está fuera de él.

    Codificada como referencia URI (RFC 3986), que es lo que SARIF 2.1.0 exige en `uri`:
    un espacio sin codificar («real cases/01 new.xml») produce un SARIF inválido.
    """
    ruta = Path(fichero)
    if not ruta.is_absolute():
        return quote(ruta.as_posix(), safe="/")
    absoluta = ruta.resolve()  # /var y /private/var son el mismo sitio en macOS
    try:
        return quote(absoluta.relative_to(Path.cwd().resolve()).as_posix(), safe="/")
    except ValueError:
        return absoluta.as_uri()


def como_sarif(informe: Informe, version: str) -> str:
    reglas_vistas: dict[str, dict[str, Any]] = {}
    resultados: list[dict[str, Any]] = []
    for h in informe.hallazgos:
        regla = REGLAS[h.regla]
        descriptor: dict[str, Any] = {
            "id": h.regla,
            "shortDescription": {"text": regla.titulo},
            "fullDescription": {"text": regla.literal},
            "defaultConfiguration": {"level": _NIVEL_SARIF[regla.severidad]},
            "properties": {"oecd_codes": list(regla.codigos)},
        }
        reglas_vistas.setdefault(h.regla, descriptor)
        codigo = f" [{'/'.join(h.codigos)}]" if h.codigos else ""
        resultados.append(
            {
                "ruleId": h.regla,
                "level": _NIVEL_SARIF[h.severidad],
                "message": {"text": f"{h.titulo}{codigo}. {h.detalle}\nCitation: {h.cita}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": _uri(h.fichero)},
                            "region": {"startLine": max(h.linea_xml, 1)},
                        }
                    }
                ],
            }
        )
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "crs-lint",
                        "version": version,
                        "informationUri": "https://github.com/easybytehub/crs-lint",
                        "rules": list(reglas_vistas.values()),
                    }
                },
                "results": resultados,
            }
        ],
    }
    return json.dumps(sarif, ensure_ascii=False, indent=2)
