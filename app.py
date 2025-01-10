from flask import Flask, request, jsonify, send_from_directory
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()  # Cargar las variables desde .env

app = Flask(__name__)  # Mantén solo una instancia de app

# Configuración de la conexión a MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),        # Desde el archivo .env
        user=os.getenv('DB_USER'),        # Desde el archivo .env
        password=os.getenv('DB_PASSWORD'),# Desde el archivo .env
        database=os.getenv('DB_NAME')     # Desde el archivo .env
    )


# Ruta para añadir un nuevo proyecto
@app.route('/proyectos', methods=['POST'])
@app.route('/proyectos', methods=['POST'])
@app.route('/proyectos', methods=['POST'])
def agregar_proyecto():
    datos = request.json

    # Obtener el siguiente ID automáticamente
    conexion = get_db_connection()
    cursor = conexion.cursor()
    cursor.execute("SELECT MAX(ID) + 1 AS next_id FROM proyectos")
    next_id = cursor.fetchone()[0] or 1  # Si no hay registros, asigna el ID 1

    # Calcular "Días"
    inicio = datos.get("Inicio")
    fin = datos.get("Fin")
    dias = None
    if inicio and fin:
        dias = (datetime.strptime(fin, '%Y-%m-%d') - datetime.strptime(inicio, '%Y-%m-%d')).days

    # Calcular "ND"
    analista = datos.get("Analista")
    dibujante = datos.get("Dibujante")
    nd = 1 if analista == dibujante else 2

    # Calcular "Costo MC"
    mc = datos.get("MC", 0)
    costo_mc = mc * 8

    # Calcular "Costo Planos"
    planos = datos.get("Planos", 0)
    costo_planos = planos * 25

    # Calcular "pMC"
    m2 = datos.get("M2", 0)
    pmc = costo_mc / (m2 * 50) if m2 > 0 else 0

    # Calcular "pPlanos"
    pplanos = costo_planos / (m2 * 50) if m2 > 0 else 0

    # Calcular "pTotal"
    ptotal = (costo_mc + costo_planos) / (m2 * 50) if m2 > 0 else 0

    try:
        insertar_proyecto = """
        INSERT INTO proyectos (ID, Year, Tipo, Proyecto, Mes, M2, Inicio, Fin, Dias, Analista, Dibujante, ND, MC, Planos, Costo_MC, Costo_Planos, pMC, pPlanos, pTotal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insertar_proyecto, (
            next_id, datos['Year'], datos['Tipo'], datos['Proyecto'], datos['Mes'],
            m2, inicio, fin, dias, analista, dibujante, nd, mc, planos, costo_mc,
            costo_planos, pmc, pplanos, ptotal
        ))
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({"mensaje": "Proyecto añadido exitosamente", "id": next_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400



# Ruta para obtener todos los proyectos
@app.route('/proyectos', methods=['GET'])
def obtener_proyectos():
    conexion = get_db_connection()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM proyectos")
    proyectos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return jsonify(proyectos)

@app.route('/proyectos/<int:id>', methods=['DELETE'])
def eliminar_proyecto(id):
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM proyectos WHERE ID = %s", (id,))
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({"mensaje": "Proyecto eliminado exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/proyectos/<int:id>', methods=['PUT'])
def editar_proyecto(id):
    datos = request.json
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        actualizar_proyecto = """
        UPDATE proyectos
        SET Year = %s, Tipo = %s, Proyecto = %s, Mes = %s, M2 = %s, Inicio = %s,
            Fin = %s, Analista = %s, Dibujante = %s, MC = %s, Planos = %s
        WHERE ID = %s
        """
        cursor.execute(actualizar_proyecto, (
            datos['Year'], datos['Tipo'], datos['Proyecto'], datos['Mes'],
            datos['M2'], datos['Inicio'], datos['Fin'], datos['Analista'],
            datos['Dibujante'], datos['MC'], datos['Planos'], id
        ))
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({"mensaje": "Proyecto actualizado exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/rendimiento', methods=['GET'])
def analizar_rendimiento():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT Analista, Dibujante, Dias, M2
            FROM proyectos
            WHERE Dias > 0 AND M2 > 0
        """)
        proyectos = cursor.fetchall()
        cursor.close()
        conexion.close()

        # Calcular rendimiento, dividiendo múltiples trabajadores
        rendimiento = {}
        for proyecto in proyectos:
            trabajadores = []

            # Dividir analistas y dibujantes si están separados por comas
            if proyecto['Analista']:
                trabajadores.extend([a.strip() for a in proyecto['Analista'].split('/')])
            if proyecto['Dibujante']:
                trabajadores.extend([d.strip() for d in proyecto['Dibujante'].split('/')])

            # Calcular rendimiento para cada trabajador válido
            for trabajador in trabajadores:
                if not trabajador or trabajador == "0":  # Descartar si es vacío o "0"
                    continue
                if trabajador not in rendimiento:
                    rendimiento[trabajador] = []
                rendimiento[trabajador].append(proyecto['M2'] / proyecto['Dias'])

        # Calcular estadísticas del rendimiento
        estadisticas = []
        for trabajador, valores in rendimiento.items():
            estadisticas.append({
                "trabajador": trabajador,
                "maximo": max(valores),      # Máximo rendimiento (M2/Día)
                "minimo": min(valores),      # Mínimo rendimiento (M2/Día)
                "promedio": sum(valores) / len(valores)  # Promedio rendimiento (M2/Día)
            })

        return jsonify(estadisticas), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/trabajador/<nombre>', methods=['GET'])
def obtener_proyectos_trabajador(nombre):
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        # Obtener proyectos del trabajador
        cursor.execute("""
            SELECT Year, ID, Proyecto, Dias, M2, (M2 / Dias) AS Rendimiento
            FROM proyectos
            WHERE (Analista LIKE %s OR Dibujante LIKE %s) AND Dias > 0 AND M2 > 0
        """, (f"%{nombre}%", f"%{nombre}%"))
        proyectos = cursor.fetchall()

        if not proyectos:
            return jsonify({"proyectos": [], "porcentaje_efectividad": 0.0}), 200
        
        # Calcular el mínimo rendimiento
        cursor.execute("SELECT Total_Anual / 365 AS ganancia_diaria FROM nominas WHERE Nombre = %s", (nombre,))
        trabajador_data = cursor.fetchone()

        if not trabajador_data:
            return jsonify({"error": "No se encontró al trabajador"}), 404

        ganancia_diaria = trabajador_data['ganancia_diaria']

        # Obtener el PU Límite
        cursor.execute("""
            SELECT 50 - AVG(MC / M2) AS pu_limite
            FROM proyectos
            WHERE M2 > 0
        """)
        pu_limite_data = cursor.fetchone()
        pu_limite = pu_limite_data['pu_limite'] if pu_limite_data else None

        if pu_limite is None:
            return jsonify({"error": "No se pudo calcular el PU Límite"}), 500

        minimo_rendimiento = ganancia_diaria / pu_limite

        # Calcular la efectividad
        proyectos_cumplen = [p for p in proyectos if p['Rendimiento'] >= minimo_rendimiento]
        total_proyectos = len(proyectos)
        proyectos_cumplen_total = len(proyectos_cumplen)
        porcentaje_efectividad = (proyectos_cumplen_total / total_proyectos) * 100 if total_proyectos > 0 else 0

        # Añadir estado de cumplimiento a cada proyecto
        for proyecto in proyectos:
            proyecto['cumple_minimo'] = proyecto['Rendimiento'] >= minimo_rendimiento

        # Calcular estadísticas adicionales
        rendimientos = [float(proyecto['Rendimiento']) for proyecto in proyectos if proyecto['Rendimiento'] is not None]
        max_rendimiento = max(rendimientos, default=0)
        min_rendimiento = min(rendimientos, default=0)
        promedio_rendimiento = sum(rendimientos) / len(rendimientos) if rendimientos else 0

        cursor.close()
        conexion.close()

        return jsonify({
            "proyectos": proyectos,
            "minimo_rendimiento": minimo_rendimiento,
            "estadisticas": {
                "maximo": max_rendimiento,
                "minimo": min_rendimiento,
                "promedio": promedio_rendimiento,
                "efectividad": porcentaje_efectividad,
                "total_proyectos": total_proyectos,
                "proyectos_efectivos": proyectos_cumplen_total
            }
        }), 200

    except Exception as e:
        print(f"Error en la consulta: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/reporte', methods=['GET'])
def generar_reporte():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT COUNT(*) as total_proyectos,
                   AVG(M2) as promedio_m2,
                   AVG(Dias) as promedio_dias
            FROM proyectos
        """)
        resumen = cursor.fetchone()
        cursor.close()
        conexion.close()

        return jsonify(resumen), 200

    except Exception as e:
        print(f"Error al generar reporte: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/analisis-producto', methods=['GET'])
def analisis_producto():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                Proyecto,
                M2,
                MC,
                (MC / M2) AS Pag_por_M2,
                (MC * 8 + 50) AS Costo_MC_por_M2,
                Planos,
                (Planos / M2) AS Planos_por_M2,
                (Planos * 25 + 150) AS Costo_Planos,
                ROUND((Costo_MC / (M2 * 50)) * 100) AS Porcentaje_MC,
                ROUND((Costo_Planos / (M2 * 50)) * 100) AS Porcentaje_Planos,
                ROUND(((Costo_MC + Costo_Planos) / (M2 * 50)) * 100) AS Porcentaje_Total
            FROM proyectos
            WHERE M2 > 0 AND MC > 0 AND Planos > 0
        """)
        resultados = cursor.fetchall()
        print("Resultados del análisis de producto:", resultados)  # Log de depuración
        cursor.close()
        conexion.close()

        return jsonify(resultados), 200
    except Exception as e:
        print("Error en /analisis-producto:", e)  # Log del error
        return jsonify({"error": str(e)}), 500

@app.route('/nominas', methods=['GET'])
def obtener_nominas():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM nominas")
        nominas = cursor.fetchall()
        print("Nóminas cargadas:", nominas)  # Verifica los datos aquí
        cursor.close()
        conexion.close()
        return jsonify(nominas), 200
    except Exception as e:
        print("Error al cargar nóminas:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/nominas', methods=['POST'])
@app.route('/nominas', methods=['POST'])
def agregar_nomina():
    try:
        datos = request.json
        nombre = datos.get('nombrenomina', '').strip()  # Cambiado de "nombre" a "nombrenomina"
        sueldo_mensual = datos.get('sueldo_mensual', 0)

        if not nombre or not sueldo_mensual or sueldo_mensual <= 0:
            return jsonify({"error": "Nombre y sueldo mensual son obligatorios y deben ser válidos."}), 400

        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO nominas (nombre, sueldo_mensual) VALUES (%s, %s)", (nombre, sueldo_mensual))
        conexion.commit()
        cursor.close()
        conexion.close()

        return jsonify({"mensaje": "Trabajador añadido exitosamente"}), 201

    except Exception as e:
        print(f"Error al agregar nómina: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/gastos', methods=['GET'])
def obtener_gastos():
    conexion = get_db_connection()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT id, descripcion, monto FROM gastos_operacion")
    gastos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return jsonify(gastos)


@app.route('/gastos', methods=['POST'])
def agregar_gasto():
    datos = request.json
    descripcion = datos.get('descripcion')
    monto = datos.get('monto')

    if not descripcion or not monto or monto <= 0:
        return jsonify({"error": "Descripción y monto son obligatorios y deben ser válidos."}), 400

    conexion = get_db_connection()
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO gastos_operacion (descripcion, monto) VALUES (%s, %s)", (descripcion, monto))
    conexion.commit()
    cursor.close()
    conexion.close()

    return jsonify({"mensaje": "Gasto añadido exitosamente"}), 201

@app.route('/gastos/<int:id_gasto>', methods=['DELETE'])
def eliminar_gasto(id_gasto):
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        # Eliminar el gasto por ID
        cursor.execute("DELETE FROM gastos_operacion WHERE id = %s", (id_gasto,))
        conexion.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Gasto no encontrado"}), 404

        cursor.close()
        conexion.close()
        return jsonify({"mensaje": "Gasto eliminado exitosamente"}), 200

    except Exception as e:
        print(f"Error al eliminar gasto: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/analisis-pu', methods=['POST'])
def calcular_pu():
    datos = request.json
    m2_disenar = datos.get('m2_disenar', 1)  # M2 a diseñar
    utilidad = datos.get('utilidad', 0)  # Utilidad como porcentaje (ej. 10%)

    conexion = get_db_connection()
    cursor = conexion.cursor(dictionary=True)

    # Obtener nóminas y gastos
    cursor.execute("SELECT sueldo_mensual * 13 AS nomina_anual FROM nominas")
    nominas = cursor.fetchall()

    cursor.execute("SELECT SUM(monto) AS total_gastos FROM gastos_operacion")
    total_gastos = cursor.fetchone()['total_gastos'] or 0

    # Calcular costo por m2 al día
    total_nominas = sum([n['nomina_anual'] for n in nominas])
    trabajadores = len(nominas)
    costo_diario = (total_nominas + total_gastos) / (trabajadores * 365)

    # Calcular Pu Limite
    promedio_pag_m2 = datos.get('promedio_pag_m2', 0)  # Esto debería ser calculado previamente
    pu_limite = 48.47 

    # Calcular Pu con utilidad
    pu_utilidad = pu_limite * (1 - utilidad / 100)

    cursor.close()
    conexion.close()

    return jsonify({
        "costo_diario": costo_diario,
        "pu_limite": pu_limite,
        "pu_utilidad": pu_utilidad,
        "costo_total": costo_diario * m2_disenar
    }), 200


@app.route('/analisis-pu', methods=['GET'])
def obtener_analisis_pu():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        
        # Obtener nóminas
        cursor.execute("SELECT Nombre, Total_Anual FROM nominas")
        nominas = cursor.fetchall()
        
        if not nominas:
            return jsonify({"error": "No se encontraron nóminas"}), 400

        # Obtener gastos de operación
        cursor.execute("SELECT SUM(Monto) AS total_gastos FROM gastos_operacion")
        total_gastos = cursor.fetchone()['total_gastos'] or 0
        total_gastos = float(total_gastos)  # Convertir a float

        # Obtener rendimiento
        cursor.execute("""
            SELECT Analista, Dibujante, Dias, M2, MC / M2 AS pag_M2
            FROM proyectos
            WHERE Dias > 0 AND M2 > 0
        """)
        proyectos = cursor.fetchall()
        resultados = cursor.fetchall()
        promedio_pag_m2 = sum(row['pag_m2'] for row in resultados) / len(resultados) if resultados else 0
        
        if resultados:
            valores_pag_m2 = [row['pag_m2'] for row in resultados if row['pag_m2'] is not None]
            promedio_pag_m2 = sum(valores_pag_m2) / len(valores_pag_m2) if valores_pag_m2 else 0
        else:
            promedio_pag_m2 = 0
            
        promedio_pag_m2 = sum(row['pag_M2'] for row in proyectos if row['pag_M2'] is not None) / len(proyectos) if proyectos else 0    
        pu_limite = float(50 - promedio_pag_m2)

        # Calcular rendimiento promedio
        rendimiento = {}
        for proyecto in proyectos:
            trabajadores = []

            if proyecto['Analista']:
                trabajadores.extend([a.strip() for a in proyecto['Analista'].split('/')])
            if proyecto['Dibujante']:
                trabajadores.extend([d.strip() for d in proyecto['Dibujante'].split('/')])

            for trabajador in trabajadores:
                trabajador = trabajador.upper()  # Normalizar a mayúsculas
                if not trabajador or trabajador == "0":
                    continue
                if trabajador not in rendimiento:
                    rendimiento[trabajador] = []
                rendimiento[trabajador].append(float(proyecto['M2']) / float(proyecto['Dias']))

        rendimiento_promedio = {
            trabajador: sum(valores) / len(valores)
            for trabajador, valores in rendimiento.items()
        }

        # Calcular análisis PU
        analisis_pu = []
        total_trabajadores = len(nominas)

        for nomina in nominas:
            trabajador = nomina['Nombre'].upper()  # Normalizar a mayúsculas
            nomina_anual = float(nomina['Total_Anual'])
            gasto_operacion = total_gastos / total_trabajadores
            promedio_rendimiento = rendimiento_promedio.get(trabajador, 0)
            

            # Validar rendimiento para evitar división por cero
            if promedio_rendimiento <= 0:
                costo_m2_dia = 0
            else:
                total_por_persona = nomina_anual + gasto_operacion
                ganancia_diaria = total_por_persona/365
                costo_m2_dia = ganancia_diaria / promedio_rendimiento

            analisis_pu.append({
                "trabajador": trabajador,
                "nomina_anual": float(nomina_anual),
                "gasto_operacion": float(gasto_operacion),
                "total_por_persona": float(total_por_persona),
                "ganancia_diaria": float(ganancia_diaria),
                "costo_m2_dia": float(costo_m2_dia),
            })

        cursor.close()
        conexion.close()
        return jsonify({
            "analisis_pu": analisis_pu,
            "pu_limite": pu_limite
        }), 200

    except Exception as e:
        print(f"Error en obtener_analisis_pu: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/calcular-tiempo', methods=['POST'])
def calcular_tiempo():
    try:
        datos = request.json
        m2 = datos.get('m2', 0)
        analista = datos.get('analista', '').strip()
        dibujante = datos.get('dibujante', '').strip()

        if not m2 or not analista or not dibujante:
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        # Obtener rendimientos promedio de analista y dibujante
        cursor.execute("""
            SELECT AVG(M2 / Dias) AS rendimiento
            FROM proyectos
            WHERE (Analista LIKE %s OR Dibujante LIKE %s) AND Dias > 0 AND M2 > 0
        """, (f"%{analista}%", f"%{dibujante}%"))
        rendimiento = cursor.fetchone()

        if not rendimiento or not rendimiento['rendimiento']:
            return jsonify({"error": "No se pudo calcular el rendimiento promedio"}), 400

        rendimiento_promedio = float(rendimiento['rendimiento'])  # Convertir a float

        # Calcular el tiempo estimado en días
        tiempo_estimado_dias = m2 / rendimiento_promedio
        tiempo_estimado_dias = float(tiempo_estimado_dias)  # Asegurar tipo float

        # Convertir a semanas y meses
        semanas = int(tiempo_estimado_dias // 7)
        dias_restantes = int(tiempo_estimado_dias % 7)+7
        meses = semanas // 4
        semanas_restantes = semanas % 4

        # Calcular fecha de finalización
        fecha_inicio = datos.get('fecha_inicio')
        if not fecha_inicio:
            return jsonify({"error": "La fecha de inicio es obligatoria"}), 400

        fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fecha_fin = fecha_inicio_obj + timedelta(days=tiempo_estimado_dias)

        cursor.close()
        conexion.close()

        return jsonify({
            "tiempo_estimado": {
                "meses": meses,
                "semanas": semanas_restantes,
                "dias": dias_restantes
            },
            "fecha_fin": fecha_fin.strftime('%Y-%m-%d')
        }), 200
    except Exception as e:
        print(f"Error al calcular tiempo: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/trabajadores', methods=['GET'])
def obtener_trabajadores():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        # Obtener nombres únicos de Analistas y Dibujantes
        cursor.execute("""
            SELECT Analista, Dibujante
            FROM proyectos
            WHERE Analista IS NOT NULL OR Dibujante IS NOT NULL
        """)
        filas = cursor.fetchall()

        # Dividir nombres por comas y normalizarlos (eliminar espacios y duplicados)
        trabajadores = set()
        for fila in filas:
            if fila['Analista']:
                trabajadores.update([nombre.strip() for nombre in fila['Analista'].split('/')])
            if fila['Dibujante']:
                trabajadores.update([nombre.strip() for nombre in fila['Dibujante'].split('/')])

        cursor.close()
        conexion.close()

        # Convertir el conjunto a una lista ordenada
        return jsonify({"trabajadores": sorted(trabajadores)})
    except Exception as e:
        print(f"Error al obtener trabajadores: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/nominas/<int:id>', methods=['DELETE'])
def eliminar_nomina(id):
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()

        # Eliminar la nómina por ID
        cursor.execute("DELETE FROM nominas WHERE id = %s", (id,))
        conexion.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "No se encontró el trabajador en la nómina"}), 404

        cursor.close()
        conexion.close()
        return jsonify({"mensaje": "Trabajador eliminado exitosamente de la nómina"}), 200

    except Exception as e:
        print(f"Error al eliminar nómina: {e}")
        return jsonify({"error": str(e)}), 500


# Ruta para servir el archivo HTML
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 5001))  # Usa el puerto especificado en la variable de entorno
    debug = os.getenv('FLASK_ENV') == 'development'  # Activa debug en desarrollo
    app.run(host='0.0.0.0', port=port, debug=debug)  # Escucha en todas las interfaces
