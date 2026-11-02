import tkinter as tk
from tkinter import messagebox, filedialog, ttk


class ScannerVista:
    def __init__(self, root, controlador):
        self.controlador = controlador
        self.root = root
        self._ocupado = False
        self._hay_plan = False
        root.title("Agente IA local - Organizador de archivos")
        root.geometry("600x500")
        root.minsize(520, 440)

        marco = ttk.Frame(root, padding=12)
        marco.pack(fill="both", expand=True)

        ttk.Label(marco, text="Selecciona la carpeta que quieres analizar:").pack(anchor="w")

        fila = ttk.Frame(marco)
        fila.pack(fill="x", pady=8)
        self.btn_seleccionar = ttk.Button(fila, text="Seleccionar carpeta", command=self._seleccionar)
        self.btn_seleccionar.pack(side="left")
        self.btn_cancelar = ttk.Button(fila, text="Cancelar", command=self.controlador.cancelar,
                                       state="disabled")
        self.btn_cancelar.pack(side="left", padx=6)
        self.btn_previa = ttk.Button(fila, text="Ver vista previa", command=self.controlador.ver_vista_previa,
                                     state="disabled")
        self.btn_previa.pack(side="left", padx=6)
        self.btn_deshacer = ttk.Button(fila, text="Deshacer última organización",
                                       command=self.controlador.deshacer)
        self.btn_deshacer.pack(side="right")

        self.var_recursivo = tk.BooleanVar(value=True)
        ttk.Checkbutton(marco, text="Incluir subcarpetas", variable=self.var_recursivo).pack(anchor="w")

        self.barra = ttk.Progressbar(marco, mode="indeterminate")
        self.barra.pack(fill="x", pady=8)
        self.var_estado = tk.StringVar(value="Listo.")
        ttk.Label(marco, textvariable=self.var_estado).pack(anchor="w")

        self.txt = tk.Text(marco, height=14, wrap="char", state="disabled")
        self.txt.pack(fill="both", expand=True, pady=(8, 0))

    def _seleccionar(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.controlador.procesar_ruta(ruta, self.var_recursivo.get())

    def _estado_botones(self):
        self.btn_seleccionar.config(state="disabled" if self._ocupado else "normal")
        self.btn_deshacer.config(state="disabled" if self._ocupado else "normal")
        self.btn_previa.config(state="normal" if (self._hay_plan and not self._ocupado) else "disabled")

    def set_ocupado(self, ocupado: bool, cancelable: bool = True):
        self._ocupado = ocupado
        self._estado_botones()
        self.btn_cancelar.config(state="normal" if (ocupado and cancelable) else "disabled")
        if ocupado:
            self.barra.config(mode="indeterminate")
            self.barra.start(12)
        else:
            self.barra.stop()
            self.barra.config(mode="determinate", value=0)

    def set_plan_disponible(self, hay_plan: bool):
        self._hay_plan = hay_plan
        self._estado_botones()

    def mostrar_estado(self, texto):
        self.var_estado.set(texto)

    def mostrar_resultado(self, mensaje):
        self.txt.config(state="normal")
        self.txt.delete("1.0", tk.END)
        self.txt.insert(tk.END, mensaje)
        self.txt.config(state="disabled")

    def mostrar_error(self, titulo, mensaje):
        messagebox.showerror(titulo, mensaje)

    def mostrar_info(self, titulo, mensaje):
        messagebox.showinfo(titulo, mensaje)

    def confirmar(self, titulo, mensaje, parent=None):
        return messagebox.askyesno(titulo, mensaje, parent=parent or self.root)
