"""Regresión de la revisión adversarial de 0.1: los ficheros del revisor, tal cual.

`review/real cases/` son mensajes CRS v3.0 sintéticos que imitan casos reales (alta,
corrección, borrado, nil, nacional, un intercambio mal etiquetado…); `review/rob/` son
ficheros hostiles o rotos. El nombre con espacios es a propósito: también prueba SARIF.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from crs_lint.cli import main

REVISION = Path(__file__).resolve().parent / "fixtures" / "review"
CASOS = REVISION / "real cases"
ROB = REVISION / "rob"

# fichero → (código de salida, reglas:severidad ordenadas)
ESPERADO: dict[str, tuple[int, list[str]]] = {
    "real cases/01 new.xml": (0, []),
    "real cases/02 correction.xml": (0, []),
    "real cases/03 deletion.xml": (0, []),
    # CrsBody sin ReportingGroup: el XSD v3.0 exige al menos uno (puede ir vacío).
    "real cases/04 rfi-only-correction.xml": (1, ["OECD-50007:error"]),
    "real cases/05 late-account.xml": (0, []),
    "real cases/06 nil.xml": (0, []),
    "real cases/07 domestic sg.xml": (
        0, ["CTX-DOMESTIC:warning", "OECD-80001:warning", "OECD-80001:warning"]
    ),
    "real cases/08 rc-bug.xml": (
        0, ["CTX-DOMESTIC:warning", "OECD-80001:warning", "OECD-80001:warning"]
    ),
    "real cases/n1 cp-other.xml": (1, ["OECD-60011:error"]),
    "real cases/n2 702-new-only.xml": (1, ["OECD-80010:error"]),
    "real cases/n3 test-data.xml": (0, ["OECD-50010:warning"]),
    "real cases/n4 delete-fi-correct-ar.xml": (1, ["OECD-80009:error"]),
    # CRS703 con CrsBody entre autoridades: la UG dice que el CrsBody «will be omitted»,
    # pero ningún código de la Status Message lo recoge (80015 es la regla inversa).
    "real cases/n5 703-with-body.xml": (0, []),
    "rob/bom.xml": (0, []),
    "rob/latin1.xml": (0, []),
    "rob/utf16.xml": (0, []),
    "rob/utf32.xml": (0, []),
    "rob/pi-xsl.xml": (0, []),  # la instrucción de proceso no se sigue
    "rob/xinclude.xml": (1, ["OECD-50007:error", "OECD-50007:error"]),  # no se expande
    "rob/comment-doctype.xml": (2, ["FMT-002:error"]),
    "rob/utf16-doctype.xml": (2, ["FMT-002:error"]),
    "rob/xxe.xml": (2, ["FMT-002:error"]),
    "rob/nons.xml": (2, ["FMT-001:error"]),
    "rob/empty.xml": (1, ["OECD-50007:error"]),
    "rob/garbage.xml": (1, ["OECD-50007:error"]),
    "rob/truncated.xml": (1, ["OECD-50007:error"]),
    "rob/wrongenc.xml": (1, ["OECD-50007:error"]),
}


def _corre(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, list[str]]:
    codigo = main([*args, "--format", "json"])
    datos = json.loads(capsys.readouterr().out)
    return codigo, sorted(f"{h['rule']}:{h['severity']}" for h in datos["findings"])


@pytest.mark.parametrize("nombre", sorted(ESPERADO))
def test_fichero_del_revisor(nombre: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert _corre(capsys, str(REVISION / nombre)) == ESPERADO[nombre]


def test_estan_todos() -> None:
    presentes = {p.relative_to(REVISION).as_posix() for p in REVISION.rglob("*.xml")}
    assert presentes == set(ESPERADO)


def test_intercambio_mal_etiquetado_no_pasa_en_strict(capsys: pytest.CaptureFixture[str]) -> None:
    fichero = str(CASOS / "08 rc-bug.xml")
    assert _corre(capsys, fichero, "--strict")[0] == 1
    codigo, reglas = _corre(capsys, fichero, "--context", "exchange")
    assert codigo == 1
    assert reglas == [
        "OECD-50008:error", "OECD-50012:warning", "OECD-60011:error", "OECD-80001:error",
        "OECD-80001:error",
    ]


def test_la_serie_completa_en_una_ejecucion(capsys: pytest.CaptureFixture[str]) -> None:
    """Alta, corrección, borrado y alta tardía juntos: ningún 50009/80000 falso (el RFI
    reenviado con OECD0 conserva su DocRefId)."""
    nombres = ["01 new", "02 correction", "03 deletion", "05 late-account"]
    codigo, reglas = _corre(capsys, *(str(CASOS / f"{n}.xml") for n in nombres))
    assert (codigo, reglas) == (0, [])


def test_un_directorio_no_es_un_fichero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _corre(capsys, str(tmp_path)) == (2, ["FMT-003:error"])


@pytest.mark.skipif(
    sys.platform == "win32",
    reason=(
        "The libxml2 bundled with lxml on Windows reports a >10 MB text node differently: "
        "the file is still rejected, but as OECD 50007 instead of TOOL-001 (known limitation)."
    ),
)
def test_texto_enorme_es_limite_de_la_herramienta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plantilla = (CASOS / "01 new.xml").read_text("utf-8")
    enorme = plantilla.replace("<crs:Name>Bank</crs:Name>",
                               f"<crs:Name>{'x' * 10_500_000}</crs:Name>", 1)
    f = tmp_path / "bigtext.xml"
    f.write_text(enorme, "utf-8")
    assert _corre(capsys, str(f)) == (2, ["TOOL-001:error"])
