"""Navegación del portal SOL con Playwright: ingreso, buzón, lista, detalle y adjuntos.

Reglas de seguridad:
- Un solo intento de ingreso por empresa y ejecución. Si falla, no se reintenta.
- Si aparece captcha o un código de verificación, el bot se detiene y avisa.
- Nunca se guarda la clave en capturas, registros ni archivos.
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from playwright.sync_api import Browser, Frame, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PWTimeout

from . import selectores as S
from .config import CredencialSOL
from .modelo import MensajeBuzon

RE_FECHA = re.compile(r"\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?")


class DetenerBot(Exception):
    """Situación que requiere a una persona (captcha, código, clave incorrecta, pantalla nueva)."""


def _primero(alcances: list[Page | Frame], candidatos: list[str], espera_ms: int = 10_000) -> Locator | None:
    """Primer selector que exista en alguno de los alcances, esperando hasta `espera_ms`."""
    limite = time.monotonic() + espera_ms / 1000
    while True:
        for alcance in alcances:
            for sel in candidatos:
                try:
                    loc = alcance.locator(sel)
                    if loc.count() > 0:
                        return loc.first
                except Exception:
                    continue
        if time.monotonic() >= limite:
            return None
        time.sleep(0.25)


def _alcances(page: Page) -> list[Page | Frame]:
    return [page, *[f for f in page.frames if f is not page.main_frame]]


def _texto_visible(page: Page) -> str:
    partes = []
    for alcance in _alcances(page):
        try:
            partes.append(alcance.locator("body").inner_text(timeout=2_000))
        except Exception:
            pass
    return "\n".join(partes).lower()


class NavegadorSOL:
    def __init__(self, page: Page, sol_url: str, carpeta_exploracion: Path | None = None):
        self.page = page
        self.sol_url = sol_url
        self.exploracion = carpeta_exploracion
        self._paso = 0

    # Utilidades
    def capturar(self, nombre: str) -> None:
        """En modo exploración guarda captura y HTML de la página y de sus marcos."""
        if not self.exploracion:
            return
        self._paso += 1
        base = self.exploracion / f"{self._paso:02d}_{nombre}"
        base.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=f"{base}.png", full_page=True)
        for i, alcance in enumerate(_alcances(self.page)):
            try:
                Path(f"{base}_marco{i}.html").write_text(alcance.content(), encoding="utf-8")
            except Exception:
                pass

    def _revisar_bloqueos(self) -> None:
        if _primero(_alcances(self.page), S.SENAL_CAPTCHA, espera_ms=0):
            raise DetenerBot("Apareció un captcha. El bot no lo resuelve; revisa manualmente.")
        texto = _texto_visible(self.page)
        if any(t in texto for t in S.TEXTO_CODIGO_VERIFICACION):
            raise DetenerBot("SOL pide un código de verificación. Hay que definir cómo recibirlo.")
        if any(t in texto for t in S.TEXTO_ERROR_LOGIN):
            raise DetenerBot("SOL rechazó el ingreso o la clave está bloqueada. No se reintenta.")

    # Pasos
    def ingresar(self, cred: CredencialSOL) -> None:
        self.page.goto(self.sol_url, wait_until="domcontentloaded")
        self.capturar("login")  # antes de escribir nada
        alc = _alcances(self.page)
        pestana = _primero(alc, S.LOGIN_PESTANA_RUC, espera_ms=1_500)
        if pestana and pestana.is_visible():
            pestana.click()
        campos = [_primero(alc, s) for s in (S.LOGIN_RUC, S.LOGIN_USUARIO, S.LOGIN_CLAVE, S.LOGIN_BOTON)]
        if not all(campos):
            self._revisar_bloqueos()
            raise DetenerBot("No encontré el formulario de ingreso. La página cambió; ajustar selectores.")
        ruc, usuario, clave, boton = campos
        ruc.fill(cred.ruc)
        usuario.fill(cred.usuario)
        clave.fill(cred.clave)
        boton.click()
        # Espera el menú, pero se detiene apenas aparezca un captcha, código o error.
        limite = time.monotonic() + 20
        while True:
            try:
                self.page.wait_for_load_state("domcontentloaded")
                self._revisar_bloqueos()
                if _primero(_alcances(self.page), S.MENU_LISTO, espera_ms=0):
                    break
            except DetenerBot:
                raise
            except Exception:
                pass  # la página está navegando; se vuelve a mirar
            if time.monotonic() >= limite:
                raise DetenerBot("Después del ingreso no apareció el menú SOL.")
            time.sleep(0.5)
        self.capturar("menu")

    def abrir_buzon(self) -> Page | Frame:
        boton = _primero(_alcances(self.page), S.BOTON_BUZON)
        if not boton:
            raise DetenerBot("No encontré el acceso al Buzón Electrónico en el menú.")
        boton.click()
        # El buzón suele cargarse en un marco; si no, se usa la página.
        limite = time.monotonic() + 20
        while time.monotonic() < limite:
            for alcance in _alcances(self.page):
                if _primero([alcance], S.FILA_MENSAJE, espera_ms=0):
                    self.capturar("buzon")
                    return alcance
            time.sleep(0.5)
        self.capturar("buzon_vacio_o_desconocido")
        texto = _texto_visible(self.page)
        if "no tiene mensajes" in texto or "no existen mensajes" in texto:
            return self.page
        raise DetenerBot("Abrí el buzón pero no reconozco la lista de mensajes.")

    def listar(self, buzon: Page | Frame, ruc: str) -> list[tuple[MensajeBuzon, Locator]]:
        filas = None
        for sel in S.FILA_MENSAJE:
            if buzon.locator(sel).count() > 0:
                filas = buzon.locator(sel)
                break
        if filas is None:
            return []
        resultado = []
        for i in range(filas.count()):
            fila = filas.nth(i)
            texto = " ".join(fila.inner_text().split())
            asunto_loc = _primero([fila], S.FILA_ASUNTO, espera_ms=0)  # type: ignore[list-item]
            fecha_loc = _primero([fila], S.FILA_FECHA, espera_ms=0)  # type: ignore[list-item]
            asunto = " ".join(asunto_loc.inner_text().split()) if asunto_loc else texto
            if fecha_loc:
                fecha = fecha_loc.inner_text().strip()
            else:
                m = RE_FECHA.search(texto)
                fecha = m.group(0) if m else ""
            id_mensaje = ""
            for attr in S.ATRIBUTO_ID:
                id_mensaje = fila.get_attribute(attr) or ""
                if id_mensaje:
                    break
            if not id_mensaje:
                id_mensaje = "h" + hashlib.sha1(f"{fecha}|{asunto}".encode()).hexdigest()[:16]
            clases = (fila.get_attribute("class") or "").lower()
            leido = not any(c in clases for c in S.CLASE_NO_LEIDO)
            resultado.append((MensajeBuzon(ruc, id_mensaje, fecha, asunto, leido_antes=leido), fila))
        return resultado

    def abrir_y_descargar(self, buzon: Page | Frame, mensaje: MensajeBuzon, fila: Locator,
                          carpeta: Path) -> MensajeBuzon:
        carpeta.mkdir(parents=True, exist_ok=True)
        enlace = _primero([fila], S.FILA_ASUNTO, espera_ms=0)  # type: ignore[list-item]
        (enlace or fila).click()
        detalle = _primero(_alcances(self.page), S.DETALLE, espera_ms=15_000)
        if not detalle:
            raise DetenerBot(f"No se abrió el detalle del mensaje {mensaje.asunto!r}.")
        detalle.wait_for(state="visible", timeout=15_000)
        mensaje.texto = detalle.inner_text().strip()
        (carpeta / "mensaje.txt").write_text(
            f"RUC: {mensaje.ruc}\nFecha de depósito: {mensaje.fecha_deposito}\n"
            f"Asunto: {mensaje.asunto}\n\n{mensaje.texto}\n", encoding="utf-8")
        self.capturar(f"detalle_{mensaje.id_mensaje}")

        enlaces: list[Locator] = []
        for alcance in _alcances(self.page):
            for sel in S.ENLACE_ADJUNTO:  # el primer selector que encuentre algo gana
                loc = alcance.locator(f"{sel} >> visible=true")
                if loc.count():
                    enlaces.extend(loc.nth(i) for i in range(loc.count()))
                    break
        for i, e in enumerate(enlaces):
            try:
                with self.page.expect_download(timeout=30_000) as dl:
                    e.click()
                nombre = dl.value.suggested_filename or f"adjunto_{i + 1}.pdf"
                destino = carpeta / nombre
                dl.value.save_as(destino)
                if str(destino) not in mensaje.adjuntos:
                    mensaje.adjuntos.append(str(destino))
            except PWTimeout:
                continue  # el enlace no era una descarga
        volver = _primero(_alcances(self.page), S.VOLVER, espera_ms=2_000)
        if volver:
            volver.click()
            _primero(_alcances(self.page), S.FILA_MENSAJE, espera_ms=10_000)
        return mensaje

    def salir(self) -> None:
        boton = _primero(_alcances(self.page), S.SALIR, espera_ms=1_000)
        if boton:
            try:
                boton.click()
            except Exception:
                pass


@contextmanager
def navegador(visible: bool = False) -> Iterator[Browser]:
    with sync_playwright() as pw:
        # SUNAT_CHROMIUM permite usar un Chromium ya instalado en vez del de Playwright.
        ruta = os.environ.get("SUNAT_CHROMIUM") or None
        browser = pw.chromium.launch(headless=not visible, executable_path=ruta)
        try:
            yield browser
        finally:
            browser.close()
