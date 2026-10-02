"""Qué es un hallazgo, y por qué hay tres severidades y no dos.

**`INCOMPLETO` es la severidad que hace honesta a esta herramienta**, igual que en sus
hermanas `verifactu-lint` y `ai-mark-lint`. Un linter de cumplimiento tiene dos formas
de equivocarse y no cuestan lo mismo: callar un error real es malo, y afirmar uno que no
existe es peor, porque quien lo lee cambia un generador correcto y deja de creerse el
resto del informe. Cuando el fichero no basta para decidir, se dice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severidad(StrEnum):
    ERROR = "error"
    """El fichero contradice una regla escrita de la OCDE: la administración lo devolverá
    con ese código en el Status Message."""

    AVISO = "warning"
    """Probablemente rechazado, o la regla depende de algo que el fichero no dice (por
    ejemplo, si va al entorno de pruebas o al de producción)."""

    INCOMPLETO = "undetermined"
    """No se puede determinar con este fichero. El hallazgo dice qué haría falta mirar."""


@dataclass(frozen=True)
class Hallazgo:
    """Un incumplimiento, o la imposibilidad de descartarlo.

    `codigos` y `cita` no son decorado: sin el código oficial y la frase literal, quien
    recibe el informe no puede contrastarlo con lo que le devolverá la administración.
    """

    regla: str
    severidad: Severidad
    titulo: str
    detalle: str
    codigos: tuple[str, ...]
    cita: str
    fichero: str = ""
    linea_xml: int = 0

    def linea(self, con_fichero: bool = False) -> str:
        donde = ""
        if con_fichero and self.fichero:
            donde = f" [{self.fichero}{f':{self.linea_xml}' if self.linea_xml else ''}]"
        elif self.linea_xml:
            donde = f" [line {self.linea_xml}]"
        codigo = f" ({'/'.join(self.codigos)})" if self.codigos else ""
        return f"{self.severidad.value.upper():12} {self.regla}{codigo}{donde}: {self.titulo}"


@dataclass
class Informe:
    """El resultado completo de revisar uno o varios ficheros."""

    hallazgos: list[Hallazgo]
    ficheros: list[str]
    versiones: dict[str, str]
    """Versión de esquema usada para cada fichero (`2.0`, `3.0`)."""
    contextos: dict[str, str]
    """`exchange` (entre autoridades competentes) o `domestic` (entidad → su administración)."""

    @property
    def errores(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.severidad is Severidad.ERROR]

    @property
    def avisos(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.severidad is Severidad.AVISO]

    @property
    def incompletos(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.severidad is Severidad.INCOMPLETO]
