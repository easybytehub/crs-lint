"""La CLI: códigos de salida, formatos y los caminos en que la herramienta no puede trabajar."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import crs_lint.cli
from crs_lint import __version__
from crs_lint.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"
VALIDO = FIXTURES / "valid-3.0.xml"


def _json(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, dict[str, Any]]:
    codigo = main([*args, "--format", "json"])
    salida = capsys.readouterr().out
    return codigo, (json.loads(salida) if salida.strip() else {})


def _reglas(datos: dict[str, Any]) -> list[str]:
    return sorted(h["rule"] for h in datos["findings"])


def test_valido_sale_con_cero(capsys: pytest.CaptureFixture[str]) -> None:
    codigo, datos = _json(capsys, str(VALIDO))
    assert codigo == 0
    assert datos["findings"] == []
    assert datos["files"] == [
        {"path": str(VALIDO), "schema_version": "3.0", "context": "exchange"}
    ]


def test_sin_ficheros_sale_con_dos(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "at least one" in capsys.readouterr().err


def test_fichero_inexistente_no_aborta_el_resto(capsys: pytest.CaptureFixture[str]) -> None:
    codigo, datos = _json(capsys, "no-such-file.xml", str(FIXTURES / "60002-negative-balance.xml"))
    assert codigo == 2
    assert _reglas(datos) == ["FMT-003", "OECD-60002"]


@pytest.mark.parametrize("codificacion", ["utf-8", "utf-16"])
def test_doctype_se_rechaza(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], codificacion: str
) -> None:
    risa = (
        f'<?xml version="1.0" encoding="{codificacion.upper()}"?>\n'
        '<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>\n'
        "<lolz>&lol2;</lolz>"
    )
    f = tmp_path / "bomb.xml"
    f.write_bytes(risa.encode(codificacion))
    codigo, datos = _json(capsys, str(f))
    assert codigo == 2
    assert _reglas(datos) == ["FMT-002"]


def test_doctype_tras_un_prologo_largo_tambien_se_rechaza(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "late.xml"
    f.write_text("<!--" + "x" * 9000 + '-->\n<!DOCTYPE x [<!ENTITY a "b">]>\n<x>&a;</x>')
    codigo, datos = _json(capsys, str(f))
    assert codigo == 2
    assert _reglas(datos) == ["FMT-002"]


def test_xml_mal_formado_es_un_50007(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "roto.xml"
    f.write_text('<crs:CRS_OECD xmlns:crs="urn:oecd:ties:crs:v3">\n<a>\n</crs:CRS_OECD>')
    codigo, datos = _json(capsys, str(f))
    assert codigo == 1
    assert _reglas(datos) == ["OECD-50007"]
    assert datos["findings"][0]["line"] == 3


def test_raiz_que_no_es_crs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "otro.xml"
    f.write_text("<factura/>")
    codigo, datos = _json(capsys, str(f))
    assert codigo == 2
    assert _reglas(datos) == ["FMT-001"]


def test_el_sobre_de_la_aeat_se_reconoce(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "m289.xml"
    f.write_text('<p:Presentation xmlns:p="urn:aeat:crsdac2:present:v20"/>')
    codigo, datos = _json(capsys, str(f))
    assert codigo == 2
    assert "modelo 289" in datos["findings"][0]["detail"]


def test_version_fijada_que_no_coincide_es_error(capsys: pytest.CaptureFixture[str]) -> None:
    codigo, datos = _json(capsys, str(FIXTURES / "valid-2.0.xml"), "--schema-version", "3.0")
    assert codigo == 1
    assert _reglas(datos) == ["OECD-50007"]
    assert "--schema-version 3.0" in datos["findings"][0]["detail"]


def test_version_fijada_que_coincide(capsys: pytest.CaptureFixture[str]) -> None:
    codigo, _ = _json(capsys, str(FIXTURES / "valid-2.0.xml"), "--schema-version", "2.0")
    assert codigo == 0


def test_strict_hace_fallar_los_avisos(capsys: pytest.CaptureFixture[str]) -> None:
    f = str(FIXTURES / "50010-test-data.xml")
    assert _json(capsys, f)[0] == 0
    assert _json(capsys, f, "--strict")[0] == 1


def test_contexto_forzado(capsys: pytest.CaptureFixture[str]) -> None:
    nacional = str(FIXTURES / "valid-domestic-3.0.xml")
    codigo, datos = _json(capsys, nacional)
    assert (codigo, _reglas(datos)) == (0, ["CTX-DOMESTIC"])
    # Explícito: quien lo pide ya sabe que es nacional, no hace falta decírselo.
    codigo, datos = _json(capsys, nacional, "--context", "domestic")
    assert (codigo, _reglas(datos)) == (0, [])
    codigo, datos = _json(capsys, nacional, "--context", "exchange")
    assert codigo == 1
    # Titulares alemanes en un «intercambio» hacia ES: 60011 por cada persona (tres
    # titulares y una persona de control) y 60012 por la entidad.
    assert _reglas(datos) == ["OECD-50008", "OECD-50012", "OECD-60011", "OECD-60011",
                              "OECD-60011", "OECD-60011", "OECD-60012"]
    severidad = {h["rule"]: h["severity"] for h in datos["findings"]}
    assert severidad["OECD-50012"] == "warning"
    codigo, datos = _json(capsys, str(FIXTURES / "60011-person-rescountry.xml"), "--context",
                          "domestic")
    assert codigo == 0


def test_identificadores_repetidos_entre_ficheros(capsys: pytest.CaptureFixture[str]) -> None:
    codigo, datos = _json(capsys, str(VALIDO), str(FIXTURES / "50009-same-messagerefid.xml"))
    assert codigo == 1
    assert _reglas(datos) == ["OECD-50009"]
    codigo, datos = _json(capsys, str(VALIDO), str(FIXTURES / "50007-schema.xml"))
    # Mismo MessageRefId y mismos DocRefId: 50009 una vez, 80000 por cada registro.
    assert "OECD-50009" in _reglas(datos)
    assert _reglas(datos).count("OECD-80000") == 5


def test_el_reporting_fi_reenviado_conserva_su_docrefid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """OECD0 reutiliza el DocRefId del envío original (así lo muestran los ejemplos de la
    guía): no es un 80000 aunque los dos mensajes vayan en la misma ejecución."""
    correccion = (FIXTURES / "80005-missing-corrdocrefid.xml").read_text("utf-8")
    correccion = correccion.replace("<stf:DocRefId>ESAR2026C001</stf:DocRefId>",
                                    "<stf:DocRefId>ESAR2026C001</stf:DocRefId>"
                                    "<stf:CorrDocRefId>ESAR20260001</stf:CorrDocRefId>")
    f = tmp_path / "correction.xml"
    f.write_text(correccion, "utf-8")
    codigo, datos = _json(capsys, str(VALIDO), str(f))
    assert _reglas(datos) == []
    assert codigo == 0


def test_el_mismo_fichero_dos_veces_no_es_un_duplicado(capsys: pytest.CaptureFixture[str]) -> None:
    codigo, datos = _json(capsys, str(VALIDO), str(VALIDO))
    assert codigo == 0
    assert len(datos["files"]) == 1


def test_fallo_interno_sale_con_dos_en_una_linea(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def explota(_: Path) -> None:
        raise RuntimeError("boom\nsecond line")

    monkeypatch.setattr(crs_lint.cli, "lee", explota)
    assert main([str(VALIDO)]) == 2
    err = capsys.readouterr().err
    assert err.strip() == "crs-lint: internal error: RuntimeError: boom"


def test_ctx_domestic_sale_en_los_tres_formatos(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    nacional = str(FIXTURES / "valid-domestic-3.0.xml")
    assert main([nacional, "--no-color"]) == 0
    assert "TC=RC=ES: treated as domestic" in capsys.readouterr().out
    _, datos = _json(capsys, nacional)
    assert datos["findings"][0]["detail"].startswith("TC=RC=ES: treated as domestic")
    monkeypatch.chdir(FIXTURES.parent.parent)
    main([nacional, "--format", "sarif"])
    sarif = json.loads(capsys.readouterr().out)
    resultado = sarif["runs"][0]["results"][0]
    assert (resultado["ruleId"], resultado["level"]) == ("CTX-DOMESTIC", "warning")


def test_sarif_codifica_la_uri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    carpeta = tmp_path / "real cases"
    carpeta.mkdir()
    f = carpeta / "01 new #1.xml"
    f.write_bytes((FIXTURES / "60002-negative-balance.xml").read_bytes())
    monkeypatch.chdir(tmp_path)
    main(["real cases/01 new #1.xml", "--format", "sarif"])
    uri = json.loads(capsys.readouterr().out)["runs"][0]["results"][0]["locations"][0][
        "physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "real%20cases/01%20new%20%231.xml"


def test_el_aviso_legal_solo_sin_errores(capsys: pytest.CaptureFixture[str]) -> None:
    main([str(FIXTURES / "60002-negative-balance.xml"), "--no-color"])
    assert "Zero errors means" not in capsys.readouterr().out
    main([str(VALIDO), "--no-color"])
    assert "Zero errors means" in capsys.readouterr().out
    _, datos = _json(capsys, str(FIXTURES / "60002-negative-balance.xml"))
    assert datos["notice"] is None


def test_sarif_con_ruta_relativa_y_linea(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(FIXTURES.parent.parent)
    codigo = main([str(FIXTURES / "60014-birthdate.xml"), "--format", "sarif"])
    sarif = json.loads(capsys.readouterr().out)
    assert codigo == 1
    resultado = sarif["runs"][0]["results"][0]
    ubicacion = resultado["locations"][0]["physicalLocation"]
    assert ubicacion["artifactLocation"]["uri"] == "tests/fixtures/60014-birthdate.xml"
    assert ubicacion["region"]["startLine"] > 1
    assert resultado["ruleId"] == "OECD-60014"
    assert sarif["runs"][0]["tool"]["driver"]["rules"][0]["properties"]["oecd_codes"] == ["60014"]


def test_texto_cita_codigo_y_fuente(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(FIXTURES / "60017-emoney-not-depository.xml"), "--no-color"]) == 1
    salida = capsys.readouterr().out
    assert "OECD-60017 (60017)" in salida
    assert "must be a Depository Account (AccountType is CRS1101)" in salida
    assert "PDF p. 31" in salida


def test_v2_cita_la_status_message_de_2019(capsys: pytest.CaptureFixture[str]) -> None:
    _, datos = _json(capsys, str(FIXTURES / "v2-60000-iban.xml"))
    assert "Version 2.0 – June 2019, PDF p. 35" in datos["findings"][0]["citation"]


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as salida:
        main(["--version"])
    assert salida.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_ejecutable_como_modulo_con_salida_redirigida() -> None:
    """Un proceso real con la salida en una tubería: en Windows es donde la página de
    códigos ANSI rompía los caracteres no ASCII."""
    p = subprocess.run(
        [sys.executable, "-m", "crs_lint", str(FIXTURES / "60013-fi-rescountry.xml"),
         "--no-color"],
        capture_output=True, check=False,
    )
    assert p.returncode == 1
    assert "crs-lint · 1 file" in p.stdout.decode("utf-8")
