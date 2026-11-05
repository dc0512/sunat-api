from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AlertaCorreo:
    """Aviso que SUNAT manda por correo cuando deposita algo en el buzón."""

    message_id: str
    ruc: str
    fecha: str  # fecha del correo, ISO 8601
    remitente: str
    asunto: str
    tipo: str  # buzon, sine, coactiva, deuda, otro
    razon_social: str = ""
    documento: str = ""  # número de resolución o valor, si el correo lo trae
    fecha_limite: str = ""  # dd/mm/aaaa, si el correo la trae


@dataclass
class MensajeBuzon:
    """Mensaje leído del Buzón Electrónico en SOL."""

    ruc: str
    id_mensaje: str
    fecha_deposito: str
    asunto: str
    leido_antes: bool = False
    texto: str = ""
    adjuntos: list[str] = field(default_factory=list)  # rutas locales
