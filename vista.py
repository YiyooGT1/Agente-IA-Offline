import tkinter as tk
from tkinter import filedialog, messagebox

class ScannerVista:
    def __init__(self, root, controlador):
        self.controlador = controlador
        self.root = root
        self.root.title("Agente IA - Skill Scanner")
        self.root.geometry("400x300")

        # Elementos de la interfaz
        tk.Label(root, text="Seleccione un disco o carpeta a escanear:").pack(pady=10)
        
        self.btn_seleccionar = tk.Button(root, text="Seleccionar Ruta", command=self.seleccionar_ruta)
        self.btn_seleccionar.pack(pady=5)

        self.txt_resultados = tk.Text(root, height=10, width=45)
        self.txt_resultados.pack(pady=10)

    def seleccionar_ruta(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.controlador.procesar_ruta(ruta)

    def mostrar_resultado(self, mensaje):
        self.txt_resultados.delete(1.0, tk.END)
        self.txt_resultados.insert(tk.END, mensaje)

    def mostrar_error(self, titulo, mensaje):
        messagebox.showerror(titulo, mensaje)