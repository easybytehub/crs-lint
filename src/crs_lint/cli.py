"""La interfaz de línea de comandos (en inglés: es para un público global).

**El código de salida es la parte que importa.** `1` cuando hay errores, `0` cuando no,
`2` cuando la herramienta no ha podido hacer su trabajo (fichero que no se lee, DTD
rechazada, raíz que no es CRS, fallo interno). Un XML mal formado no es un 2: es un
hallazgo (50007), porque es exactamente lo que la administración devolvería.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from crs_lint import __version__
from crs_lint.catalogo import REGLAS
from crs_lint.documento import (
    MAX_ERRORES_XSD,
    LimiteDeRecursos,
    MalFormado,
    NoEsCrs,
    Rechazado,
    lee,
    valida_xsd,
)
from crs_lint.hallazgos import Hallazgo, Informe
from crs_lint.reglas import Vistos, contexto_de, linea_de, revisa
from crs_lint.salida import como_json, como_sarif, texto

EPILOGO = """\
crs-lint checks OECD Common Reporting Standard XML files (CRS_OECD, schema v2.0 and
v3.0) against the official XSD and against the record and file rules of the OECD CRS
Status Message User Guide that can be decided from the file itself. Every finding
cites the OECD error code the receiving administration would return (5xxxx, 6xxxx,
8xxxx) and the literal rule.

Context: 'exchange' is a message between Competent Authorities; 'domestic' is a
Financial Institution reporting to its own administration (the OECD User Guide: "[For
domestic reporting this element would be the domestic Country Code.]"). In domestic
files 50008, 60011 and 60012 are not applied and 80001 is only a warning. When the
context is detected rather than given, the report says so (CTX-DOMESTIC).

Not checked: anything that needs the receiver's records (a DocRefID or MessageRefID
used in an earlier submission, an unknown CorrDocRefId) and national TIN rules. It
never goes to the network.

Exit codes: 0 no errors; 1 errors (or warnings with --strict); 2 the tool could not do
its job. A clean result does not mean the administration will accept the file.
"""


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="crs-lint",
        description="Lint OECD CRS XML files (schema v2.0 and v3.0) against the XSD and the "
        "OECD Status Message rules.",
        epilog=EPILOGO,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("files", nargs="*", type=Path, help="CRS XML files (root CRS_OECD)")
    p.add_argument(
        "--schema-version",
        choices=("auto", "2.0", "3.0"),
        default="auto",
        help="schema to check against; 'auto' (default) reads it from the root namespace. "
        "A fixed version also asserts it: a file in the other version is an error",
    )
    p.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    p.add_argument("--strict", action="store_true", help="exit with 1 on warnings too")
    p.add_argument(
        "--context",
        choices=("auto", "exchange", "domestic"),
        default="auto",
        help="'auto' (default): domestic when TransmittingCountry equals ReceivingCountry",
    )
    p.add_argument("--no-color", action="store_true", help="disable colour")
    p.add_argument("--version", action="version", version=f"crs-lint {__version__}")
    return p.parse_args(argv)


def _error(msg: str) -> int:
    print(f"crs-lint: {msg}", file=sys.stderr)
    return 2


def _salida_utf8() -> None:
    # On Windows, redirected output (CI logs, pipes, files) uses the ANSI code page, which
    # has no '·' or '→': print() would raise UnicodeEncodeError and the tool would exit 2 on
    # a valid run. Force UTF-8 on both streams when the runtime allows it.
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            try:
                reconfigurar(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _salida_utf8()
    args = _argumentos(argv)
    try:
        return _ejecuta(args)
    except Exception as exc:  # red de seguridad: nunca una traza en CI
        # Un fallo interno no es un hallazgo: es la herramienta que no ha podido hacer su
        # trabajo, y eso es la salida 2, con una línea que se pueda pegar en un issue.
        return _error(f"internal error: {type(exc).__name__}: {exc}".splitlines()[0])


def _ejecuta(args: argparse.Namespace) -> int:
    if not args.files:
        return _error("give at least one CRS XML file")

    rutas: list[Path] = []
    vistas: set[Path] = set()
    for ruta in args.files:
        clave = ruta.resolve()
        if clave not in vistas:  # un glob que repite fichero no es un MessageRefId repetido
            vistas.add(clave)
            rutas.append(ruta)

    hallazgos: list[Hallazgo] = []
    versiones: dict[str, str] = {}
    contextos: dict[str, str] = {}
    no_procesados: list[str] = []
    vistos = Vistos()
    hoy = date.today()

    for ruta in rutas:
        fichero = str(ruta)
        version_fija = None if args.schema_version == "auto" else args.schema_version
        if not ruta.is_file():
            no_procesados.append(fichero)
            hallazgos.append(
                REGLAS["FMT-003"].hallazgo(
                    "Does not exist or is not a regular file.", version="3.0", fichero=fichero
                )
            )
            continue
        try:
            doc = lee(ruta)
        except OSError as exc:
            no_procesados.append(fichero)
            hallazgos.append(
                REGLAS["FMT-003"].hallazgo(
                    f"{exc.strerror or exc}.", version="3.0", fichero=fichero
                )
            )
            continue
        except Rechazado as exc:
            no_procesados.append(fichero)
            hallazgos.append(
                REGLAS["FMT-002"].hallazgo(f"{exc}.", version="3.0", fichero=fichero)
            )
            continue
        except LimiteDeRecursos as exc:
            no_procesados.append(fichero)
            hallazgos.append(
                REGLAS["TOOL-001"].hallazgo(
                    f"{exc}", version="3.0", fichero=fichero, linea=exc.linea
                )
            )
            continue
        except NoEsCrs as exc:
            no_procesados.append(fichero)
            hallazgos.append(
                REGLAS["FMT-001"].hallazgo(f"{exc}.", version="3.0", fichero=fichero)
            )
            continue
        except MalFormado as exc:
            version = version_fija or "3.0"
            versiones[fichero] = version
            contextos[fichero] = "-"
            hallazgos.append(
                REGLAS["OECD-50007"].hallazgo(
                    f"Not well-formed XML: {exc}", version=version, fichero=fichero,
                    linea=exc.linea,
                )
            )
            continue

        version = doc.version_detectada
        versiones[fichero] = version
        if version_fija is not None and version_fija != version:
            hallazgos.append(
                REGLAS["OECD-50007"].hallazgo(
                    f"--schema-version {version_fija} was required, but the root namespace "
                    f"is that of schema {version}.",
                    version=version_fija, fichero=fichero, linea=linea_de(doc.raiz),
                )
            )
        errores, total = valida_xsd(doc, version)
        for e in errores:
            hallazgos.append(
                REGLAS["OECD-50007"].hallazgo(
                    e.mensaje, version=version, fichero=fichero, linea=e.linea
                )
            )
        if total > MAX_ERRORES_XSD:
            hallazgos.append(
                REGLAS["OECD-50007"].hallazgo(
                    f"... and {total - MAX_ERRORES_XSD} more schema errors not listed.",
                    version=version, fichero=fichero,
                )
            )
        contexto = contexto_de(doc.raiz, args.context)
        contextos[fichero] = contexto
        hallazgos += revisa(
            doc.raiz, fichero=fichero, version=version, version_raiz=doc.version_detectada,
            contexto=contexto, hoy=hoy, vistos=vistos,
            contexto_auto=args.context == "auto",
        )

    informe = Informe(
        hallazgos=hallazgos,
        ficheros=[str(r) for r in rutas],
        versiones=versiones,
        contextos=contextos,
    )
    if args.format == "json":
        print(como_json(informe))
    elif args.format == "sarif":
        print(como_sarif(informe, __version__))
    else:
        print(texto(informe, color=not args.no_color and sys.stdout.isatty()))

    if no_procesados:
        return _error(f"could not check: {', '.join(no_procesados)}")
    if informe.errores or (args.strict and informe.avisos):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
