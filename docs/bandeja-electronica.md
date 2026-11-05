# Plan técnico: lectura de la bandeja electrónica (Buzón SOL)

Estado: borrador para revisión. No contiene credenciales ni las necesita.
Fecha de la investigación: 5 de noviembre de 2026.

## 1. Resumen

- **No encontré una API oficial de SUNAT para leer el Buzón Electrónico.** Las "Credenciales de API SUNAT" (client_id y client_secret) sirven para SIRE, guías de remisión (GRE) y consulta de validez de comprobantes, pero ningún manual público que encontré expone un recurso de buzón o de notificaciones.
- Por eso el plan propone tres vías, en orden de preferencia:
  1. **Alertas por correo** que SUNAT envía al correo registrado en la ficha RUC cada vez que deposita algo en el buzón. No necesita Clave SOL.
  2. **Lectura automatizada del portal SOL** con un usuario secundario de solo lectura por empresa. Necesita una clave, pero no la Clave SOL principal.
  3. **API oficial**, si SUNAT la publica o la confirma. El código queda preparado para cambiar de fuente sin rehacer el resto.
- Las credenciales API sí son útiles para el resto del proyecto (SIRE, validación de comprobantes, GRE), así que vale la pena generarlas igual.

## 2. Qué verifiqué y qué no

| Punto | Estado |
|---|---|
| El buzón se consulta en SOL (Mis Trámites y Consultas) y en la App SUNAT | Verificado en páginas públicas de SUNAT y gob.pe |
| SUNAT envía una alerta al correo o celular registrado cuando deposita una notificación | Verificado en orientacion.sunat.gob.pe |
| Desde el 1 de marzo de 2023 la notificación se entiende hecha en la fecha de depósito en el buzón | Verificado en fuentes públicas (prensa y SUNAT) |
| No existe API oficial pública para el buzón | **No verificado del todo.** Solo puedo decir que no la encontré en los manuales públicos. Conviene confirmarlo con SUNAT (0-801-12-100 o Orientación SOL) |
| El endpoint de token y el formato del cuerpo (sección 4) | Verificado en resúmenes de los manuales GRE y de Consulta Integrada de CPE. Los manuales advierten que las URI son referenciales |
| El `scope` exacto de SIRE y el host `api-sire.sunat.gob.pe` | **No verificado.** Lo indico de memoria. Desde este entorno no pude descargar los PDF de `cpe.sunat.gob.pe` porque la red lo bloquea |
| La ruta exacta del menú SOL para generar credenciales | **No verificado.** La ruta de la sección 5 es aproximada |
| Los endpoints internos de la web SOL del buzón | **No verificado.** No los documenté a propósito porque no son públicos y pueden cambiar sin aviso |
| Proveedores privados que ofrecen un "inbox" por API (por ejemplo Visioner7) | Existen anuncios, pero no hay respaldo oficial de SUNAT y requieren entregarles acceso a SOL |

## 3. Datos que queremos obtener del buzón

Cada mensaje del buzón se guardaría con estos campos (los nombres son nuestros, no de SUNAT):

| Campo | Descripción | Vía 1 (correo) | Vía 2 (SOL) |
|---|---|---|---|
| `ruc` | Empresa destinataria | Sí | Sí |
| `fecha_deposito` | Fecha y hora de depósito, que es la que cuenta para los plazos | Aproximada (hora del correo) | Sí |
| `asunto` | Asunto o tipo de documento | Parcial | Sí |
| `tipo` | Orden de pago, resolución de cobranza, esquela, requerimiento, valor, etc. | Inferido del asunto, si lo trae | Sí |
| `numero_documento` | Número de la resolución o del valor | No | Sí, si aparece |
| `leido` | Si ya se abrió en SOL | No | Sí |
| `adjuntos` | PDF de la notificación y constancia | No | Sí |
| `plazo_estimado` | Vencimiento calculado desde `fecha_deposito` según el tipo | Calculado | Calculado |

El plazo es un cálculo nuestro como ayuda. Siempre hay que validarlo con el documento.

## 4. Autenticación OAuth de SUNAT (para SIRE y otros servicios)

Esto **no** abre el buzón, pero es la base de las demás automatizaciones del proyecto.

### 4.1 Token con usuario SOL (SIRE, GRE)

```
POST https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/
Content-Type: application/x-www-form-urlencoded

grant_type=password
scope=<scope del servicio>
client_id={client_id}
client_secret={client_secret}
username={RUC}{USUARIO_SOL}
password={CLAVE_SOL}
```

Respuesta: `access_token`, `token_type` y `expires_in` (en segundos, normalmente 3600). El token se manda como `Authorization: Bearer <access_token>`.

Valores de `scope` por servicio:

| Servicio | scope | Estado |
|---|---|---|
| GRE (guías de remisión) | `https://api-cpe.sunat.gob.pe` | Visto en el manual GRE |
| SIRE (registros de ventas y compras) | `https://api-sire.sunat.gob.pe` | **No verificado** |

**Ojo:** este flujo pide la Clave SOL en cada solicitud de token. Las credenciales API no reemplazan la Clave SOL, solo identifican la aplicación. Por eso recomiendo usar un **usuario secundario SOL** por empresa (sección 5) y nunca la clave principal.

### 4.2 Token sin usuario SOL (consulta de validez de comprobantes)

```
POST https://api-seguridad.sunat.gob.pe/v1/clientesextranet/{client_id}/oauth2/token/
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
scope=https://api.sunat.gob.pe/v1/contribuyente/contribuyentes
client_id={client_id}
client_secret={client_secret}
```

Sirve para la Consulta Integrada de Comprobantes de Pago. El `scope` está tomado de memoria y del manual de Consulta Integrada, pero no pude abrir el PDF desde aquí.

## 5. Pasos para Dario

Hazlos tú en tu navegador. No pegues claves en el chat, en issues ni en el repositorio.

1. **Confirma el correo de alertas.** En SOL, revisa que cada empresa tenga registrado un correo al que tengas acceso (de preferencia uno solo para todas, por ejemplo `alertas-sunat@...`). Esto activa la vía 1.
2. **Crea un usuario secundario SOL por empresa** (SOL > Administración de usuarios secundarios). Dale solo los perfiles de consulta que necesites (buzón, consultas, SIRE). Así la automatización nunca usa tu Clave SOL principal y puedes darla de baja cuando quieras. La ruta y los nombres exactos de los perfiles no los verifiqué.
3. **Genera las credenciales API** por empresa, en SOL > Empresas > Credenciales de API SUNAT (ruta aproximada). Registra una aplicación, por ejemplo "sunat-api", y anota el `client_id` y el `client_secret`. Si te pide una URL, usa `https://dc0512.github.io/sunat-api/`.
4. **Guarda los secretos fuera del repo.** Lo mínimo es un archivo `.env` local, que el `.gitignore` de este PR ya excluye del repo, o, mejor, un gestor de secretos (1Password, Bitwarden, o los Secrets de GitHub Actions si se ejecuta allí). Un juego por RUC: `SUNAT_<RUC>_CLIENT_ID`, `SUNAT_<RUC>_CLIENT_SECRET`, `SUNAT_<RUC>_SOL_USER`, `SUNAT_<RUC>_SOL_PASS`.
5. **Pregunta a SUNAT** si hay o habrá un servicio API para el buzón. Si lo confirman, se cambia la fuente a la vía 3 y se borra la vía 2.

## 6. Diseño propuesto

```
fuentes/
  correo.py      # vía 1: lee alertas del correo (IMAP o Gmail API)
  sol_web.py     # vía 2: navegador sin interfaz (Playwright), solo lectura
  api.py         # vía 3: si SUNAT publica un servicio
modelo.py        # Mensaje(ruc, fecha_deposito, asunto, tipo, ...)
almacen.py       # SQLite: evita duplicados por (ruc, id o hash)
avisos.py        # resumen diario por correo o en la página del proyecto
```

- **Frecuencia:** una lectura al día por empresa (por ejemplo, 7:00 a. m.). La vía 1 puede revisarse cada hora porque solo lee correo.
- **Vía 2, reglas de seguridad:** solo lectura, sin descargar más de lo necesario, pausas entre empresas, y se detiene si aparece captcha o un cambio de pantalla en lugar de intentar saltarlo. Abrir un mensaje en SOL puede marcarlo como leído, lo cual no cambia la fecha de notificación (cuenta el depósito), pero conviene que el resumen lo diga.
- **Salida:** una tabla con los mensajes nuevos por empresa, el tipo y el plazo estimado, marcando en rojo órdenes de pago, resoluciones de cobranza coactiva y requerimientos de fiscalización.

## 7. Próximos pasos

1. Dario confirma el correo de alertas y crea los usuarios secundarios (pasos 1 y 2).
2. Implementar la vía 1 (correo) con una empresa de prueba.
3. Implementar la vía 2 con un usuario secundario de una empresa, solo lectura.
4. Repetir para el resto de empresas.

## Fuentes

- Buzón Electrónico, SUNAT: https://personas.sunat.gob.pe/landing/buzon-electronico
- Notificaciones Electrónicas, Orientación SUNAT: https://orientacion.sunat.gob.pe/6620-09-notificaciones-electronicas-empresas
- Acceder al Buzón SOL, gob.pe: https://www.gob.pe/7880-acceder-al-buzon-sol
- Manual de servicios web de la plataforma nueva GRE: https://cpe.sunat.gob.pe/sites/default/files/inline-files/Manual_Servicios_GRE%20(1)_0.pdf
- Manual de Consulta Integrada de Comprobante de Pago por Servicio Web v2.0: https://cpe.sunat.gob.pe/sites/default/files/inline-files/Manual-de-Consulta-Integrada-de-Comprobante-de-Pago-por-ServicioWEB_v2_0.pdf
- Manual de servicios Web API SIRE Compras v28: https://cpe.sunat.gob.pe/sites/default/files/inline-files/Manual%20de%20servicios%20Web%20Api%20-%20SIRE_Compras%20v28.pdf
