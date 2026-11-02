"""Punto de entrada: python controlador.py"""
import os
import queue
import threading
import time
import tkinter as tk
from collections import Counter

import config
from modelo import duplicados, organizador
from modelo.base_datos import BaseDatos
from modelo.escaner import Escaner
from modelo.opciones import cargar_prefs, crear_opciones, cimas, guardar_prefs
from modelo.utiles import es_descendiente, formatear_tamano, norm
from vista.ventana import ScannerVista
from vista.vista_previa import VistaPrevia


class ScannerControlador:
    def __init__(self, root):
        self.root = root
        self.db = BaseDatos(config.DB_PATH)
        self._cancelar = threading.Event()
        self._cola = queue.Queue()
        self._ultimo_progreso = 0.0
        self._reporte_base = ""
        self.plan = None
        self.op = None
        self.archivos = []
        self._ventana_previa = None
        self.vista = ScannerVista(root, self)
        self.root.after(100, self._revisar_cola)

    def procesar_ruta(self, ruta, recursivo=True):
        ruta = os.path.normpath(ruta)
        escaner = Escaner(self._cancelar)
        if not escaner.verificar_ruta(ruta):
            self.vista.mostrar_error("Error", "El disco o carpeta no existe.")
            return
        if not escaner.validar_permisos(ruta):
            self._guardar(ruta, False, 0, 0)
            self.vista.mostrar_error("Permisos", "No tienes permisos de lectura en esta ruta.")
            return

        self.plan = None
        self.vista.set_plan_disponible(False)
        self._cancelar.clear()
        self.vista.set_ocupado(True)
        self.vista.mostrar_resultado("")
        self._lanzar(self._trabajo_escaneo, escaner, ruta, recursivo)

    def cancelar(self):
        self._cancelar.set()
        self.vista.mostrar_estado("Cancelando...")

    def ver_vista_previa(self):
        if self.plan:
            self._abrir_previa()

    def deshacer(self):
        if not self.db.ultimo_lote_activo():
            self.vista.mostrar_info("Deshacer", "No hay organizaciones para deshacer.")
            return
        if not self.vista.confirmar("Deshacer", "Se devolverán los archivos y carpetas de la última "
                                                "organización a su ubicación original.\n\n¿Continuar?"):
            return
        self.vista.set_ocupado(True, cancelable=False)
        self.vista.mostrar_estado("Deshaciendo...")
        self._lanzar(self._trabajo_deshacer)

    # ================= acciones de la vista previa =================
    def _reconstruir(self):
        if self.plan is None:
            return
        self.plan = organizador.construir_plan(self.plan.raiz, self.archivos, self.plan.grupos, self.op)

    def cambiar_conservado(self, indice_grupo, indice_archivo):
        self.plan.grupos[indice_grupo].indice_conservado = indice_archivo
        self._reconstruir()

    def cambiar_destino(self, clave, ruta):
        ruta = os.path.normpath(ruta.strip()) if ruta.strip() else ""
        if not ruta or not os.path.isabs(ruta):
            return False, "Escribe una ruta completa (por ejemplo C:\\Users\\tu_usuario\\Documentos)."
        self.op.destinos[clave] = ruta
        self._reconstruir()
        return True, ""

    def cambiar_activa(self, clave, valor):
        self.op.activas[clave] = bool(valor)
        self._reconstruir()

    def restablecer_destinos(self):
        self.op.restablecer()
        self._reconstruir()

    def es_protegida(self, carpeta):
        return any(norm(carpeta) == norm(p) or es_descendiente(carpeta, p) for p in self.op.protegidas)

    def mover_carpeta(self, carpeta, destino):
        carpeta, destino = os.path.normpath(carpeta), os.path.normpath(destino.strip())
        if not os.path.isabs(destino):
            return False, "Escribe una ruta de destino completa."
        if norm(carpeta) == norm(self.plan.raiz):
            return False, "No puedes mover la carpeta raíz completa; elige una de sus subcarpetas."
        if norm(destino) == norm(carpeta) or es_descendiente(destino, carpeta):
            return False, "El destino no puede estar dentro de la propia carpeta."
        if norm(os.path.dirname(carpeta)) == norm(destino):
            return False, "La carpeta ya está en ese destino."
        for u in self.op.carpetas_unidad:
            if es_descendiente(carpeta, u):
                return False, f"Esa carpeta ya se mueve junto con «{os.path.basename(u)}»."
        for u in [u for u in self.op.carpetas_unidad if es_descendiente(u, carpeta)]:
            del self.op.carpetas_unidad[u]               # la carpeta mayor reemplaza a las internas
        self.op.carpetas_unidad[carpeta] = destino
        self._reconstruir()
        return True, ""

    def quitar_carpeta(self, carpeta):
        for u in [u for u in self.op.carpetas_unidad if norm(u) == norm(carpeta)]:
            del self.op.carpetas_unidad[u]
        self._reconstruir()

    def alternar_proteccion(self, carpeta):
        existente = [p for p in self.op.protegidas if norm(p) == norm(carpeta)]
        if existente:
            self.op.protegidas.discard(existente[0])
        else:
            for p in self.op.protegidas:
                if es_descendiente(carpeta, p):
                    return False, (f"Esta carpeta está dentro de «{os.path.basename(p)}», que está protegida. "
                                   "Incluye esa carpeta para liberar su contenido.")
            self.op.protegidas.add(carpeta)
        self._reconstruir()
        return True, ""

    def aplicar_plan(self, ventana):
        if not self.plan or not self.plan.movimientos:
            self.vista.mostrar_info("Organización", "No hay nada que mover con la configuración actual.")
            return
        p = self.plan
        detalle = f"{p.n_clasificacion + p.n_duplicados} archivos"
        if p.n_carpetas:
            detalle += f" y {p.n_carpetas} carpetas completas"
        if not self.vista.confirmar("Confirmar organización",
                                    f"Se moverán {detalle}. Nada se borra y podrás deshacerlo.\n\n¿Continuar?",
                                    parent=ventana):
            return
        ventana.destroy()
        try:
            guardar_prefs(self.db, self.op)              # el agente recuerda cómo ordena este usuario
        except Exception as e:
            print(f"No se pudieron guardar las preferencias: {e}")
        self.vista.set_ocupado(True, cancelable=False)
        self.vista.mostrar_estado("Moviendo archivos...")
        self._lanzar(self._trabajo_aplicar, p)

    # ================= hilos de trabajo (nunca tocan Tkinter) =================
    def _lanzar(self, objetivo, *args):
        def envoltura():
            try:
                objetivo(*args)
            except Exception as e:                       # el hilo nunca muere en silencio
                self._cola.put(("error", str(e)))
        threading.Thread(target=envoltura, daemon=True).start()

    def _progreso(self, tipo):
        def cb(hechos, total):
            ahora = time.monotonic()
            if ahora - self._ultimo_progreso > 0.1 or hechos == total:
                self._ultimo_progreso = ahora
                self._cola.put((tipo, hechos, total))
        return cb

    def _trabajo_escaneo(self, escaner, ruta, recursivo):
        res = escaner.escanear(ruta, recursivo,
                               progreso=lambda n, d: self._cola.put(("escaneo_progreso", n, d)))
        self._cola.put(("escaneo_fin", ruta, res))

    def _trabajo_analisis(self, id_escaneo, ruta, archivos, op):
        # Las carpetas protegidas (programas) no se revisan: ahorra mucho tiempo y no se tocarán de todos modos.
        a_revisar = [a for a in archivos
                     if not any(es_descendiente(a.ruta, p) for p in op.protegidas)]
        grupos, hashes = duplicados.detectar(a_revisar, self._cancelar, self._progreso("dup_progreso"))
        if self._cancelar.is_set():
            self._cola.put(("analisis_cancelado",))
            return
        if id_escaneo:
            self.db.actualizar_hashes(id_escaneo, hashes)
        self._cola.put(("plan", organizador.construir_plan(ruta, archivos, grupos, op)))

    def _trabajo_aplicar(self, plan):
        res = organizador.aplicar(plan, self.db, self._progreso("aplicar_progreso"))
        self._cola.put(("aplicar_fin", res))

    def _trabajo_deshacer(self):
        self._cola.put(("deshacer_fin", organizador.deshacer(self.db, self._progreso("aplicar_progreso"))))

    def _trabajo_limpieza(self, carpetas):
        self._cola.put(("limpieza_fin", organizador.eliminar_carpetas_vacias(carpetas)))

    # ================= puente hilo -> interfaz =================
    def _revisar_cola(self):
        try:
            while True:
                msg = self._cola.get_nowait()
                try:
                    self._manejar(msg)
                except Exception as e:
                    print(f"Error en la interfaz: {e}")
        except queue.Empty:
            pass
        self.root.after(100, self._revisar_cola)

    def _manejar(self, msg):
        tipo = msg[0]
        if tipo == "escaneo_progreso":
            self.vista.mostrar_estado(f"Escaneando... {msg[1]} archivos encontrados")
        elif tipo == "escaneo_fin":
            self._escaneo_terminado(msg[1], msg[2])
        elif tipo == "dup_progreso":
            self.vista.mostrar_estado(f"Buscando duplicados... {msg[1]}/{msg[2]} archivos revisados")
        elif tipo == "analisis_cancelado":
            self.vista.set_ocupado(False)
            self.vista.mostrar_estado("Análisis cancelado.")
        elif tipo == "plan":
            self._plan_listo(msg[1])
        elif tipo == "aplicar_progreso":
            self.vista.mostrar_estado(f"Procesando... {msg[1]}/{msg[2]}")
        elif tipo == "aplicar_fin":
            self._aplicacion_terminada(msg[1])
        elif tipo == "deshacer_fin":
            self._deshacer_terminado(*msg[1])
        elif tipo == "limpieza_fin":
            self.vista.set_ocupado(False)
            self.vista.mostrar_estado("Limpieza completada.")
            self.vista.mostrar_info("Carpetas vacías", f"Se eliminaron {msg[1]} carpetas vacías.")
        elif tipo == "error":
            self.vista.set_ocupado(False)
            self.vista.mostrar_error("Error inesperado", msg[1])

    # ================= etapas =================
    def _escaneo_terminado(self, ruta, res):
        if res.cancelado:
            self.vista.set_ocupado(False)
            self.vista.mostrar_estado("Escaneo cancelado.")
            self.vista.mostrar_resultado("Escaneo cancelado. No se guardó ningún registro.")
            return

        self.archivos = res.archivos
        id_escaneo = self._guardar(ruta, True, res.total_carpetas, len(res.archivos), res.archivos)
        protegidas = cimas(os.path.normpath(c) for c in res.carpetas_programa)
        self.op = crear_opciones(ruta, protegidas, cargar_prefs(self.db))

        cuenta = Counter(a.categoria for a in res.archivos)
        lineas = [f"--- RUTA ESCANEADA ---\n{ruta}\n",
                  f"Carpetas encontradas: {res.total_carpetas}",
                  f"Archivos encontrados: {len(res.archivos)}", "", "Por categoría:"]
        lineas += [f"  • {cat}: {n}" for cat, n in cuenta.most_common()]
        if res.omitidos_video:
            lineas.append(f"\nVideos omitidos (fuera de alcance): {res.omitidos_video}")
        if protegidas:
            lineas.append(f"Carpetas protegidas (parecen programas): {len(protegidas)}")
        if res.errores:
            lineas.append(f"Carpetas/archivos sin acceso: {len(res.errores)}")
        lineas.append("\n[✓] Registro guardado en la base de datos." if id_escaneo
                      else "\n[!] No se pudo guardar el registro en la base de datos.")
        self._reporte_base = "\n".join(lineas)
        self.vista.mostrar_resultado(self._reporte_base)

        self.vista.mostrar_estado("Buscando duplicados...")
        self._lanzar(self._trabajo_analisis, id_escaneo, ruta, res.archivos, self.op)

    def _plan_listo(self, plan):
        self.plan = plan
        self.vista.set_ocupado(False)
        self.vista.mostrar_estado("Análisis completado.")
        extra = [f"\nDuplicados: {len(plan.grupos)} grupos "
                 f"(espacio recuperable: {formatear_tamano(plan.espacio_recuperable)})"]
        if plan.movimientos:
            extra.append(f"Organización propuesta: {len(plan.movimientos)} elementos por mover.")
        else:
            extra.append("No hay nada que mover con la configuración actual.")
        self.vista.mostrar_resultado(self._reporte_base + "\n" + "\n".join(extra))
        self.vista.set_plan_disponible(bool(plan.movimientos or plan.grupos or self.op.protegidas))
        if plan.movimientos:
            self._abrir_previa()

    def _abrir_previa(self):
        if self._ventana_previa is not None and self._ventana_previa.winfo_exists():
            self._ventana_previa.lift()
            return
        self._ventana_previa = VistaPrevia(self.root, self)

    def _aplicacion_terminada(self, res):
        raiz = self.plan.raiz
        self.plan = None
        self.vista.set_plan_disponible(False)
        self.vista.set_ocupado(False)
        self.vista.mostrar_estado("Organización aplicada.")
        texto = [f"[✓] Elementos movidos: {res.movidos}",
                 "Puedes revertirlo con «Deshacer última organización»."]
        if res.errores:
            texto.append(f"\n[!] No se pudieron mover {len(res.errores)} elementos:")
            texto += [f"  • {r} ({m})" for r, m in res.errores[:5]]
            if len(res.errores) > 5:
                texto.append(f"  ... y {len(res.errores) - 5} más")
        self.vista.mostrar_resultado("\n".join(texto))

        if res.carpetas_vacias:
            muestra = [os.path.relpath(c, raiz) for c in res.carpetas_vacias[:8]]
            if len(res.carpetas_vacias) > 8:
                muestra.append(f"... y {len(res.carpetas_vacias) - 8} más")
            if self.vista.confirmar(
                    "Carpetas vacías",
                    f"Tras mover los archivos quedaron {len(res.carpetas_vacias)} carpetas vacías:\n\n"
                    + "\n".join(f"  • {m}" for m in muestra)
                    + "\n\n¿Quieres eliminarlas? (No se borra ningún archivo.)"):
                self.vista.set_ocupado(True, cancelable=False)
                self.vista.mostrar_estado("Limpiando carpetas vacías...")
                self._lanzar(self._trabajo_limpieza, res.carpetas_vacias)

    def _deshacer_terminado(self, lote, revertidos, errores):
        self.vista.set_ocupado(False)
        self.vista.mostrar_estado("Deshacer completado.")
        texto = [f"[✓] Elementos devueltos a su lugar: {revertidos}"]
        if errores:
            texto.append(f"\n[!] No se pudieron revertir {len(errores)}:")
            texto += [f"  • {r} ({m})" for r, m in errores[:5]]
        self.vista.mostrar_resultado("\n".join(texto))

    def _guardar(self, ruta, acceso, carpetas, archivos, lista=None):
        """Devuelve el id del escaneo, o None si SQLite falló."""
        try:
            return self.db.registrar_escaneo(ruta, acceso, carpetas, archivos, lista)
        except Exception as e:
            print(f"Error al guardar en SQLite: {e}")
            return None


if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerControlador(root)
    root.mainloop()
