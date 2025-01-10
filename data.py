import pandas as pd
import mysql.connector


archivo_excel = "db.xlsx"
df = pd.read_excel(archivo_excel)
# Reemplazar valores inválidos en las columnas con valores predeterminados
df = df.replace('-', 0)  # Reemplazar '-' con 0
df = df.fillna(0)  # Reemplazar NaN con 0
# Reemplazar valores inválidos en columnas de tipo DATE con NULL
# Convertir columnas de fecha a formato datetime, manejando errores
df['Inicio'] = pd.to_datetime(df['Inicio'], errors='coerce')  # Convierte fechas inválidas a NaT
df['Fin'] = pd.to_datetime(df['Fin'], errors='coerce')  # Convierte fechas inválidas a NaT

# Verifica los cambios
print(df[['Inicio', 'Fin']].head())

print(df.head())

conexion = mysql.connector.connect(
    host="localhost",
    user="root",  # Cambia esto por tu usuario de MySQL
    password="Puma2020!",  # Cambia esto por tu contraseña
    database="DEMEX"  # Cambia esto por el nombre de tu base de datos
)



cursor = conexion.cursor()

# Crear la tabla si no existe
crear_tabla = """
CREATE TABLE IF NOT EXISTS proyectos (
    Year INT,
    ID INT PRIMARY KEY,
    Tipo VARCHAR(100),
    Proyecto VARCHAR(255),
    Mes VARCHAR(50),
    M2 DECIMAL(10, 2),
    Inicio DATE,
    Fin DATE,
    Dias INT,
    Analista VARCHAR(100),
    Dibujante VARCHAR(100),
    ND INT,
    MC INT,
    Planos INT,
    Costo_MC DECIMAL(10, 2),
    Costo_Planos DECIMAL(10, 2),
    pMC DECIMAL(10, 6),
    pPlanos DECIMAL(10, 6),
    pTotal DECIMAL(10, 6)
);
"""
cursor.execute(crear_tabla)
conexion.commit()

# Insertar los datos
insertar_datos = """
INSERT INTO proyectos (
    Year, ID, Tipo, Proyecto, Mes, M2, Inicio, Fin, Dias, Analista, Dibujante, ND, MC, Planos, Costo_MC, Costo_Planos, pMC, pPlanos, pTotal
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

for _, fila in df.iterrows():
    datos = (
        fila['Year'], fila['ID'], fila['Tipo'], fila['Proyecto'], fila['Mes'],
        fila['M2'], 
        fila['Inicio'] if pd.notnull(fila['Inicio']) else None,  # Manejar NaT como None
        fila['Fin'] if pd.notnull(fila['Fin']) else None,        # Manejar NaT como None
        fila['Dias'], fila['Analista'], fila['Dibujante'], fila['ND'],
        fila['MC'], fila['Planos'], fila['Costo MC'], fila['Costo Planos'],
        fila['pMC'], fila['pPlanos'], fila['pTotal']
    )
    try:
        # Verificar si el ID ya existe
        cursor.execute("SELECT COUNT(*) FROM proyectos WHERE ID = %s", (fila['ID'],))
        if cursor.fetchone()[0] > 0:
            print(f"ID duplicado: {fila['ID']}, omitiendo inserción.")
            continue
        
        # Intentar insertar la fila
        cursor.execute(insertar_datos, datos)
    except mysql.connector.Error as err:
        print(f"Error al insertar la fila {fila['ID']}: {err}")


conexion.commit()

print(f"Datos insertados exitosamente. Total filas: {len(df)}")

# Verificar los datos insertados
cursor.execute("SELECT COUNT(*) FROM proyectos")
conteo = cursor.fetchone()[0]
print(f"Total de filas en la tabla 'proyectos': {conteo}")

# Cerrar la conexión
cursor.close()
conexion.close()