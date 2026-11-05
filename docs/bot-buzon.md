# Bot del Buzón Electrónico SOL

Estado: esqueleto funcional, probado solo contra un portal SOL **simulado**. Los selectores del portal real están sin verificar y se ajustan en la primera corrida con `--explorar`.

## Qué hace

1. **`alertas`**: lee del correo (IMAP, solo lectura) los avisos de SUNAT de los últimos días y los muestra por empresa: RUC, razón social, tipo (buzón, SINE, coactiva, deuda), número de resolución y fecha límite si el correo los trae. No entra a SOL.
2. **`revisar`**: entra a SOL con el usuario secundario de cada empresa, abre el Buzón Electrónico, lista los mensajes, abre los que no tiene guardados y guarda el texto (`mensaje.txt`) y los PDF en `salida/<RUC>/<fecha>_<asunto>/`. Una base SQLite (`salida/buzon.sqlite`) evita repetir mensajes.

Con `--desde-correo`, `revisar` solo entra a las empresas que tienen alertas nuevas en el correo. Así se reducen los ingresos a SOL.

## Reglas de seguridad del bot

- Las claves se leen de un `.env` local o de variables de entorno. No están en el repo, no se imprimen y no quedan en las capturas.
- Un solo intento de ingreso por empresa. Si SOL rechaza la clave, el bot no reintenta, para no bloquear el usuario.
- Si aparece captcha o un código de verificación, el bot se detiene y lo dice. No intenta saltarlos.
- `--solo-listar` muestra los mensajes nuevos sin abrirlos, para no marcarlos como leídos.
- Pausa de 20 segundos entre empresas (`--pausa`).

## Instalación (en tu computadora)

```bash
git clone https://github.com/dc0512/sunat-api.git
cd sunat-api
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env             # y completa .env con tus datos; nunca lo subas
```

## Uso

```bash
python -m sunat_bot alertas --dias 7
python -m sunat_bot revisar --ruc 20XXXXXXXXX --explorar --ver --solo-listar   # primera corrida
python -m sunat_bot revisar --desde-correo                                     # uso diario
```

## Pendiente hasta tener el usuario secundario

| Paso | Quién | Detalle |
|---|---|---|
| 1. Crear un usuario secundario SOL de prueba con perfil de consulta del buzón | Dario | En SOL, administración de usuarios secundarios. Empezar con una sola empresa |
| 2. Contraseña de aplicación del correo de alertas | Dario | En Gmail: Cuenta de Google > Seguridad > Contraseñas de aplicación. Con eso ya funciona `alertas` |
| 3. Primera corrida con `--explorar --ver --solo-listar` | Dario, en su computadora | Guarda capturas y HTML de cada paso en `salida/exploracion/<RUC>/`. Revisa las capturas antes de compartirlas: pueden mostrar datos de la empresa |
| 4. Ajustar `sunat_bot/selectores.py` con lo que se vea en el portal real | Claude | Los selectores actuales son suposiciones marcadas como no verificadas |
| 5. Definir qué hacer si SOL pide un código de verificación | Dario y Claude | Depende de las R.S. 000089-2026 y 000121-2026. Si el código llega por correo, el bot puede leerlo; si llega por SMS, no |
| 6. Programar la ejecución diaria | Claude | Tarea programada en tu computadora (cron o Programador de tareas de Windows) |

## Pruebas

```bash
pip install -r requirements.txt && playwright install chromium
python -m pytest -q
```

`tests/test_sol_simulado.py` levanta un portal falso en `tests/portal_falso/` y prueba el ingreso, la lista, la apertura, la descarga y las paradas por captcha, código y clave incorrecta. Los formatos de correo de `tests/test_correo.py` están basados en alertas reales, con RUC y nombres ficticios.

Si ya tienes un Chromium instalado y no quieres descargar el de Playwright, define `SUNAT_CHROMIUM` con la ruta del ejecutable.
