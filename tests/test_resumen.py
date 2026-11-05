from datetime import date

from sunat_bot.modelo import AlertaCorreo
from sunat_bot.resumen import armar_resumen, urgencia

HOY = date(2026, 11, 5)


def _a(ruc, tipo, limite="", doc="", mid="m", fecha="2026-11-01T10:00"):
    return AlertaCorreo(mid, ruc, fecha, "x@sunat.gob.pe", "asunto", tipo, "EMPRESA", doc, limite)


def test_urgencias():
    assert urgencia(_a("1", "coactiva", "06/11/2026"), HOY) == (1, "vence mañana (06/11/2026)")
    assert urgencia(_a("1", "coactiva", "19/10/2026"), HOY)[0] == 0
    assert urgencia(_a("1", "coactiva"), HOY)[0] == 3
    assert urgencia(_a("1", "buzon"), HOY)[0] == 9


def test_resumen_ordena_y_deduplica():
    alertas = [
        _a("10987654321", "coactiva", "19/10/2026", "111", "a"),
        _a("10987654321", "otro", "19/10/2026", "111", "b"),
        _a("20123456789", "coactiva", "06/11/2026", "222", "c"),
        _a("20123456789", "buzon", mid="d", fecha="2026-11-04T10:00"),
    ]
    txt = armar_resumen(alertas, HOY, {"20123456789"})
    urg = txt.split("## Por empresa")[0]
    assert urg.index("VENCIDA") < urg.index("vence mañana")
    assert urg.count("111") == 1
    assert "| 20123456789 | EMPRESA | 2 | buzon 1, coactiva 1 | 2026-11-04 | sí |" in txt
    assert "| no |" in txt
