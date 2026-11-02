import os
import mysql.connector
from mysql.connector import Error

class ScannerModelo:
    def __init__(self):
        # Configura aquí tus credenciales locales de MySQL
        self.host = "localhost"
        self.user = "root"      # Tu usuario de MySQL
        self.password = ""      # Tu contraseña de MySQL (déjalo vacío si usas XAMPP por defecto)
        self.database = "db_agente_ia"

    def verificar_ruta(self, ruta):
        return os.path.exists(ruta)
        
    def validar_permisos(self, ruta):
        return os.access(ruta, os.R_OK)

    def leer_contenido(self, ruta):
        resultado = {"carpetas": [], "archivos": []}
        try:
            for elemento in os.listdir(ruta):
                ruta_completa = os.path.join(ruta, elemento)
                if os.path.isdir(ruta_completa):
                    resultado["carpetas"].append(elemento)
                else:
                    resultado["archivos"].append(elemento)
        except PermissionError:
            pass 
        return resultado

    # --- NUEVA FUNCIÓN PARA EL PUNTO 14 ---
    def guardar_registro_db(self, ruta, acceso, carpetas, archivos):
        try:
            # 1. Establecer conexión
            conexion = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            
            if conexion.is_connected():
                cursor = conexion.cursor()
                # 2. Preparar la consulta SQL (Evita inyección SQL usando %s)
                sql = """INSERT INTO log_escaneos 
                         (ruta_analizada, acceso_permitido, total_carpetas, total_archivos) 
                         VALUES (%s, %s, %s, %s)"""
                
                # 3. Asignar los valores y ejecutar
                valores = (ruta, acceso, carpetas, archivos)
                cursor.execute(sql, valores)
                
                # 4. Confirmar los cambios en la BD
                conexion.commit()
                
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            
        finally:
            # 5. Cerrar la conexión siempre, ocurra o no un error
            if 'conexion' in locals() and conexion.is_connected():
                cursor.close()
                conexion.close()