#!/usr/bin/env bash
# Corre el resumen diario de alertas SUNAT. Pensado para cron: no depende de la carpeta actual
# ni de variables del usuario. Deja un registro en <salida>/resumen.log y, si hay escritorio,
# muestra una notificación. Si el bot falla, avisa del fallo (nunca "sin urgencias") y sale con 1.
set -uo pipefail
umask 077   # resúmenes y registros solo legibles por el usuario
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"
SALIDA="$(grep -E '^SUNAT_SALIDA=' .env 2>/dev/null | cut -d= -f2- | tr -d '"'"'" || true)"
SALIDA="${SALIDA:-salida}"
case "$SALIDA" in /*) ;; *) SALIDA="$DIR/$SALIDA" ;; esac
mkdir -p "$SALIDA"
LOG="$SALIDA/resumen.log"
SALIDA_TXT="$SALIDA/ultimo-resumen.txt"
RESUMEN_MD="$SALIDA/resumen-$(date +%F).md"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"
if "$DIR/.venv/bin/python" -m sunat_bot --env "$DIR/.env" resumen --dias 30 > "$SALIDA_TXT" 2>&1 \
   && [ -s "$RESUMEN_MD" ]; then
  ESTADO=0
  echo "OK" >> "$LOG"
else
  ESTADO=1
  echo "ERROR (ver $SALIDA_TXT)" >> "$LOG"
fi
chmod 600 "$SALIDA"/resumen-*.md "$SALIDA_TXT" "$LOG" "$SALIDA"/*.sqlite 2>/dev/null || true

if [ "$ESTADO" -eq 0 ]; then
  URGENTES="$(sed -n '/^## Urgente/,/^## Por empresa/p' "$RESUMEN_MD" | grep -c '^- ' || true)"
  if [ "${URGENTES:-0}" -gt 0 ]; then
    TITULO="SUNAT: $URGENTES urgencia(s)"; NIVEL=critical
  else
    TITULO="SUNAT: sin urgencias"; NIVEL=normal
  fi
  CUERPO="$RESUMEN_MD"
else
  TITULO="SUNAT: el resumen FALLÓ"; NIVEL=critical
  CUERPO="No se pudo revisar el correo. Ver $SALIDA_TXT"
fi

if command -v notify-send >/dev/null 2>&1; then
  # cron no conoce la sesión gráfica; se usa la del usuario.
  export DISPLAY="${DISPLAY:-:0}"
  export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
  notify-send -u "$NIVEL" "$TITULO" "$CUERPO" || true
fi
exit "$ESTADO"
