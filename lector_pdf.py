import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
import pandas as pd


modelo = SentenceTransformer("all-MiniLM-L6-v2")

def extraer_texto_excel(ruta):
    try:
        df = pd.read_excel(ruta, sheet_name=None)  # lee todas las hojas
        texto = ""
        for nombre_hoja, hoja in df.items():
            texto += f"Hoja: {nombre_hoja}\n"
            texto += hoja.fillna("").astype(str).apply(lambda x: " ".join(x), axis=1).str.cat(sep="\n")
            texto += "\n"
        return texto
    except Exception as e:
        print(f"[ERROR] Al leer Excel: {e}")
        return ""



def extraer_texto_pdf(ruta_pdf):
    doc = fitz.open(ruta_pdf)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    doc.close()
    return texto

def dividir_y_vectorizar(texto):
    lineas = [l.strip() for l in texto.split('\n') if len(l.strip()) > 20]
    fragmentos = []
    buffer = []

    for linea in lineas:
        buffer.append(linea)
        if len(buffer) == 3:
            fragmentos.append(" ".join(buffer))
            buffer = []

    if buffer:
        fragmentos.append(" ".join(buffer))

    embeddings = [modelo.encode(frag) for frag in fragmentos]
    return list(zip(fragmentos, embeddings))

def procesar_pdf(ruta_pdf, cursor, conexion):
    print(f"[INFO] Procesando archivo: {ruta_pdf}")
    
    # Eliminar contenido anterior
    cursor.execute("DELETE FROM pdf_conocimiento")
    cursor.execute("DELETE FROM pdf_texto")
    conexion.commit()
    print("[INFO] Se eliminó contenido anterior del PDF.")

    texto = extraer_texto_pdf(ruta_pdf)

    # Guardar texto completo
    cursor.execute("INSERT INTO pdf_texto (texto) VALUES (%s)", (texto,))
    conexion.commit()

    # Guardar fragmentos y embeddings
    fragmentos = dividir_y_vectorizar(texto)
    for frag, emb in fragmentos:
        emb_str = ','.join(str(x) for x in emb)
        cursor.execute(
            "INSERT INTO pdf_conocimiento (fragmento, embedding) VALUES (%s, %s)",
            (frag, emb_str)
        )
    conexion.commit()
    print("[INFO] PDF cargado correctamente en la base de datos.")
    