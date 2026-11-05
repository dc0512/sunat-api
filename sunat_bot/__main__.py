"""Uso:

  python -m sunat_bot alertas [--dias 7]
      Lee las alertas de SUNAT del correo (IMAP) y las muestra por empresa. No entra a SOL.

  python -m sunat_bot revisar [--ruc RUC ...] [--desde-correo] [--solo-listar] [--explorar] [--ver]
      Entra al buzón SOL de cada empresa, abre los mensajes nuevos y descarga su contenido.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from . import config as cfgmod
from .almacen import Almacen
from .correo import leer_alertas_imap


def _carpeta_segura(texto: str) -> str:
    return re.sub(r"[^\w.-]+", "_", texto)[:60].strip("_") or "mensaje"


def cmd_alertas(cfg: cfgmod.Config, args: argparse.Namespace) -> int:
    if not cfg.imap:
        print("Falta SUNAT_IMAP_USUARIO y SUNAT_IMAP_CLAVE en el .env.")
        return 2
    almacen = Almacen(cfg.base_datos)
    alertas = leer_alertas_imap(cfg.imap, dias=args.dias)
    nuevas = [a for a in alertas if almacen.guardar_alerta(a)]
    print(f"{len(alertas)} alertas de SUNAT en {args.dias} días, {len(nuevas)} nuevas.")
    for a in sorted(alertas, key=lambda x: x.fecha, reverse=True):
        extra = " ".join(x for x in (
            f"doc {a.documento}" if a.documento else "",
            f"pagar antes del {a.fecha_limite}" if a.fecha_limite else "") if x)
        print(f"{a.fecha[:16]}  {a.ruc}  {a.tipo:<8}  {a.razon_social[:40]:<40}  {extra}")
    pendientes = almacen.rucs_con_alertas_pendientes()
    if pendientes:
        print("\nEmpresas con alertas sin revisar en el buzón:", ", ".join(pendientes))
    almacen.cerrar()
    return 0


def cmd_revisar(cfg: cfgmod.Config, args: argparse.Namespace) -> int:
    from .sol import DetenerBot, NavegadorSOL, navegador  # importa Playwright solo aquí

    almacen = Almacen(cfg.base_datos)
    if args.ruc:
        rucs = args.ruc
    elif args.desde_correo:
        if cfg.imap:
            for a in leer_alertas_imap(cfg.imap, dias=args.dias):
                almacen.guardar_alerta(a)
        rucs = [r for r in almacen.rucs_con_alertas_pendientes() if not cfg.rucs or r in cfg.rucs]
    else:
        rucs = cfg.rucs
    if not rucs:
        print("No hay empresas para revisar.")
        return 0

    codigo = 0
    with navegador(visible=args.ver) as browser:
        for n, ruc in enumerate(rucs):
            cred = cfg.credencial_sol(ruc)
            if not cred:
                print(f"[{ruc}] sin usuario SOL en el .env; se omite.")
                continue
            if n:
                time.sleep(args.pausa)
            contexto = browser.new_context(accept_downloads=True, locale="es-PE")
            page = contexto.new_page()
            explorar = cfg.salida / "exploracion" / ruc if args.explorar else None
            sol = NavegadorSOL(page, cfg.sol_url, explorar)
            try:
                sol.ingresar(cred)
                buzon = sol.abrir_buzon()
                mensajes = sol.listar(buzon, ruc)
                nuevos = [(m, f) for m, f in mensajes if not almacen.existe_mensaje(ruc, m.id_mensaje)]
                print(f"[{ruc}] {len(mensajes)} mensajes en el buzón, {len(nuevos)} nuevos.")
                for m, fila in nuevos[: args.maximo]:
                    if args.solo_listar:
                        print(f"   {m.fecha_deposito}  {m.asunto}")
                        continue
                    carpeta = cfg.salida / ruc / f"{_carpeta_segura(m.fecha_deposito)}_{_carpeta_segura(m.asunto)}"
                    m = sol.abrir_y_descargar(buzon, m, fila, carpeta)
                    almacen.guardar_mensaje(m)
                    print(f"   {m.fecha_deposito}  {m.asunto}  ({len(m.adjuntos)} adjuntos) -> {carpeta}")
                if not args.solo_listar:
                    almacen.marcar_alertas_revisadas(ruc)
                sol.salir()
            except DetenerBot as e:
                codigo = 1
                print(f"[{ruc}] DETENIDO: {e}")
            finally:
                contexto.close()
    almacen.cerrar()
    return codigo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sunat_bot", description="Bot del Buzón Electrónico SOL")
    p.add_argument("--env", default=".env", help="archivo con la configuración (por defecto .env)")
    sub = p.add_subparsers(dest="comando", required=True)

    a = sub.add_parser("alertas", help="leer alertas de SUNAT en el correo")
    a.add_argument("--dias", type=int, default=7)

    r = sub.add_parser("revisar", help="entrar al buzón SOL y descargar mensajes nuevos")
    r.add_argument("--ruc", action="append", help="revisar solo este RUC (se puede repetir)")
    r.add_argument("--desde-correo", action="store_true",
                   help="revisar solo las empresas con alertas nuevas en el correo")
    r.add_argument("--dias", type=int, default=7)
    r.add_argument("--solo-listar", action="store_true",
                   help="listar los mensajes nuevos sin abrirlos (no los marca como leídos)")
    r.add_argument("--explorar", action="store_true",
                   help="guardar capturas y HTML de cada paso para ajustar los selectores")
    r.add_argument("--ver", action="store_true", help="mostrar el navegador")
    r.add_argument("--maximo", type=int, default=50, help="máximo de mensajes a abrir por empresa")
    r.add_argument("--pausa", type=float, default=20.0, help="segundos entre empresas")

    args = p.parse_args(argv)
    cfgmod.cargar_env(args.env)
    cfg = cfgmod.desde_entorno()
    if args.comando == "alertas":
        return cmd_alertas(cfg, args)
    return cmd_revisar(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
