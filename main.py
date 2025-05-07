import pickle
import psycopg2
import random

# Cargar modelo y vectorizador
with open("modelo.pkl", "rb") as f:
    vectorizer, modelo = pickle.load(f)

# Conexión a PostgreSQL (ajusta estos datos)
conexion = psycopg2.connect(
    host="localhost",
    database="agente_ciberseguridad",
    user="postgres",
    password="1234"
)
cursor = conexion.cursor()

# Preguntas dinámicas según categoría
preguntas_seguimiento = {
    "phishing": [
        "¿El mensaje menciona algo urgente, dinero o premios?",
        "¿Te piden hacer clic en un enlace sospechoso?",
        "¿El correo parece venir de un banco o empresa conocida?"
    ],
    "contraseñas": [
        "¿Tu contraseña tiene menos de 8 caracteres?",
        "¿La usas en varios sitios diferentes?",
        "¿Incluye tu nombre o información fácil de adivinar?"
    ],
    "redes sociales": [
        "¿Has publicado información personal recientemente?",
        "¿Tienes tu perfil público?",
        "¿Aceptas solicitudes de personas que no conoces?"
    ],
    "malware y virus": [
        "¿Tu computadora está más lenta de lo normal?",
        "¿Has descargado programas de páginas no oficiales?",
        "¿Te aparecen muchas ventanas emergentes?"
    ],
    "estafas en línea": [
        "¿Te ofrecieron un producto con un precio muy bajo?",
        "¿Te pidieron pagar solo por transferencia?",
        "¿Recibiste amenazas si no realizas un pago digital?"
    ]
}

respuestas_agradecimiento = [
    "Gracias por contármelo.",
    "Eso me ayuda a entender mejor tu situación.",
    "Perfecto, con eso puedo ayudarte mejor.",
    "Entiendo, gracias por la información."
]

saludos_iniciales = [
    "¡Hola! Soy tu asistente de ciberseguridad. ¿En qué puedo ayudarte hoy?",
    "¡Bienvenido! Estoy aquí para orientarte sobre seguridad digital. ¿Qué sucede?",
    "Hola, cuéntame qué problema estás enfrentando en línea."
]

despedidas = [
    "¡Hasta luego! Recuerda proteger tus datos. 🔐",
    "Nos vemos. Mantente seguro en internet.",
    "Cualquier cosa, aquí estaré. ¡Cuídate!"
]

print("Agente:", random.choice(saludos_iniciales), "\n(Escribe 'salir' para terminar)\n")

while True:
    entrada1 = input("Tú: ")
    if entrada1.lower() == "salir":
        print("Agente:", random.choice(despedidas))
        break

    entrada_vec = vectorizer.transform([entrada1])
    probas = modelo.predict_proba(entrada_vec)[0]
    confianza = max(probas)
    categoria = modelo.classes_[probas.argmax()]

    if confianza < 0.25:
        print("Agente: Hmm... no estoy seguro si eso tiene que ver con ciberseguridad.")
        print("Agente: ¿Podrías contarme si ocurrió algo en línea, como un mensaje, correo o problema con tus cuentas?")
        continue

    print(f"\n Agente: Entiendo, parece relacionado con **{categoria}**.")
    pregunta = random.choice(preguntas_seguimiento[categoria])
    print("Agente:", pregunta)

    entrada2 = input("Tú: ")
    if entrada2.lower() == "salir":
        print("Agente:", random.choice(despedidas))
        break

    # Buscar hecho aleatorio según la categoría
    cursor.execute("""
        SELECT problema, causa, recomendacion
        FROM hechos
        WHERE categoria = %s
        ORDER BY RANDOM()
        LIMIT 1
    """, (categoria,))
    resultado = cursor.fetchone()

    if resultado:
        problema, causa, recomendacion = resultado
        print("\nAgente:", random.choice(respuestas_agradecimiento))
        print(f"Parece un caso de: *{problema}*")
        print(f"Causa probable: {causa}")
        print(f"Recomendación: {recomendacion}\n")
    else:
        print("Agente: Lo siento, no tengo información suficiente sobre ese tema.\n")

# Cierre
cursor.close()
conexion.close()
