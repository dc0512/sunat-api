# Investigación: leer y descargar los mensajes del Buzón Electrónico SOL

Estado: investigación, sin credenciales. Fecha: 5 de noviembre de 2026.
Complementa el plan técnico de [bandeja-electronica.md](bandeja-electronica.md).

**Motivo.** Las alertas que SUNAT manda por correo no traen todo el contenido del mensaje. Para ver el detalle y el PDF hay que entrar al buzón en SOL. Este documento evalúa cómo podría hacerlo un bot.

**Convención.** Todo lo marcado **[no verificado]** no lo pude confirmar en una fuente oficial. Desde el entorno de la investigación la red bloquea todos los dominios `*.sunat.gob.pe` (y también `lpderecho.pe`), así que tampoco pude abrir las guías y los PDF oficiales para contrastar.

## Respuesta corta

1. **No encontré ningún servicio oficial (API REST ni SOAP) que devuelva el contenido de los mensajes del buzón.** Los servicios con credenciales API de SUNAT cubren SIRE, guías de remisión y consulta de comprobantes. Los servicios SOAP conocidos (`billService`, consulta de CDR) son de facturación electrónica. Ninguno expone el buzón **[no verificado como ausencia definitiva; solo puedo afirmar que no aparece en la documentación pública]**.
2. Sin API, la única vía para obtener el contenido completo es **automatizar el portal SOL** con un navegador (Playwright), entrando con un usuario secundario de solo consulta por empresa.
3. Los riesgos principales son: las nuevas medidas de seguridad de acceso a SOL de 2026, cambios de pantalla sin aviso, y que abrir un mensaje lo marque como leído.
4. Esfuerzo estimado: correo como disparador, 2 a 3 días; portal SOL con descarga de PDF para una empresa, 5 a 8 días; extender a todas las empresas y dejarlo estable, 3 a 5 días más.

## 1. ¿Existe un servicio oficial para el contenido del buzón?

| Servicio de SUNAT | Credenciales | ¿Da acceso al buzón? |
|---|---|---|
| API SIRE (registros de compras y ventas) | `client_id` + `client_secret` + usuario y Clave SOL (OAuth `grant_type=password`) | No |
| API GRE (guías de remisión) | Igual que SIRE | No |
| Consulta Integrada de Comprobantes | `client_id` + `client_secret` (`client_credentials`) | No |
| SOAP de facturación electrónica (`billService`, consulta CDR) | Usuario SOL secundario + certificado | No |
| Buzón Electrónico | Solo web SOL y App SUNAT (Personas / Emprender) con Clave SOL | No tiene API pública **[no verificado]** |

Lo que sí está confirmado en fuentes públicas de SUNAT y gob.pe:

- El buzón está dentro de SOL, en "Mis Trámites y Consultas", y también en las apps de SUNAT. Se necesita Clave SOL.
- SUNAT avisa por correo o celular registrado cuando deposita una notificación, pero la falta de aviso no invalida la notificación.
- Desde el 1 de marzo de 2023 la notificación electrónica se entiende hecha en la fecha de depósito en el buzón.
- La app permite buscar, crear carpetas y descargar notificaciones.

La app móvil usa por fuerza algún servicio interno, pero no está documentado ni autorizado para terceros. Usarlo sería ingeniería inversa de un canal privado, así que lo descarto como opción.

Hay proveedores privados que anuncian un "inbox SUNAT" por API. Por dentro también entran al portal con la clave del cliente, así que no son una vía oficial y obligan a entregarles acceso a SOL.

**Acción recomendada:** preguntar a SUNAT (0-801-12-100 u Orientación SOL) si existe o se prevé un servicio para el buzón. Si dicen que sí, se usa ese y se abandona el portal.

## 2. Flujo del portal web para listar y abrir un mensaje

SUNAT no publica las rutas internas del buzón. Lo que sigue combina los pasos que describen las guías públicas con URLs conocidas del portal. Las URLs están **[no verificadas]**: no pude abrirlas desde este entorno y pueden haber cambiado.

| Paso | Qué hace el usuario | Ruta o parámetro | Estado |
|---|---|---|---|
| 1 | Entra a SUNAT Operaciones en Línea desde sunat.gob.pe | Menú SOL: `https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm` | **[no verificado]** |
| 2 | Inicia sesión con RUC, usuario y Clave SOL (o DNI y Clave SOL) | La pantalla de login se sirve desde `api-seguridad.sunat.gob.pe` (flujo OAuth de SUNAT) con RUC, usuario y clave como campos del formulario | **[no verificado]** |
| 3 | Pasa las medidas adicionales de seguridad, si SUNAT las pide | Validación de correo y celular, posible código de un solo uso (ver sección 3) | Parcial: hay resoluciones de 2026 sobre seguridad de acceso, contenido no leído |
| 4 | En el menú, abre el ícono "Buzón Electrónico" (en "Mis Trámites y Consultas") | Se abre el módulo del buzón dentro del menú SOL, normalmente en un marco (iframe) | Pasos confirmados en guías públicas; ruta del módulo **[no verificada, no la documento]** |
| 5 | Ve la lista de mensajes: asunto, fecha de depósito, estado leído o no leído, carpetas | La lista se carga por solicitudes internas del módulo | Campos confirmados en guías y prensa; solicitudes **[no verificadas]** |
| 6 | Abre un mensaje: ve el texto y los adjuntos (notificación en PDF, constancia de depósito) | Cada mensaje tiene un identificador interno que usa el módulo para mostrar el detalle y descargar el PDF | Descarga confirmada en guías; formato del identificador **[no verificado]** |

Para el bot, lo seguro es **no depender de rutas internas** y navegar como una persona: clic en el ícono, leer la tabla, abrir cada fila nueva, descargar el adjunto y guardarlo con `ruc`, fecha de depósito y asunto. Cuando haya acceso real con un usuario de prueba, se puede grabar el tráfico del navegador para ver si la lista viene en JSON, lo que haría la lectura más estable que leer el HTML.

## 3. Riesgos de automatizar el portal

| Riesgo | Detalle | Cómo mitigarlo |
|---|---|---|
| Nuevas medidas de seguridad de acceso en 2026 | La R.S. 000089-2026/SUNAT menciona nuevas medidas de seguridad para entrar a SOL y la R.S. 000121-2026/SUNAT obliga a validar correo y celular del RUC. Si incluyen un código por SMS o correo en cada ingreso, el bot no puede entrar solo. **[contenido exacto no verificado]** | Leer las dos resoluciones antes de programar. Si hay código por correo, el bot puede leerlo del buzón de correo de alertas; si es por SMS, hay que pedir el código a una persona |
| Captcha | No encontré fuente que diga que el login de SOL use captcha hoy **[no verificado]**. Algunas consultas públicas de SUNAT sí lo usan | Si aparece, el bot se detiene y avisa. No se intenta resolver ni saltar |
| Bloqueo de la Clave SOL por intentos fallidos | SUNAT bloquea el acceso tras varios intentos fallidos; el número exacto **[no verificado]** | Un solo intento por ejecución; si falla, no reintenta y avisa |
| Cambios de pantalla | SUNAT cambia el portal sin aviso (por ejemplo, el login migró a `api-seguridad`) | Selectores por texto visible, prueba diaria que avise si no encuentra el ícono o la tabla |
| Sesión única o expiración | Entrar con el mismo usuario desde el bot y desde un navegador puede cerrar una de las sesiones **[no verificado]** | Usuario secundario exclusivo del bot |
| Mensaje marcado como leído | Abrir el mensaje en SOL cambia su estado. La fecha de notificación es la del depósito, así que no cambia el plazo | Avisar en el resumen; guardar siempre el PDF |
| Seguridad de las claves | El bot necesita una clave para cada empresa | Usuario secundario solo con perfil de consulta del buzón, secretos en un gestor y nunca en el repo ni en el chat |
| Términos de uso | SUNAT no prohíbe expresamente el acceso automatizado con credenciales propias en lo que encontré, pero tampoco lo autoriza **[no verificado]** | Frecuencia baja (una vez al día por empresa), pausas entre empresas, solo lectura |

## 4. Estimación de esfuerzo

Supone un desarrollador que conoce Python y Playwright, y que Dario ya creó un usuario secundario de prueba.

| Opción | Qué entrega | Esfuerzo | Notas |
|---|---|---|---|
| A. Solo correo de alertas | Lista de avisos nuevos por empresa, sin contenido completo | 2 a 3 días | No resuelve el problema por sí sola; sirve como disparador para B |
| B. Portal SOL con Playwright, una empresa | Login, lista, apertura de mensajes nuevos, descarga de PDF, guardado en SQLite | 5 a 8 días | Más 1 a 2 días si hay código de verificación por correo |
| B'. B para todas las empresas | Bucle por RUC, secretos por empresa, resumen diario, avisos de fallo | 3 a 5 días más | Mantenimiento estimado de 1 a 2 días al trimestre por cambios del portal |
| C. API oficial | Lectura estable por servicio | 2 a 4 días, si existe | Hoy no existe que yo sepa; depende de la respuesta de SUNAT |

Recomendación: **A + B**. El correo dice cuándo hay algo nuevo y en qué empresa, y el bot entra solo a esa empresa a descargar el contenido. Así se reducen los ingresos a SOL y el riesgo de bloqueo.

## 5. Qué falta para confirmar

1. Leer las R.S. 000089-2026 y 000121-2026 para saber si el ingreso a SOL pide un código adicional. Si Dario sube los PDF al proyecto, se pueden revisar.
2. Confirmar con SUNAT si hay una API para el buzón.
3. Una sesión de prueba, hecha por Dario en su navegador con un usuario secundario, para anotar los pasos reales y grabar el tráfico (sin compartir la clave).

## Fuentes

- Buzón Electrónico, SUNAT: https://personas.sunat.gob.pe/landing/buzon-electronico
- 08. Buzón Electrónico, Orientación SUNAT: https://orientacion.sunat.gob.pe/6619-08-buzon-electronico
- Notificaciones SUNAT, Emprender: https://emprender.sunat.gob.pe/acciones-sunat/facultad-fiscalizacion/notificaciones-sunat
- Guía del Buzón Electrónico (PDF), Emprender: https://emprender.sunat.gob.pe/sites/default/files/inline-files/Buz%C3%B3n%20Electr%C3%B3nico_compressed.pdf
- Notificaciones a través de Buzón SOL, cobranza coactiva: https://orientacion.sunat.gob.pe/node/949
- Acceder al Buzón SOL, gob.pe: https://www.gob.pe/7880-acceder-al-buzon-sol
- Notificaciones válidas desde su remisión (1 de marzo de 2023), Andina: https://andina.pe/agencia/noticia-sunat-desde-hoy-1-marzo-notificaciones-electronicas-valdran-desde-su-remision-930684.aspx
- Cómo acceder al buzón electrónico, Gestión: https://gestion.pe/peru/sunat-como-acceder-a-mi-buzon-electronico-notificaciones-electronicas-peru-nnda-nnlt-noticia/
- R.S. 000089-2026/SUNAT: https://www.sunat.gob.pe/legislacion/superin/2026/000089-2026.pdf
- R.S. 000121-2026/SUNAT, resumen en LP Derecho: https://lpderecho.pe/sujetos-obligados-inscribirse-ruc-informar-validar-datos-contacto-correo-electronico-numero-celular-resolucion-de-superintendencia-000121-2026-sunat/
