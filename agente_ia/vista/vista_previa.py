import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config
from modelo import organizador
from modelo.opciones import accesos_rapidos, claves_destino
from modelo.utiles import es_descendiente, formatear_tamano, norm
class ToolTip:
    def __init__(self, widget, text):
        self.tipwindow = None


class VistaPrevia(tk.Toplevel):
    """Vista previa interactiva: qué se mueve, qué duplicado se conserva, dónde va cada cosa."""

    def __init__(self, root, controlador):
        super().__init__(root)
        self.c = controlador
        self.title("Vista previa de la organización")
        self.geometry("920x600")
        self.minsize(720, 460)
        self.transient(root)
        self._accesos = accesos_rapidos()

        self.var_resumen = tk.StringVar()
        ttk.Label(self, textvariable=self.var_resumen, padding=10, justify="left").pack(anchor="w")

        # Los botones se empaquetan primero abajo para que nunca queden tapados al achicar la ventana
        botones = ttk.Frame(self, padding=10)
        botones.pack(side="bottom", fill="x")
        ttk.Button(botones, text="Aplicar organización", command=self._aplicar).pack(side="right")
        ttk.Button(botones, text="Cerrar", command=self.destroy).pack(side="right", padx=6)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10)
        self._tab_movimientos()
        self._tab_duplicados()
        self._tab_destinos()
        self._tab_carpetas()
        self._refrescar_todo()

    # ------------------------------------------------------------------ utilidades
    @property
    def plan(self):
        return self.c.plan

    @property
    def op(self):
        return self.c.op

    @staticmethod
    def _crear_tree(parent, columnas, titulos, anchos, con_arbol=False):
        marco = ttk.Frame(parent)
        marco.pack(fill="both", expand=True)
        tree = ttk.Treeview(marco, columns=columnas, show="tree headings" if con_arbol else "headings")
        for col, t, w in zip(columnas, titulos, anchos):
            tree.heading(col, text=t)
            tree.column(col, width=w, anchor="w", stretch=(col == columnas[-1]))
        vs = ttk.Scrollbar(marco, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(marco, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)
        return tree

    def _rel(self, ruta):
        try:
            return os.path.relpath(ruta, self.plan.raiz)
        except ValueError:
            return ruta

    def _aviso(self, texto):
        messagebox.showinfo("Aviso", texto, parent=self)

    # ------------------------------------------------------------------ pestaña Movimientos
    def _tab_movimientos(self):
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="Movimientos")
        self.tree_mov = self._crear_tree(tab, ("motivo", "origen", "destino"),
                                         ("Motivo", "Desde", "Hacia"), (120, 330, 340))

    def _refrescar_movimientos(self):
        self.tree_mov.delete(*self.tree_mov.get_children())
        nombres = {"duplicado": "Duplicado", "carpeta": "Carpeta completa", "clasificacion": "Clasificación"}
        for m in self.plan.movimientos:
            destino = m.destino if os.path.isabs(m.destino) and not es_descendiente(m.destino, self.plan.raiz) \
                else self._rel(m.destino)
            self.tree_mov.insert("", "end", values=(nombres[m.motivo], self._rel(m.origen), destino))

    # ------------------------------------------------------------------ pestaña Duplicados
    def _tab_duplicados(self):
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="Duplicados")
        ttk.Label(tab, text="Doble clic en un archivo para elegir cuál conservar. "
                            "Las demás copias irán a la carpeta de duplicados.").pack(anchor="w", pady=(0, 4))
        self.tree_dup = self._crear_tree(tab, ("estado", "tamano", "ruta"),
                                         ("Acción", "Tamaño", "Ruta"), (200, 80, 450), con_arbol=True)
        self.tree_dup.heading("#0", text="Grupo")
        self.tree_dup.column("#0", width=140, stretch=False)
        self.tree_dup.bind("<Double-1>", self._doble_clic_dup)
        grupos = self.plan.grupos
        for gi, g in enumerate(grupos):
            padre = self.tree_dup.insert("", "end", iid=f"g{gi}", open=len(grupos) <= 15,
                                         text=f"Grupo {gi + 1}: {len(g.archivos)} copias")
            for ai, a in enumerate(g.archivos):
                self.tree_dup.insert(padre, "end", iid=f"g{gi}_{ai}", values=("", formatear_tamano(a.tamano), a.ruta))

    def _estado_dup(self, g, i):
        a = g.archivos[i]
        if i == g.indice_conservado:
            return "✓ Conservar"
        if a.ruta in self.plan.se_queda:
            return f"Se queda ({self.plan.se_queda[a.ruta]})"
        return "→ Duplicados"

    def _refrescar_duplicados(self):
        for gi, g in enumerate(self.plan.grupos):
            for ai, a in enumerate(g.archivos):
                self.tree_dup.item(f"g{gi}_{ai}",
                                   values=(self._estado_dup(g, ai), formatear_tamano(a.tamano), a.ruta))

    def _doble_clic_dup(self, event):
        iid = self.tree_dup.identify_row(event.y)
        if not iid or "_" not in iid:
            return
        gi, ai = (int(x) for x in iid[1:].split("_"))
        self.c.cambiar_conservado(gi, ai)
        self._refrescar_todo()

    # ------------------------------------------------------------------ pestaña Destinos
# -------------------------------------------------------- pestaña Destinos
    def _tab_destinos(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Destinos")
        tab.columnconfigure(2, weight=1)

        # 1. TEXTO INSTRUCTIVO RESUMIDO
        instrucciones = "Configura la ruta de destino. Desmarca la casilla para dejar un tipo de archivo en su lugar original."
        ttk.Label(tab, wraplength=840, justify="left", text=instrucciones).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        # 2. ENCABEZADOS DE COLUMNA
        ttk.Label(tab, text="Categoría", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Label(tab, text="Activar", font=("Segoe UI", 9, "bold")).grid(row=1, column=1, padx=4, pady=5)
        ttk.Label(tab, text="Ruta de Destino", font=("Segoe UI", 9, "bold")).grid(row=1, column=2, sticky="w", padx=4, pady=5)
        
        # 3. LÍNEA SEPARADORA
        ttk.Separator(tab, orient='horizontal').grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        self._vars_destino, self._vars_activa = {}, {}
        
        # Usamos start=3 porque las filas 0, 1 y 2 ahora están ocupadas por instrucciones y encabezados
        for fila, clave in enumerate(claves_destino(), start=3):
            etiqueta = "Duplicados" if clave == config.CARPETA_DUPLICADOS else clave
            ttk.Label(tab, text=etiqueta).grid(row=fila, column=0, sticky="w", padx=(0, 10), pady=6)

            if clave != config.CARPETA_DUPLICADOS:
                va = tk.BooleanVar(value=self.op.activas[clave])
                # Checkbutton SIN el texto "Mover" y con más espacio vertical (pady=6)
                ttk.Checkbutton(tab, variable=va, command=lambda c=clave: self._cambio_activa(c)).grid(row=fila, column=1, padx=4, pady=6)
                self._vars_activa[clave] = va

            vd = tk.StringVar(value=self.op.destinos[clave])
            cmb = ttk.Combobox(tab, textvariable=vd, values=[self.op.destino_defecto(clave)] + self._accesos)
            cmb.grid(row=fila, column=2, sticky="ew", padx=4, pady=6)
            
            # TOOLTIP: Muestra la ruta completa al pasar el ratón por el Combobox
            ToolTip(cmb, text=f"Ruta actual asignada:\n{vd.get()}")

            for ev in ("<<ComboboxSelected>>", "<Return>", "<FocusOut>"):
                cmb.bind(ev, lambda e, c=clave: self._cambio_destino(c))
                
            ttk.Button(tab, text="Examinar...", command=lambda c=clave: self._examinar_destino(c)).grid(row=fila, column=3, padx=(4, 0), pady=6)
            self._vars_destino[clave] = vd

        # Ajustamos la fila del botón final sumando 3 por los nuevos encabezados
        ttk.Button(tab, text="Restablecer valores predeterminados", command=self._restablecer).grid(row=len(claves_destino()) + 3, column=0, columnspan=4, sticky="e", pady=12)

    def _cambio_activa(self, clave):
        self.c.cambiar_activa(clave, self._vars_activa[clave].get())
        self._refrescar_todo()

    def _cambio_destino(self, clave):
        texto = self._vars_destino[clave].get().strip()
        if norm(texto or ".") == norm(self.op.destinos[clave]):
            return
        ok, msg = self.c.cambiar_destino(clave, texto)
        self._vars_destino[clave].set(self.op.destinos[clave])   # primero restaura (evita avisos en bucle)
        if not ok:
            self._aviso(msg)
        self._refrescar_todo()

    def _examinar_destino(self, clave):
        actual = self.op.destinos[clave]
        ruta = filedialog.askdirectory(parent=self, initialdir=actual if os.path.isdir(actual) else None)
        if ruta:
            self._vars_destino[clave].set(ruta)
            self._cambio_destino(clave)

    def _restablecer(self):
        self.c.restablecer_destinos()
        self._refrescar_todo()

    def _sincronizar_destinos(self):
        """Aplica lo que haya quedado escrito en los campos aunque no se haya confirmado con Enter."""
        for clave in self._vars_destino:
            self._cambio_destino(clave)

    def _refrescar_destinos(self):
        for clave, var in self._vars_destino.items():
            if var.get() != self.op.destinos[clave]:
                var.set(self.op.destinos[clave])
        for clave, var in self._vars_activa.items():
            if var.get() != self.op.activas[clave]:
                var.set(self.op.activas[clave])

    # ------------------------------------------------------------------ pestaña Carpetas
    def _tab_carpetas(self):
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="Carpetas")

        # controles abajo (se empaquetan primero para que no se corten)
        nota = ("Las carpetas protegidas no se tocan. Si incluyes una, sus archivos se ordenan por categoría, "
                "pero no se revisan en busca de duplicados.")
        ttk.Label(tab, text=nota, wraplength=840, justify="left").pack(side="bottom", anchor="w", pady=(4, 0))
        fila2 = ttk.Frame(tab)
        fila2.pack(side="bottom", fill="x", pady=4)
        ttk.Button(fila2, text="Mover carpeta completa a ese destino", command=self._mover_carpeta).pack(side="left")
        ttk.Button(fila2, text="Dejar de mover", command=self._quitar_carpeta).pack(side="left", padx=6)
        ttk.Button(fila2, text="Proteger / Incluir", command=self._alternar_proteccion).pack(side="left")
        fila1 = ttk.Frame(tab)
        fila1.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Label(fila1, text="Destino:").pack(side="left")
        self.var_dest_carpeta = tk.StringVar()
        ttk.Combobox(fila1, textvariable=self.var_dest_carpeta, values=self._accesos
                     ).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(fila1, text="Examinar…", command=self._examinar_carpeta).pack(side="left")

        ttk.Label(tab, text="Selecciona una carpeta y muévela completa a otro lugar, o protégela / inclúyela."
                  ).pack(anchor="w", pady=(0, 4))
        self.tree_car = self._crear_tree(tab, ("estado",), ("Estado",), (420,), con_arbol=True)
        self.tree_car.heading("#0", text="Carpeta")
        self.tree_car.column("#0", width=330, stretch=False)

        raiz = self.plan.raiz
        carpetas = {raiz}
        for a in self.c.archivos:
            d = os.path.dirname(a.ruta)
            while es_descendiente(d, raiz):
                carpetas.add(d)
                d = os.path.dirname(d)
        self._iid_por_ruta, self._ruta_por_iid = {}, {}
        for i, ruta in enumerate(sorted(carpetas, key=lambda p: (p.count(os.sep), p.lower()))):
            iid = f"d{i}"
            es_raiz = norm(ruta) == norm(raiz)
            padre = "" if es_raiz else self._iid_por_ruta.get(norm(os.path.dirname(ruta)), "")
            self.tree_car.insert(padre, "end", iid=iid, open=es_raiz or padre == "",
                                 text=ruta if es_raiz else os.path.basename(ruta), values=("",))
            self._iid_por_ruta[norm(ruta)] = iid
            self._ruta_por_iid[iid] = ruta

    def _refrescar_carpetas(self):
        for iid, ruta in self._ruta_por_iid.items():
            self.tree_car.set(iid, "estado", organizador.estado_carpeta(ruta, self.op))

    def _carpeta_seleccionada(self):
        sel = self.tree_car.selection()
        if not sel:
            self._aviso("Selecciona primero una carpeta de la lista.")
            return None
        return self._ruta_por_iid[sel[0]]

    def _examinar_carpeta(self):
        ruta = filedialog.askdirectory(parent=self)
        if ruta:
            self.var_dest_carpeta.set(ruta)

    def _mover_carpeta(self):
        carpeta = self._carpeta_seleccionada()
        if not carpeta:
            return
        destino = self.var_dest_carpeta.get().strip()
        if not destino:
            self._aviso("Escribe o elige el destino al que quieres mover la carpeta.")
            return
        if self.c.es_protegida(carpeta) and not messagebox.askyesno(
                "Carpeta protegida",
                "Esta carpeta parece un programa instalado. Moverla puede romper sus accesos directos.\n\n"
                "¿Quieres moverla de todos modos?", parent=self):
            return
        ok, msg = self.c.mover_carpeta(carpeta, destino)
        if not ok:
            self._aviso(msg)
        self._refrescar_todo()

    def _quitar_carpeta(self):
        carpeta = self._carpeta_seleccionada()
        if carpeta:
            self.c.quitar_carpeta(carpeta)
            self._refrescar_todo()

    def _alternar_proteccion(self):
        carpeta = self._carpeta_seleccionada()
        if not carpeta:
            return
        ok, msg = self.c.alternar_proteccion(carpeta)
        if not ok:
            self._aviso(msg)
        self._refrescar_todo()

    # ------------------------------------------------------------------ resumen y refresco global
    def _refrescar_resumen(self):
        p = self.plan
        lineas = [f"Se moverán {len(p.movimientos)} elementos: {p.n_clasificacion} archivos a su categoría, "
                  f"{p.n_duplicados} duplicados y {p.n_carpetas} carpetas completas.",
                  f"Grupos de duplicados: {len(p.grupos)}  ·  Espacio recuperable: "
                  f"{formatear_tamano(p.espacio_recuperable)}"]
        if self.op.protegidas:
            lineas.append(f"Carpetas protegidas: {len(self.op.protegidas)} (no se tocan).")
        self.var_resumen.set("\n".join(lineas))

    def _refrescar_todo(self):
        self._refrescar_movimientos()
        self._refrescar_duplicados()
        self._refrescar_destinos()
        self._refrescar_carpetas()
        self._refrescar_resumen()

    def _aplicar(self):
        self._sincronizar_destinos()
        self.c.aplicar_plan(self)