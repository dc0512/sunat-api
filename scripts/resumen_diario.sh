#!/usr/bin/env bash
# Corre el resumen diario de alertas SUNAT. Pensado para cron: no depende de la carpeta actual
# ni de variables del usuario. Deja un registro en <salida>/resumen.log y, si hay escritorio,
# muestra una notificación con las urgencias.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"
SALIDA="$(grep -E '^SUNAT_SALIDA=' .env 2>/dev/null | cut -d= -f2- || true)"
SALIDA="${SALIDA:-salida}"
mkdir -p "$SALIDA"
LOG="$SALIDA/resumen.log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
  if "$DIR/.venv/bin/python" -m sunat_bot --env "$DIR/.env" resumen --dias 30 > "$SALIDA/ultimo-resumen.txt" 2>&1; then
    echo "OK"
  else
    echo "ERROR (ver $SALIDA/ultimo-resumen.txt)"
  fi
} >> "$LOG" 2>&1

URGENTES="$(sed -n '/^## Urgente/,/^## /p' "$SALIDA/ultimo-resumen.txt" | grep '^- ' | wc -l || true)"
if command -v notify-send >/dev/null 2>&1; then
  # cron no conoce la sesión gráfica; se intenta con la del usuario.
  export DISPLAY="${DISPLAY:-:0}"
  export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
  if [ "${URGENTES:-0}" -gt 0 ]; then
    notify-send -u critical "SUNAT: $URGENTES urgencia(s)" "Revisa $DIR/$SALIDA/resumen-$(date +%F).md" || true
  else
    notify-send "SUNAT: sin urgencias" "Resumen en $DIR/$SALIDA/resumen-$(date +%F).md" || true
  fi
fi
