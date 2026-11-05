"""Base SQLite local: evita procesar dos veces la misma alerta o el mismo mensaje."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .modelo import AlertaCorreo, MensajeBuzon

ESQUEMA = """
CREATE TABLE IF NOT EXISTS alertas (
    message_id TEXT PRIMARY KEY,
    ruc TEXT NOT NULL,
    fecha TEXT NOT NULL,
    remitente TEXT,
    asunto TEXT,
    tipo TEXT,
    razon_social TEXT,
    documento TEXT,
    fecha_limite TEXT,
    revisada INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mensajes (
    ruc TEXT NOT NULL,
    id_mensaje TEXT NOT NULL,
    fecha_deposito TEXT,
    asunto TEXT,
    leido_antes INTEGER,
    texto TEXT,
    adjuntos TEXT,
    guardado_en TEXT NOT NULL,
    PRIMARY KEY (ruc, id_mensaje)
);
"""


class Almacen:
    def __init__(self, ruta: str | Path):
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(ruta))
        self.db.executescript(ESQUEMA)

    def cerrar(self) -> None:
        self.db.close()

    # Alertas de correo
    def guardar_alerta(self, a: AlertaCorreo) -> bool:
        """Devuelve True si la alerta es nueva."""
        cur = self.db.execute(
            "INSERT OR IGNORE INTO alertas (message_id, ruc, fecha, remitente, asunto, tipo,"
            " razon_social, documento, fecha_limite) VALUES (?,?,?,?,?,?,?,?,?)",
            (a.message_id, a.ruc, a.fecha, a.remitente, a.asunto, a.tipo,
             a.razon_social, a.documento, a.fecha_limite),
        )
        self.db.commit()
        return cur.rowcount == 1

    def rucs_con_alertas_pendientes(self) -> list[str]:
        filas = self.db.execute(
            "SELECT DISTINCT ruc FROM alertas WHERE revisada = 0 ORDER BY ruc"
        ).fetchall()
        return [f[0] for f in filas]

    def marcar_alertas_revisadas(self, ruc: str) -> None:
        self.db.execute("UPDATE alertas SET revisada = 1 WHERE ruc = ?", (ruc,))
        self.db.commit()

    # Mensajes del buzón
    def existe_mensaje(self, ruc: str, id_mensaje: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM mensajes WHERE ruc = ? AND id_mensaje = ?", (ruc, id_mensaje)
        ).fetchone() is not None

    def guardar_mensaje(self, m: MensajeBuzon) -> None:
        d = asdict(m)
        self.db.execute(
            "INSERT OR REPLACE INTO mensajes (ruc, id_mensaje, fecha_deposito, asunto,"
            " leido_antes, texto, adjuntos, guardado_en) VALUES (?,?,?,?,?,?,?,?)",
            (d["ruc"], d["id_mensaje"], d["fecha_deposito"], d["asunto"],
             int(d["leido_antes"]), d["texto"], json.dumps(d["adjuntos"], ensure_ascii=False),
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        self.db.commit()
