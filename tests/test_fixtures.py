"""Cada fixture dice exactamente lo que tiene que decir: ni una regla de más ni de menos."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from crs_lint.cli import main
from crs_lint.documento import esquema, lee, valida_xsd

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
ESPERADOS: dict[str, list[str]] = json.loads((FIXTURES / "expected.json").read_text("utf-8"))


def _generador() -> ModuleType:
    script = RAIZ / "scripts" / "generar-fixtures.py"
    spec = importlib.util.spec_from_file_location("generar", script)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.mark.parametrize("nombre", sorted(ESPERADOS))
def test_cada_fixture_dispara_solo_su_regla(
    nombre: str, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo = main([str(FIXTURES / nombre), "--format", "json"])
    datos = json.loads(capsys.readouterr().out)
    reglas = sorted({h["rule"] for h in datos["findings"]})
    assert reglas == ESPERADOS[nombre]
    errores = datos["summary"]["errors"]
    assert codigo == (1 if errores else 0)


@pytest.mark.parametrize("nombre", sorted(n for n, r in ESPERADOS.items() if "OECD-50007" not in r))
def test_las_fixtures_son_validas_contra_el_xsd_oficial(nombre: str) -> None:
    """Las reglas de negocio se prueban sobre XML que el XSD acepta: si no, el fallo que
    se ve podría ser del esquema y no de la regla."""
    doc = lee(FIXTURES / nombre)
    errores, total = valida_xsd(doc, doc.version_detectada)
    assert total == 0, errores


def test_hay_una_fixture_por_regla_implementada() -> None:
    from crs_lint.catalogo import REGLAS

    # 50009 (dos ficheros) y 50012 (--context exchange) se prueban en test_cli.py;
    # TOOL-001 (10 MB de texto) en test_revision.py.
    cubiertas = {r for reglas in ESPERADOS.values() for r in reglas} | {"OECD-50009",
                                                                        "OECD-50012"}
    implementadas = {r for r in REGLAS if not r.startswith(("FMT-", "TOOL-"))}
    assert implementadas == cubiertas


def test_las_fixtures_versionadas_son_las_que_genera_el_script(tmp_path: Path) -> None:
    _generador().genera(tmp_path)
    generados = sorted(p.name for p in tmp_path.iterdir())
    versionados = sorted(p.name for p in FIXTURES.iterdir() if p.suffix in (".xml", ".json"))
    assert generados == versionados
    for nombre in generados:
        assert (tmp_path / nombre).read_bytes() == (FIXTURES / nombre).read_bytes(), nombre


def test_los_dos_esquemas_compilan_por_separado() -> None:
    assert esquema("2.0") is not esquema("3.0")
