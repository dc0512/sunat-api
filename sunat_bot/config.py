"""Configuración del bot. Todo se lee de variables de entorno o de un archivo .env local.

Las claves nunca se guardan en el repositorio ni se escriben en los registros.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# URL de entrada a SUNAT Operaciones en Línea. [no verificado] Puede cambiar sin aviso.
SOL_URL_POR_DEFECTO = "https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm"


def cargar_env(ruta: str | Path = ".env") -> None:
    """Carga un .env sencillo (CLAVE=valor). No pisa variables ya definidas."""
    ruta = Path(ruta)
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class CredencialSOL:
    ruc: str
    usuario: str
    clave: str = field(repr=False)  # nunca se imprime


@dataclass(frozen=True)
class CredencialIMAP:
    host: str
    usuario: str
    clave: str = field(repr=False)
    carpeta: str = "INBOX"


@dataclass
class Config:
    rucs: list[str]
    salida: Path
    sol_url: str
    imap: CredencialIMAP | None

    def credencial_sol(self, ruc: str) -> CredencialSOL | None:
        usuario = os.environ.get(f"SUNAT_{ruc}_SOL_USUARIO", "").strip()
        clave = os.environ.get(f"SUNAT_{ruc}_SOL_CLAVE", "")
        if not usuario or not clave:
            return None
        return CredencialSOL(ruc=ruc, usuario=usuario, clave=clave)

    @property
    def base_datos(self) -> Path:
        return self.salida / "buzon.sqlite"


def desde_entorno() -> Config:
    rucs = [r.strip() for r in os.environ.get("SUNAT_RUCS", "").split(",") if r.strip()]
    for ruc in rucs:
        if not (ruc.isdigit() and len(ruc) == 11):
            raise ValueError(f"RUC inválido en SUNAT_RUCS: {ruc!r}")
    imap = None
    if os.environ.get("SUNAT_IMAP_USUARIO") and os.environ.get("SUNAT_IMAP_CLAVE"):
        imap = CredencialIMAP(
            host=os.environ.get("SUNAT_IMAP_HOST", "imap.gmail.com"),
            usuario=os.environ["SUNAT_IMAP_USUARIO"],
            clave=os.environ["SUNAT_IMAP_CLAVE"],
            carpeta=os.environ.get("SUNAT_IMAP_CARPETA", "INBOX"),
        )
    return Config(
        rucs=rucs,
        salida=Path(os.environ.get("SUNAT_SALIDA", "salida")),
        sol_url=os.environ.get("SUNAT_SOL_URL", SOL_URL_POR_DEFECTO),
        imap=imap,
    )
