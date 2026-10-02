"""Reglas sueltas, el catálogo y su sincronía con SPEC.md."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from crs_lint.catalogo import FUERA_DE_ALCANCE, REGLAS
from crs_lint.hallazgos import Severidad
from crs_lint.reglas import Vistos, iban_estado, iban_valido, isin_valido, revisa

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"


@pytest.mark.parametrize(
    ("valor", "valido"),
    [
        ("DE89370400440532013000", True),
        ("DE89 3704 0044 0532 0130 00", True),  # formato de impresión: tolerado
        ("GB82WEST12345698765432", True),
        ("DE89370400440532013001", False),  # dígito de control
        ("DE8937040044", False),  # demasiado corto
        ("1234567890123456", False),
        ("", False),
    ],
)
def test_iban(valor: str, valido: bool) -> None:
    assert iban_valido(valor) is valido


@pytest.mark.parametrize(
    ("valor", "estado"),
    [
        ("DE89370400440532013000", "ok"),
        ("DE89 3704 0044 0532 0130 00", "impresion"),
        ("de89370400440532013000", "impresion"),
        ("DE89 3704 0044 0532 0130 01", "invalido"),
    ],
)
def test_iban_formato_de_impresion(valor: str, estado: str) -> None:
    assert iban_estado(valor) == estado


@pytest.mark.parametrize(
    ("valor", "valido"),
    [
        ("US0378331005", True),
        ("DE000BAY0017", True),
        ("US0378331006", False),
        ("US037833100", False),
        ("0378331005US", False),
    ],
)
def test_isin(valor: str, valido: bool) -> None:
    assert isin_valido(valor) is valido


def _revisa(xml: str, hoy: date = date(2027, 3, 1)) -> list[str]:
    raiz = etree.fromstring(xml.encode())
    hallazgos = revisa(
        raiz, fichero="x.xml", version="3.0", version_raiz="3.0", contexto="exchange",
        hoy=hoy, vistos=Vistos(),
    )
    return [f"{h.regla}:{h.severidad.value}" for h in hallazgos]


def test_fecha_de_nacimiento_posterior_al_anio_en_curso() -> None:
    xml = (FIXTURES / "valid-3.0.xml").read_text("utf-8").replace("1980-05-17", "2028-01-01")
    assert "OECD-60014:error" in _revisa(xml, hoy=date(2027, 12, 31))
    assert "OECD-60014:error" not in _revisa(xml, hoy=date(2028, 1, 1))


def test_60020_sin_tipo_de_numero_es_indeterminado() -> None:
    xml = (FIXTURES / "valid-3.0.xml").read_text("utf-8").replace(
        '<crs:AccountNumber AcctNumberType="OECD605">', "<crs:AccountNumber>"
    )
    assert _revisa(xml) == [f"OECD-60020:{Severidad.INCOMPLETO.value}"]


def test_anio_del_messagerefid_fuera_del_periodo_es_aviso() -> None:
    xml = (FIXTURES / "valid-3.0.xml").read_text("utf-8").replace(
        "ES2026DE0000000001", "ES2019DE0000000001"
    )
    assert _revisa(xml) == ["OECD-50008:warning"]


def test_cierre_con_saldo_cero_no_es_error() -> None:
    xml = (FIXTURES / "60003-closed-with-balance.xml").read_text("utf-8").replace(
        ">1500.00<", ">0.00<"
    )
    assert _revisa(xml) == []


def test_reglas_v3_no_se_aplican_a_v2() -> None:
    assert all(
        REGLAS[r].versiones == ("3.0",)
        for r in ("OECD-60017", "OECD-60018", "OECD-60019", "OECD-60020", "OECD-60021",
                  "OECD-60022", "OECD-60023")
    )


def test_cada_regla_cita_una_pagina_por_version() -> None:
    for regla in REGLAS.values():
        assert regla.literal.strip(), regla.id
        if regla.id.startswith(("OECD-", "UG-")):
            for v in regla.versiones:
                assert re.search(r"PDF p\. \d+$", regla.paginas[v]), (regla.id, v)


def test_los_codigos_coinciden_con_el_id() -> None:
    for regla in REGLAS.values():
        if regla.id.startswith("OECD-"):
            assert regla.id == "OECD-" + "-".join(regla.codigos)


def test_spec_documenta_todas_las_reglas_y_las_descartadas() -> None:
    spec = (RAIZ / "SPEC.md").read_text("utf-8")
    for regla in REGLAS.values():
        assert f"`{regla.id}`" in spec, regla.id
        assert regla.literal in spec, regla.id
    for codigo in FUERA_DE_ALCANCE:
        assert codigo in spec, codigo
