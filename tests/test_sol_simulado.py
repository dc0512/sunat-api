"""Prueba el flujo completo contra un portal SOL simulado (tests/portal_falso).

El portal simulado usa los selectores que el bot espera; no prueba que coincidan con el real.
"""
import functools
import http.server
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from sunat_bot.config import CredencialSOL  # noqa: E402
from sunat_bot.sol import DetenerBot, NavegadorSOL, navegador  # noqa: E402

PORTAL = Path(__file__).parent / "portal_falso"


@pytest.fixture(scope="module")
def url():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(PORTAL))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/login.html"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with navegador() as b:
        yield b


def _sol(browser, url, tmp_path=None):
    ctx = browser.new_context(accept_downloads=True)
    return ctx, NavegadorSOL(ctx.new_page(), url, tmp_path)


def test_flujo_completo(browser, url, tmp_path):
    ctx, sol = _sol(browser, url, tmp_path / "explorar")
    sol.ingresar(CredencialSOL("20123456789", "BOTLECTU", "ok-secreta-987"))
    buzon = sol.abrir_buzon()
    mensajes = sol.listar(buzon, "20123456789")
    assert [m.id_mensaje for m, _ in mensajes] == ["M001", "M002"]
    assert mensajes[0][0].leido_antes is False and mensajes[1][0].leido_antes is True
    assert mensajes[0][0].fecha_deposito == "03/11/2026 10:15"

    m, fila = mensajes[0]
    m = sol.abrir_y_descargar(buzon, m, fila, tmp_path / "M001")
    assert "Contenido completo" in m.texto
    assert len(m.adjuntos) == 1 and Path(m.adjuntos[0]).name == "M001.pdf"
    assert Path(m.adjuntos[0]).read_bytes().startswith(b"%PDF")

    m2, fila2 = mensajes[1]
    m2 = sol.abrir_y_descargar(buzon, m2, fila2, tmp_path / "M002")
    assert Path(m2.adjuntos[0]).name == "M002.pdf"

    capturas = list((tmp_path / "explorar").glob("*.png"))
    assert capturas
    html = "".join(p.read_text() for p in (tmp_path / "explorar").glob("*.html"))
    assert "ok-secreta-987" not in html
    ctx.close()


@pytest.mark.parametrize("clave,motivo", [
    ("captcha", "captcha"),
    ("codigo", "código de verificación"),
    ("mal", "rechazó"),
])
def test_se_detiene(browser, url, clave, motivo):
    ctx, sol = _sol(browser, url)
    with pytest.raises(DetenerBot, match=motivo):
        sol.ingresar(CredencialSOL("20123456789", "BOTLECTU", clave))
    ctx.close()


def test_error_de_red_no_intenta_ingreso(browser):
    ctx = browser.new_context()
    sol = NavegadorSOL(ctx.new_page(), "http://127.0.0.1:1/login.html")
    with pytest.raises(DetenerBot, match="No se intentó el ingreso"):
        sol.ingresar(CredencialSOL("20123456789", "BOTLECTU", "ok-x"))
    ctx.close()
