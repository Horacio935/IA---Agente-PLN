import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Frases de entrenamiento
frases = [
    # PHISHING
    "me llegó un correo con un enlace sospechoso",
    "recibí un mensaje que dice que gané un premio",
    "un banco me pidió mis datos por correo",
    "me mandaron un mensaje con urgencia para entrar a un sitio",
    "vi un enlace acortado en redes sociales",
    
    # CONTRASEÑAS
    "uso la misma contraseña en todo",
    "mi clave es muy corta",
    "compartí mi contraseña con un amigo",
    "uso mi fecha de cumpleaños como contraseña",
    "escribí mi contraseña en un papel",
    
    # REDES SOCIALES
    "publiqué mi dirección en una historia",
    "acepté una solicitud de un desconocido",
    "mi perfil es público",
    "dejé activada la ubicación en mis publicaciones",
    "subí una foto con mi tarjeta de crédito",

    # MALWARE Y VIRUS
    "descargué un archivo de una página rara",
    "mi computadora se puso lenta de la nada",
    "me salen muchas ventanas emergentes",
    "instalé un programa pirata",
    "mi navegador se redirige solo a otras páginas",

    # ESTAFAS EN LÍNEA
    "compré en una tienda que era falsa",
    "me ofrecieron un producto demasiado barato",
    "me dijeron que gané dinero sin participar",
    "me pidieron pagar solo por transferencia",
    "recibí un mensaje que me amenaza si no pago en bitcoin"
]

# Etiquetas correspondientes
etiquetas = [
    "phishing", "phishing", "phishing", "phishing", "phishing",
    "contraseñas", "contraseñas", "contraseñas", "contraseñas", "contraseñas",
    "redes sociales", "redes sociales", "redes sociales", "redes sociales", "redes sociales",
    "malware y virus", "malware y virus", "malware y virus", "malware y virus", "malware y virus",
    "estafas en línea", "estafas en línea", "estafas en línea", "estafas en línea", "estafas en línea"
]

# Entrenamiento del modelo
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(frases)

modelo = MultinomialNB()
modelo.fit(X, etiquetas)

# Guardar el modelo y vectorizador
with open("modelo.pkl", "wb") as f:
    pickle.dump((vectorizer, modelo), f)

print("✅ Modelo actualizado y guardado exitosamente con los 5 temas.")
