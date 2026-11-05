from sunat_bot.almacen import Almacen
from sunat_bot.modelo import AlertaCorreo, MensajeBuzon


def test_alertas_y_mensajes(tmp_path):
    al = Almacen(tmp_path / "b.sqlite")
    a = AlertaCorreo("m1", "20123456789", "2026-11-04", "comunica@correo.sunat.gob.pe", "x", "buzon")
    assert al.guardar_alerta(a) is True
    assert al.guardar_alerta(a) is False
    assert al.rucs_con_alertas_pendientes() == ["20123456789"]
    al.marcar_alertas_revisadas("20123456789")
    assert al.rucs_con_alertas_pendientes() == []

    m = MensajeBuzon("20123456789", "M1", "03/11/2026", "Orden de pago", adjuntos=["a.pdf"])
    assert not al.existe_mensaje("20123456789", "M1")
    al.guardar_mensaje(m)
    assert al.existe_mensaje("20123456789", "M1")
