"""Lo que rodea al código: esquemas versionados, Action y workflows."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent
ESQUEMAS = RAIZ / "src" / "crs_lint" / "esquemas"


def test_los_xsd_son_los_publicados() -> None:
    """Cada XSD versionado tiene el SHA-256 que dice esquemas/README.md: tocar un esquema
    oficial tiene que verse en el diff de los dos ficheros a la vez."""
    readme = (ESQUEMAS / "README.md").read_text("utf-8")
    por_ruta = {
        ruta: sha for sha, ruta in re.findall(r"`([0-9a-f]{64})`\s*\|\s*`([^`]+)`", readme)
    }
    ficheros = sorted(p.relative_to(ESQUEMAS).as_posix() for p in ESQUEMAS.rglob("*.xsd"))
    assert ficheros == sorted(por_ruta)
    for ruta in ficheros:
        assert hashlib.sha256((ESQUEMAS / ruta).read_bytes()).hexdigest() == por_ruta[ruta]


def test_oecd606_solo_en_v3() -> None:
    v2 = (ESQUEMAS / "2.0" / "CommonTypesFatcaCrs_v2.0.xsd").read_text("utf-8")
    v3 = (ESQUEMAS / "3.0" / "CommonTypesFatcaCrs_v2.0.xsd").read_text("utf-8")
    assert "OECD606" not in v2
    assert "OECD606" in v3


def _yaml(ruta: Path) -> Any:
    return yaml.safe_load(ruta.read_text("utf-8"))


def _usos(nodo: Any) -> list[str]:
    if isinstance(nodo, dict):
        return [v for k, v in nodo.items() if k == "uses"] + [
            u for v in nodo.values() for u in _usos(v)
        ]
    if isinstance(nodo, list):
        return [u for v in nodo for u in _usos(v)]
    return []


def test_actions_fijadas_por_sha() -> None:
    rutas = [RAIZ / "action.yml", *sorted((RAIZ / ".github" / "workflows").glob("*.yml"))]
    usos = [u for r in rutas for u in _usos(_yaml(r))]
    assert usos
    for uso in usos:
        if uso.startswith("./"):
            continue
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", uso), uso


def test_la_action_se_instala_desde_su_propio_codigo() -> None:
    accion = _yaml(RAIZ / "action.yml")
    pasos = accion["runs"]["steps"]
    assert any("github.action_path" in str(p.get("run", "")) for p in pasos)
    assert not any("pip install crs-lint" in str(p.get("run", "")) for p in pasos)


def test_ci_en_tres_sistemas_y_cuatro_pythons() -> None:
    ci = _yaml(RAIZ / ".github" / "workflows" / "ci.yml")
    matriz = ci["jobs"]["tests"]["strategy"]["matrix"]
    assert set(matriz["os"]) == {"ubuntu-latest", "macos-latest", "windows-latest"}
    assert matriz["python"] == ["3.11", "3.12", "3.13", "3.14"]


def test_una_etiqueta_en_rojo_no_se_publica() -> None:
    release = _yaml(RAIZ / ".github" / "workflows" / "release.yml")
    trabajos = release["jobs"]
    assert trabajos["build"]["needs"] == "tests"
    pasos = " ".join(str(p.get("run", "")) for p in trabajos["tests"]["steps"])
    assert "pytest" in pasos and "ruff" in pasos and "mypy" in pasos


def test_pypi_condicionado_a_trusted_publisher() -> None:
    release = _yaml(RAIZ / ".github" / "workflows" / "release.yml")
    pasos = release["jobs"]["publish"]["steps"]
    pypi = [p for p in pasos if "pypi-publish" in str(p.get("uses", ""))]
    assert len(pypi) == 1
    assert "PYPI_TRUSTED_PUBLISHER" in pypi[0]["if"]
