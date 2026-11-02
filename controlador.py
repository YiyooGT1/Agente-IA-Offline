import tkinter as tk
from modelo import ScannerModelo
from vista import ScannerVista

class ScannerControlador:
    def __init__(self, root):
        # Instanciamos el Modelo (Lógica y BD) y la Vista (Interfaz Tkinter)
        self.modelo = ScannerModelo()
        self.vista = ScannerVista(root, self)

    def procesar_ruta(self, ruta):
        # 1. Validar Detección
        if not self.modelo.verificar_ruta(ruta):
            self.vista.mostrar_error("Error", "El disco o carpeta no existe.")
            return

        # 2. Validar Permisos
        tiene_permiso = self.modelo.validar_permisos(ruta)
        if not tiene_permiso:
            # Registramos en MySQL el intento de acceso fallido
            self.modelo.guardar_registro_db(ruta, False, 0, 0)
            self.vista.mostrar_error("Permisos", "No tienes permisos de lectura en esta ruta.")
            return

        # 3. Leer Carpetas y Archivos
        contenido = self.modelo.leer_contenido(ruta)
        total_carpetas = len(contenido['carpetas'])
        total_archivos = len(contenido['archivos'])
        
        # 4. Guardar resultados exitosos en MySQL
        self.modelo.guardar_registro_db(ruta, True, total_carpetas, total_archivos)
        
        # 5. Formatear el reporte visual para mostrarlo en la ventana
        reporte = f"--- RUTA ESCANEADA ---\n{ruta}\n\n"
        reporte += f"Carpetas encontradas: {total_carpetas}\n"
        reporte += f"Archivos encontrados: {total_archivos}\n"
        reporte += "\n[✓] Registro guardado en la Base de Datos exitosamente."
        
        # Enviar la información a la vista
        self.vista.mostrar_resultado(reporte)

# Punto de entrada principal de la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerControlador(root)
    root.mainloop()