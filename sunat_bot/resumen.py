"""Resumen de alertas por empresa, con las urgencias primero."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from .config import SOL_URL_POR_DEFECTO
from .modelo import AlertaCorreo


def _fecha_limite(a: AlertaCorreo) -> date | None:
    try:
        return datetime.strptime(a.fecha_limite, "%d/%m/%Y").date()
    except ValueError:
        return None


def urgencia(a: AlertaCorreo, hoy: date) -> tuple[int, str]:
    """(prioridad, etiqueta). Menor prioridad = más urgente."""
    limite = _fecha_limite(a)
    if limite:
        dias = (limite - hoy).days
        if dias < 0:
            return 0, f"VENCIDA el {a.fecha_limite}"
        if dias <= 1:
            return 1, f"vence {'hoy' if dias == 0 else 'mañana'} ({a.fecha_limite})"
        if dias <= 7:
            return 2, f"vence en {dias} días ({a.fecha_limite})"
        return 4, f"vence el {a.fecha_limite}"
    if a.tipo == "coactiva":
        return 3, "cobranza coactiva sin fecha en el correo"
    return 9, ""


def armar_resumen(alertas: list[AlertaCorreo], hoy: date, rucs_con_sol: set[str] | None = None) -> str:
    lineas = [f"# Resumen de alertas SUNAT, {hoy.strftime('%d/%m/%Y')}", ""]
    if not alertas:
        return "\n".join(lineas + ["No hay alertas en el periodo."])

    urgentes = sorted(
        ((urgencia(a, hoy), a) for a in alertas if urgencia(a, hoy)[0] < 9),
        key=lambda x: (x[0][0], x[1].fecha_limite, x[1].ruc),
    )
    vistos = set()
    if urgentes:
        lineas += ["## Urgente", ""]
        for (_, etiqueta), a in urgentes:
            clave = (a.ruc, a.documento or a.message_id)
            if clave in vistos:
                continue
            vistos.add(clave)
            doc = f", documento {a.documento}" if a.documento else ""
            lineas.append(f"- **{a.ruc}** {a.razon_social}: {a.tipo}{doc}, {etiqueta}")
        lineas.append("")

    por_ruc: dict[str, list[AlertaCorreo]] = defaultdict(list)
    for a in alertas:
        por_ruc[a.ruc].append(a)

    lineas += ["## Por empresa", "", "| RUC | Empresa | Alertas | Tipos | Última | Usuario SOL |",
               "|---|---|---:|---|---|---|"]
    for ruc, lista in sorted(por_ruc.items(), key=lambda x: max(a.fecha for a in x[1]), reverse=True):
        razon = next((a.razon_social for a in sorted(lista, key=lambda a: a.fecha, reverse=True)
                      if a.razon_social), "")
        tipos: dict[str, int] = defaultdict(int)
        for a in lista:
            tipos[a.tipo] += 1
        tipos_txt = ", ".join(f"{t} {n}" for t, n in sorted(tipos.items()))
        ultima = max(a.fecha for a in lista)[:10]
        sol = "" if rucs_con_sol is None else ("sí" if ruc in rucs_con_sol else "no")
        lineas.append(f"| {ruc} | {razon} | {len(lista)} | {tipos_txt} | {ultima} | {sol} |")

    lineas += ["", f"Para ver el detalle, entra al Buzón Electrónico en SOL: {SOL_URL_POR_DEFECTO}",
               "", "Las fechas límite salen del texto del correo. Confírmalas siempre en SOL."]
    return "\n".join(lineas)
