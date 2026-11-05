"""Lectura de las alertas que SUNAT envía por correo.

Formatos vistos en alertas reales (noviembre de 2026):
- comunica@correo.sunat.gob.pe, asunto "Alerta de notificación Buzon SOL" o "Alerta de notificación SINE":
  razón social en una línea y debajo "RUC N°20xxxxxxxxx".
- comunica@correo.sunat.gob.pe, asunto "Notificaciones a través del Buzón Electrónico SOL": "RUC: 10xxxxxxxxx".
- cobranzasunatNN@sunat.gob.pe, asunto "Alerta SUNAT notificación de Resolución de Ejecución Coactiva."
  o "Alerta SUNAT notificación de deuda": "Razón Social: ..." y "Número de RUC: ...",
  a veces con el número de resolución y una fecha límite de pago.
"""
from __future__ import annotations

import email
import imaplib
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime
from html import unescape

from .config import CredencialIMAP
from .modelo import AlertaCorreo

RE_RUC = re.compile(r"RUC\s*(?:N\s*[°º.o]?\s*)?:?\s*(\d{11})\b", re.IGNORECASE)
RE_RAZON_EXPLICITA = re.compile(r"Raz[oó]n Social:[ \t]*([^\n|]*)", re.IGNORECASE)
RE_DOCUMENTO = re.compile(
    r"(?:Resoluci[oó]n|Orden de Pago|Valor|Esquela|Requerimiento)[^\n]{0,80}?N\s*\.?\s*[°º]\s*(\d{6,})",
    re.IGNORECASE,
)
RE_FECHA_LIMITE = re.compile(r"a m[aá]s tardar el\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)


def _normalizar(texto: str) -> str:
    # Algunos asuntos llegan con "?" en lugar de tildes; se comparan sin ellas.
    t = texto.lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("?", "")):
        t = t.replace(a, b)
    return t


def clasificar(asunto: str) -> str:
    a = _normalizar(asunto)
    a = a.replace("_", " ")
    if "coactiva" in a:
        return "coactiva"
    if "acciones de cobranza" in a:
        return "cobranza"
    if "fraccionamiento" in a:
        return "fraccionamiento"
    if "deuda" in a:  # incluye "DEUDA_COBRANZA", que es un aviso de deuda
        return "deuda"
    if "cobranza" in a:
        return "cobranza"
    if "omiso" in a or "declaracion" in a:
        return "declaracion"
    if "sine" in a:
        return "sine"
    if "buzn" in a or "buzon" in a:
        return "buzon"
    return "otro"


RE_NO_ES_RAZON = re.compile(r"\bRUC\b|n[uú]mero de|estimad|señor|contribuyente|http|@|para asegurar",
                            re.IGNORECASE)


def razon_valida(texto: str) -> str:
    """Devuelve la razón social limpia o "" si el texto no parece una."""
    t = " ".join(texto.strip(" |:\t").split())
    if len(t) < 3 or RE_NO_ES_RAZON.search(t):
        return ""
    return t


def es_de_sunat(remitente: str) -> bool:
    return remitente.lower().rstrip(">").endswith("sunat.gob.pe")


def interpretar_alerta(message_id: str, remitente: str, asunto: str, fecha: str,
                       cuerpo: str) -> AlertaCorreo | None:
    """Convierte un correo de SUNAT en AlertaCorreo. Devuelve None si no trae RUC."""
    if not es_de_sunat(remitente):
        return None
    m = RE_RUC.search(cuerpo)
    if not m:
        return None
    ruc = m.group(1)

    razon = ""
    m_razon = RE_RAZON_EXPLICITA.search(cuerpo)
    if m_razon:
        razon = razon_valida(m_razon.group(1))
    if not razon:
        # La razón social suele venir en la línea no vacía anterior a "RUC N°..."
        previas = [l for l in cuerpo[: m.start()].splitlines() if l.strip(" |")]
        if previas:
            razon = razon_valida(previas[-1])

    documento = ""
    m_doc = RE_DOCUMENTO.search(cuerpo)
    if m_doc:
        documento = m_doc.group(1)
    m_lim = RE_FECHA_LIMITE.search(cuerpo)

    return AlertaCorreo(
        message_id=message_id,
        ruc=ruc,
        fecha=fecha,
        remitente=remitente,
        asunto=asunto.strip(),
        tipo=clasificar(asunto),
        razon_social=razon,
        documento=documento,
        fecha_limite=m_lim.group(1) if m_lim else "",
    )


def _texto_de(msg: Message) -> str:
    plano, html = [], []
    for parte in msg.walk():
        tipo = parte.get_content_type()
        if parte.get_content_maintype() == "multipart" or parte.get_filename():
            continue
        carga = parte.get_payload(decode=True)
        if carga is None:
            continue
        texto = carga.decode(parte.get_content_charset() or "utf-8", errors="replace")
        if tipo == "text/plain":
            plano.append(texto)
        elif tipo == "text/html":
            html.append(texto)
    if plano:
        return "\n".join(plano)
    crudo = "\n".join(html)
    crudo = re.sub(r"(?is)<(script|style).*?</\1>", " ", crudo)
    crudo = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</td>", "\n", crudo)
    return unescape(re.sub(r"<[^>]+>", " ", crudo))


def _decodificar(valor: str | None) -> str:
    return str(make_header(decode_header(valor or "")))


def leer_alertas_imap(cred: CredencialIMAP, dias: int = 7) -> list[AlertaCorreo]:
    """Lee los correos de SUNAT de los últimos `dias` días. Solo lectura: no marca nada."""
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%d-%b-%Y")
    alertas: list[AlertaCorreo] = []
    with imaplib.IMAP4_SSL(cred.host) as imap:
        imap.login(cred.usuario, cred.clave)
        imap.select(cred.carpeta, readonly=True)
        _, datos = imap.search(None, f'(FROM "sunat.gob.pe" SINCE {desde})')
        for num in datos[0].split():
            _, partes = imap.fetch(num, "(BODY.PEEK[])")
            msg = email.message_from_bytes(partes[0][1])
            try:
                fecha = parsedate_to_datetime(msg["Date"]).isoformat()
            except (TypeError, ValueError):
                fecha = ""
            remitente = email.utils.parseaddr(msg.get("From", ""))[1]
            alerta = interpretar_alerta(
                message_id=msg.get("Message-ID", f"imap-{num.decode()}").strip(),
                remitente=remitente,
                asunto=_decodificar(msg.get("Subject")),
                fecha=fecha,
                cuerpo=_texto_de(msg),
            )
            if alerta:
                alertas.append(alerta)
    return alertas
