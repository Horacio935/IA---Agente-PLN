import psycopg2
import numpy as np
import re
import unicodedata
from sentence_transformers import SentenceTransformer, util
from lector_pdf import procesar_pdf
import os
from transformers import pipeline
from collections import Counter
from docx2pdf import convert
import tempfile
import shutil


# Funcion para normalizar texto, es decir en minusculas y sin tildes
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.strip()

modelo = SentenceTransformer("all-MiniLM-L6-v2")


def resumen_fragmentos_pdf(cursor, cantidad_oraciones=5):
    cursor.execute("SELECT fragmento FROM pdf_conocimiento")
    fragmentos = cursor.fetchall()
    texto_completo = " ".join(f[0] for f in fragmentos)

    oraciones = re.split(r'(?<=[.!?]) +', texto_completo)
    palabras = re.findall(r'\b\w+\b', texto_completo.lower())

    stopwords = set([
        "el", "la", "los", "las", "de", "que", "y", "a", "en", "es", "un", "una", "con", "por", "para", "se", "al", "del"
    ])
    palabras = [w for w in palabras if w not in stopwords]

    frecuencia = Counter(palabras)
    oraciones_puntaje = []

    for oracion in oraciones:
        palabras_oracion = re.findall(r'\b\w+\b', oracion.lower())
        puntaje = sum(frecuencia.get(p, 0) for p in palabras_oracion)
        oraciones_puntaje.append((puntaje, oracion))

    oraciones_puntaje.sort(reverse=True)
    top = [o for _, o in oraciones_puntaje[:cantidad_oraciones]]

    return " ".join(top)

# Conexion a PostgreSQL
conexion = psycopg2.connect(
    host="localhost",
    database="agente_autonomo",
    user="postgres",
    password="1234"
)
cursor = conexion.cursor()

UMBRAL_SIMILITUD = 0.75

print("Agente listo para conversar. Escribe 'salir' para terminar.\n")

while True:
    entrada = input("Tú: ").strip()
    entrada_norm = normalizar(entrada)
    embedding_entrada = modelo.encode(entrada_norm)

    # 🚨 Petición de resumen detectada
    if entrada_norm in ["resumen", "resumelo", "dame un resumen", "resumen del pdf", "haz un resumen"]:
        resumen = resumen_fragmentos_pdf(cursor)
        print("Agente (resumen):", resumen)
        continue
    
    # Detectar si el usuario ingreso una ruta a un PDF
    if entrada_norm.endswith((".pdf", ".docx")) and os.path.exists(entrada):
        try:
            ruta_procesar = entrada

            if entrada_norm.endswith(".docx"):
                temp_dir = tempfile.mkdtemp()
                ruta_pdf = os.path.join(temp_dir, "convertido.pdf")
                convert(entrada, ruta_pdf)
                ruta_procesar = ruta_pdf  # actualiza ruta a PDF generado

            procesar_pdf(ruta_procesar, cursor, conexion)
            print("Agente: He analizado el archivo y he aprendido de él.")

            if entrada_norm.endswith(".docx"):
                shutil.rmtree(temp_dir)  # limpia temporal

        except Exception as e:
            print(f"Agente: Ocurrió un error al procesar el documento: {e}")
        continue


    # ---------------------------
    # Comprension de frases conversacionales (como estas?, que haces, etc)
    frases_sociales = {
        "como estas": "Estoy muy bien, gracias por preguntar!",
        "como te va": "Todo va excelente, y contigo?",
        "que haces": "Estoy aqui para ayudarte. En que te puedo servir?",
        "como va todo": "Todo tranquilo por aquí. ¿Y tu que tal?",
        "todo bien": "Si! Todo bien. Espero que tu tambien.",
        "como te sientes": "Me siento util cuando puedo ayudarte.",
        "como esta usted": "Muy amable, estoy bien. ¿Y usted?"
    }

    respuestas_sociales = {
        "estoy bien": "¡Me alegra saber eso!",
        "todo bien": "¡Perfecto! Me gusta escuchar eso.",
        "me alegra": "¡A mi tambien! Gracias.",
        "no tan bien": "Lo siento, espero que todo mejore pronto.",
        "ando triste": "Estoy aqui para ti si necesitas hablar.",
        "estoy feliz": "¡Eso me hace feliz tambien!",
        "mal": "¿Quieres que hablemos de eso?",
        "cansado": "Descansar un poco ayuda. animo!"
    }

    # ---------------------------
    # Intenciones negativas: "no puedes ayudarme", "no me sirves", etc.
    intenciones_negativas = {
        "no puedes ayudarme": "Entiendo, pero estaré aquí por si cambias de opinión.",
        "no me sirves": "Lamento que no pueda ayudarte ahora. Intentaré mejorar.",
        "no eres util": "Gracias por tu sinceridad. Seguiré aprendiendo.",
        "no ayudas": "Intento hacerlo lo mejor posible. ¿Quieres explicarme más?",
        "no entiendo para que sirves": "Puedo aprender con tu ayuda. ¿Qué necesitas saber?"
    }

    mejor_similitud_neg = 0
    respuesta_negativa = None

    for frase_ref, respuesta_ref in intenciones_negativas.items():
        emb_ref = modelo.encode(frase_ref)
        sim = util.cos_sim(
            np.array(embedding_entrada).astype(np.float32),
            np.array(emb_ref).astype(np.float32)
        ).item()
        if sim > mejor_similitud_neg:
            mejor_similitud_neg = sim
            respuesta_negativa = respuesta_ref

    if mejor_similitud_neg >= 0.78:
        print(f"Agente: {respuesta_negativa}")
        continue


    palabra_clave = None

    # Detectar preguntas tipo que es?, que significa?, etc
    match_significado = re.search(r"(que|qué) (es|significa)( un| una| el| la)? (\w+)", entrada_norm)
    if match_significado:
        palabra_clave = match_significado.group(4)

    match_sabes_significado = re.search(r"sabes.*?(significado|que es) (un|una|el|la)? (\w+)", entrada_norm)
    if match_sabes_significado:
        palabra_clave = match_sabes_significado.group(3)

    # Comparar por similitud semántica
    
    mejor_similitud_social = 0
    respuesta_social = None

    for frase_ref, respuesta_ref in frases_sociales.items():
        emb_ref = modelo.encode(frase_ref)
        sim = util.cos_sim(
            np.array(embedding_entrada).astype(np.float32),
            np.array(emb_ref).astype(np.float32)
        ).item()

        if sim > mejor_similitud_social:
            mejor_similitud_social = sim
            respuesta_social = respuesta_ref

    if mejor_similitud_social >= 0.78:
        print(f"Agente: {respuesta_social}")
        continue

    # Detectar respuestas emocionales del usuario
    mejor_similitud_estado = 0
    respuesta_estado = None

    for frase_ref, respuesta_ref in respuestas_sociales.items():
        emb_ref = modelo.encode(frase_ref)
        sim = util.cos_sim(
            np.array(embedding_entrada).astype(np.float32),
            np.array(emb_ref).astype(np.float32)
        ).item()

        if sim > mejor_similitud_estado:
            mejor_similitud_estado = sim
            respuesta_estado = respuesta_ref

    if mejor_similitud_estado >= 0.78:
        print(f"Agente: {respuesta_estado}")
        continue

    # ---------------------------
    # Detectar saludos, despedidas y agradecimientos
    saludos = ["hola", "buenos dias", "buenas tardes", "buenas noches", "que tal"]
    agradecimientos = ["gracias", "muchas gracias", "te lo agradezco"]
    despedidas = ["adios", "nos vemos", "hasta luego", "chao", "bye"]

    # Saludo
    if any(re.search(rf"\b{saludo}\b", entrada_norm) for saludo in saludos) and not entrada_norm.startswith("que es"):
        print("Agente: ¡Hola! ¿En qué te puedo ayudar?")
        continue

    # Agradecimiento
    if any(re.search(rf"\b{agrade}\b", entrada_norm) for agrade in agradecimientos) and not entrada_norm.startswith("que es"):
        print("Agente: ¡De nada! Me alegra ayudarte.")
        continue

    # Despedida
    if any(re.search(rf"\b{desp}\b", entrada_norm) for desp in despedidas) and not entrada_norm.startswith("que es"):
        print("Agente: ¡Nos vemos pronto! Cuidate.")
        continue


    if entrada_norm == "salir":
        print("Agente: ¡Hasta luego!")
        break

    # ---------------------------
    # Quien es mi...?
    match_rol = re.search(r"(quien|quién) es mi ([\w\s]+)", entrada_norm)
    if match_rol:
        rol = normalizar(match_rol.group(2)).strip()
        descripcion_esperada = f"tu {rol}"

        cursor.execute("SELECT nombre, descripcion FROM identidades")
        resultado = None

        for nombre, descripcion in cursor.fetchall():
            if descripcion_esperada in normalizar(descripcion):
                resultado = nombre
                break

        if resultado:
            print(f"Agente: Tu {rol} es {resultado}")
        else:
            print(f"Agente: No lo sé aún... ¿quién es tu {rol}?")
            nombre = input("Tú: ").strip()
            nombre = normalizar(nombre)
            cursor.execute("INSERT INTO identidades (nombre, descripcion) VALUES (%s, %s)", (nombre, f"Tu {rol}"))
            conexion.commit()
            print(f"Agente: ¡Gracias! Ahora se que tu {rol} se llama {nombre}.")
        continue
    
    # ---------------------------
    # quien es X?
    match_quien = re.match(r"(quien|quién) es (.+)\??", entrada_norm)
    if match_quien:
        nombre = normalizar(match_quien.group(2).rstrip("?"))

        cursor.execute("SELECT descripcion FROM identidades WHERE nombre = %s", (nombre,))
        resultado = cursor.fetchone()

        if resultado:
            print(f"Agente: {resultado[0]}")
            continue
        else:
            print("Agente: No lo sé aún... ¿quién es?")
            descripcion = input("Tú: ").strip()
            # mi por tu y yo soy por tu eres
            descripcion = re.sub(r'\bmi\b', 'tu', descripcion, flags=re.IGNORECASE)
            descripcion = re.sub(r'\bsoy yo\b', 'eres tú', descripcion, flags=re.IGNORECASE)
            descripcion = descripcion.strip().capitalize()
            
            cursor.execute("SELECT 1 FROM identidades WHERE nombre = %s", (nombre,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO identidades (nombre, descripcion) VALUES (%s, %s)", (nombre, descripcion))
                conexion.commit()

            print("Agente: ¡Gracias! Lo recordare")
            continue

    # ---------------------------
    # como me llamo?
    match_nombre = re.search(r"(como me llamo|cu[aá]l es mi nombre|sabes como me llamo)", entrada_norm)
    if match_nombre:
        cursor.execute("SELECT nombre FROM identidades WHERE descripcion = 'Eres tú'")
        resultado = cursor.fetchone()
        if resultado:
            print(f"Agente: Te llamas {resultado[0]}")
        else:
            print("Agente: No lo sé aún... ¿cómo te llamas?")
            respuesta = input("Tú: ").strip()
            nombre = normalizar(respuesta)
            cursor.execute("INSERT INTO identidades (nombre, descripcion) VALUES (%s, %s)", (nombre, "Eres tú"))
            conexion.commit()
            print("Agente: ¡Gracias! Lo recordare")
        continue


    # ---------------------------
    # como se llama mi...?
    match_familia = re.search(r"como se llama mi (\w+)", entrada_norm)
    if match_familia:
        rol = match_familia.group(1)
        descripcion_esperada = f"Tu {rol}"

        cursor.execute("SELECT nombre FROM identidades WHERE LOWER(descripcion) LIKE %s", (f"%{descripcion_esperada.lower()}%",))
        resultado = cursor.fetchone()

        if resultado:
            print(f"Agente: {descripcion_esperada} se llama {resultado[0]}")
        else:
            print(f"Agente: No lo se aun... ¿cómo se llama tu {rol}?")
            nombre = input("Tú: ").strip()
            nombre = normalizar(nombre)

            cursor.execute("INSERT INTO identidades (nombre, descripcion) VALUES (%s, %s)", (nombre, descripcion_esperada))
            conexion.commit()
            print(f"Agente: ¡Gracias! Ahora se que tu {rol} se llama {nombre}.")
        continue

    # ---------------------------
    #Detectar identidad
    patrones_identidad = [
        r"yo soy (.+)",
        r"mi (mama|papa|hermano|hermana|novia|novio|esposa|esposo|amigo|amiga|perro|perrita|gato|gatita) se llama (.+)",
        r"(.+) es mi (mama|papa|hermano|hermana|novia|novio|esposa|esposo|amigo|amiga|perro|perrita|gato|gatita)"
    ]

    identidad_detectada = False

    for patron in patrones_identidad:
        match = re.match(patron, entrada_norm)
        if match:
            if patron.startswith("yo soy"):
                nombre = normalizar(match.group(1))
                descripcion = "Eres tú"
            elif "se llama" in patron:
                tipo = match.group(1)
                nombre = normalizar(match.group(2))
                descripcion = f"Tu {tipo}"
            else:
                nombre = normalizar(match.group(1))
                tipo = match.group(2)
                descripcion = f"Tu {tipo}"

            cursor.execute("SELECT 1 FROM identidades WHERE nombre = %s", (nombre,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO identidades (nombre, descripcion) VALUES (%s, %s)", (nombre, descripcion))
                conexion.commit()

            print(f"Agente: ¡Genial! Ya se quien es {nombre}.")
            identidad_detectada = True
            break

    if identidad_detectada:
        continue

    if entrada_norm in ["resumen", "resumelo", "dame un resumen", "resumen del pdf", "haz un resumen"]:
        resumen = resumen_fragmentos_pdf(cursor)
        print("Agente (resumen):", resumen)
        continue

    # ---------------------------
    #Buscar por similitud en conocimiento
    # Buscar por similitud en conocimiento
    embedding_usuario = modelo.encode(entrada_norm)

    cursor.execute("SELECT pregunta, respuesta, embedding FROM conocimiento")
    registros = cursor.fetchall()

    mejor_similitud = 0
    mejor_respuesta = None

    for pregunta_bd, respuesta_bd, embedding_txt in registros:
        if palabra_clave and palabra_clave not in pregunta_bd:
            continue
        try:
            vector_bd = np.fromstring(embedding_txt, sep=',').astype(np.float32)
            if vector_bd.shape[0] != 384:
                continue
            similitud = util.cos_sim(
                np.array(embedding_usuario).astype(np.float32),
                vector_bd
            ).item()
        except Exception as e:
            print(f"[WARN] Embedding corrupto en 'conocimiento': {e}")
            continue


        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_respuesta = respuesta_bd

    if mejor_similitud >= UMBRAL_SIMILITUD:
        print(f"Agente: {mejor_respuesta}")
        continue

    # Último intento: buscar en fragmentos del PDF con vectores y extraer info después de palabra clave
    cursor.execute("SELECT fragmento, embedding FROM pdf_conocimiento")
    fragmentos = cursor.fetchall()

    mejor_similitud = 0
    mejor_fragmento = None

    for frag, emb_txt in fragmentos:
        try:
            vector = np.fromstring(emb_txt, sep=',').astype(np.float32)
            if vector.shape[0] != 384:
                continue
            similitud = util.cos_sim(
                np.array(embedding_usuario).astype(np.float32),
                vector
            ).item()
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_fragmento = frag
        except Exception as e:
            print(f"[WARN] Fragmento corrupto: {e}")
            continue

    if mejor_fragmento and mejor_similitud >= 0.70:
        if palabra_clave:
            frag_norm = normalizar(mejor_fragmento)
            idx = frag_norm.find(palabra_clave)
            if idx != -1:
                original = mejor_fragmento[idx:]
                punto = original.find(".")
                if punto != -1:
                    respuesta = original[:punto+1].strip()
                else:
                    # Buscar siguiente fragmento si no hay punto
                    respuesta = original.strip()
                    index_actual = [f[0] for f in fragmentos].index(mejor_fragmento)
                    for siguiente in fragmentos[index_actual+1:]:
                        respuesta += " " + siguiente[0]
                        if "." in siguiente[0]:
                            break
                    punto = respuesta.find(".")
                    if punto != -1:
                        respuesta = respuesta[:punto+1]
                print("Agente (PDF):", respuesta)
                continue
        # Si no hay palabra clave o no se encuentra, devolver fragmento entero
        print("Agente (PDF):", mejor_fragmento)
        continue



    # 😅 Si no lo sabe aún, lo aprende
    print("Agente: No lo sé aún... ¿me lo puedes explicar?")
    nueva_respuesta = input("Tú: ").strip()
    embedding_str = ','.join(str(x) for x in embedding_usuario)

    cursor.execute(
        "INSERT INTO conocimiento (pregunta, respuesta, embedding) VALUES (%s, %s, %s)",
        (entrada_norm, nueva_respuesta, embedding_str)
    )
    conexion.commit()

    print("Agente: ¡Gracias! Lo recordare para la próxima.")

#C:\Users\lopez\OneDrive\Escritorio\UMG\9no Semestre\Inteligencia Artificial\Examen2\archivos\INTELIGENCIA.pdf
#C:\Users\lopez\OneDrive\Escritorio\UMG\9no Semestre\Inteligencia Artificial\Examen2\archivos\Repaso - Segundo Examen.pdf
#C:\Users\lopez\OneDrive\Escritorio\UMG\9no Semestre\Inteligencia Artificial\Examen2\archivos\INTELIGENCIA_docx.docx