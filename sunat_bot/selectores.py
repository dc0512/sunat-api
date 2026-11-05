"""Selectores del portal SOL.

TODOS ESTÁN SIN VERIFICAR contra el portal real. Se tomaron de la descripción pública del
buzón y de nombres de campos conocidos del login de SUNAT. Para cada paso hay varias
opciones y gana la primera que aparezca en la página. Cuando se haga la primera corrida
real con `--explorar`, se ajustan aquí con las capturas que guarda el bot.
"""

# Formulario de ingreso con RUC, usuario y Clave SOL.
LOGIN_PESTANA_RUC = ["#btnPorRuc", "text=RUC"]
LOGIN_RUC = ["#txtRuc", "input[name='txtRuc']", "input[placeholder*='RUC']"]
LOGIN_USUARIO = ["#txtUsuario", "input[name='txtUsuario']", "input[placeholder*='suario']"]
LOGIN_CLAVE = ["#txtContrasena", "input[name='txtContrasena']", "input[type='password']"]
LOGIN_BOTON = ["#btnAceptar", "button:has-text('Iniciar sesión')", "button:has-text('Ingresar')"]

# Señales de que el bot debe detenerse y avisar, sin reintentar.
SENAL_CAPTCHA = ["iframe[src*='recaptcha']", "iframe[src*='hcaptcha']", "img[src*='captcha' i]",
                 "input[name*='captcha' i]"]
TEXTO_CODIGO_VERIFICACION = ["código de verificación", "codigo de verificacion",
                             "código enviado", "ingrese el código"]
TEXTO_ERROR_LOGIN = ["usuario o clave incorrect", "datos ingresados no son", "clave sol bloqueada",
                     "usuario bloqueado", "intentos"]

# Menú SOL ya autenticado.
MENU_LISTO = ["#divOpcionServicio2", "text=Mis Trámites y Consultas", "#aOpcionBuzon",
              "text=Buzón Electrónico"]
BOTON_BUZON = ["#aOpcionBuzon", "a:has-text('Buzón Electrónico')", "text=Buzón Electrónico",
               "a:has-text('Buzón')"]
MARCO_APLICACION = ["#iframeApplication", "iframe[name='iframeApplication']"]

# Bandeja del buzón.
FILA_MENSAJE = ["[data-id-mensaje]", "#listaMensajes li", "table#tablaMensajes tbody tr"]
ATRIBUTO_ID = ["data-id-mensaje", "data-id", "id"]
FILA_ASUNTO = [".asunto", "td.asunto", "a"]
FILA_FECHA = [".fecha", "td.fecha"]
CLASE_NO_LEIDO = ["no-leido", "unread", "bold"]

# Detalle de un mensaje.
DETALLE = ["#detalleMensaje", ".detalle-mensaje", "#divDetalle"]
ENLACE_ADJUNTO = ["a:has-text('Descargar')", "a[href*='.pdf' i]", "a[href*='descarga' i]",
                  "a[onclick*='descarga' i]"]
VOLVER = ["#btnVolver", "button:has-text('Volver')", "a:has-text('Volver')"]

SALIR = ["#btnSalir", "a:has-text('Salir')", "text=Cerrar sesión"]
