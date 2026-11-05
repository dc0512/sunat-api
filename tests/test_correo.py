from sunat_bot.correo import clasificar, interpretar_alerta

# Cuerpos basados en el formato de alertas reales, con RUC y nombres ficticios.
BUZON_SOL = """Para asegurar la entrega de nuestras comunicaciones en su correo, por favor agregue comunica@correo.sunat.gob.pe

EMPRESA DE PRUEBA S.A.C.
RUC N°20123456789

Estimada/o contribuyente:
En ese sentido le informamos que, tiene pendiente de lectura diversos documentos que hemos notificado en su Buzón Electrónico"""

SINE = BUZON_SOL.replace("RUC N°20123456789", "RUC N° 20123456789")

NOTIFICACION_TABLA = "| Para asegurar la entrega ... |\n| RUC: 10987654321 Estimada/o contribuyente: Mediante el presente le informamos que, hemos remitido una notificación a su Buzón Electrónico |"

COACTIVA = """Señor/a:

Razón Social: PERSONA DE PRUEBA

Número de RUC: 10987654321

Como parte de este proceso, hemos enviado a su Buzón Electrónico SOL la Resolución de Ejecución Coactiva N.º 1330000000001.
A fin de evitar la ejecución de medidas de cobro forzoso, le instamos a realizar el pago total de la deuda, incluyendo intereses, a más tardar el 06/11/2026."""


def test_alerta_buzon():
    a = interpretar_alerta("id1", "comunica@correo.sunat.gob.pe", "Alerta de notificación Buzon SOL", "2026-11-04", BUZON_SOL)
    assert a.ruc == "20123456789"
    assert a.razon_social == "EMPRESA DE PRUEBA S.A.C."
    assert a.tipo == "buzon"
    assert a.documento == ""


def test_alerta_sine_con_espacio():
    a = interpretar_alerta("id2", "comunica@correo.sunat.gob.pe", "Alerta de notificación SINE", "", SINE)
    assert (a.ruc, a.tipo) == ("20123456789", "sine")


def test_alerta_con_tildes_rotas():
    a = interpretar_alerta("id3", "comunica@correo.sunat.gob.pe",
                           "Notificaciones a trav?s del Buz?n Electr?nico SOL", "", NOTIFICACION_TABLA)
    assert (a.ruc, a.tipo) == ("10987654321", "buzon")


def test_alerta_coactiva():
    a = interpretar_alerta("id4", "cobranzasunat12@sunat.gob.pe",
                           "Alerta SUNAT notificación de Resolución de Ejecución Coactiva.", "", COACTIVA)
    assert a.ruc == "10987654321"
    assert a.razon_social == "PERSONA DE PRUEBA"
    assert a.tipo == "coactiva"
    assert a.documento == "1330000000001"
    assert a.fecha_limite == "06/11/2026"


def test_ignora_remitentes_ajenos():
    assert interpretar_alerta("x", "phishing@sunat-gob.pe.com", "Buzon SOL", "", BUZON_SOL) is None


def test_clasificar_deuda():
    assert clasificar("Alerta SUNAT notificación de deuda") == "deuda"


def test_clasifica_otros_asuntos():
    assert clasificar("Alerta SUNAT inicio de acciones de Cobranza") == "cobranza"
    assert clasificar("Fraccionamiento") == "fraccionamiento"
    assert clasificar("Comunicaciones Inductivas a los omisos") == "declaracion"
    assert clasificar("Comunicación Preventiva Declaración Mensual IGV- RENTA FV 621– Periodo 09-2026") == "declaracion"


def test_razon_social_vacia_no_toma_la_linea_siguiente():
    cuerpo = "Señor/a:\n\nRazón Social:\n\nNÚMERO DE\nRUC: 20123456789\n"
    a = interpretar_alerta("id5", "cobranzasunat14@sunat.gob.pe", "Alerta SUNAT notificación de deuda", "", cuerpo)
    assert a.ruc == "20123456789" and a.razon_social == ""
