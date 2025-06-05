import tkinter as tk
import threading
import time
from agente_autonomo import responder_agente, aprender_respuesta
from agente_autonomo import guardar_identidad

ventana = tk.Tk()
ventana.title("Agente Inteligente")
ventana.geometry("800x600")
ventana.configure(bg="#f0f0f0")

canvas = tk.Canvas(ventana, bg="#f0f0f0")
scrollbar = tk.Scrollbar(ventana, command=canvas.yview)
frame_chat = tk.Frame(canvas, bg="#f0f0f0")
frame_chat.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=frame_chat, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.grid(row=0, column=0, columnspan=2, sticky="nsew")
scrollbar.grid(row=0, column=2, sticky="ns")

etiqueta_estado = tk.Label(ventana, text="", font=("Segoe UI", 10, "italic"), fg="gray", bg="#f0f0f0")
etiqueta_estado.grid(row=1, column=0, sticky="w", padx=10)

frame_entrada = tk.Frame(ventana, bg="#f0f0f0")
entrada_usuario = tk.Entry(frame_entrada, font=("Segoe UI", 12), width=80)
boton_enviar = tk.Button(frame_entrada, text="Enviar", font=("Segoe UI", 11))
entrada_usuario.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
boton_enviar.pack(side=tk.RIGHT, padx=10)
frame_entrada.grid(row=2, column=0, columnspan=2, sticky="ew")

ventana.grid_rowconfigure(0, weight=1)
ventana.grid_columnconfigure(0, weight=1)

animando = False
contador_puntos = 0

def animar():
    global contador_puntos
    if animando:
        puntos = "." * (contador_puntos % 4)
        etiqueta_estado.config(text=f"Agente escribiendo{puntos}")
        contador_puntos += 1
        ventana.after(500, animar)

def iniciar_animacion():
    global animando, contador_puntos
    animando = True
    contador_puntos = 0
    animar()

def detener_animacion():
    global animando
    animando = False
    etiqueta_estado.config(text="")

def agregar_burbuja(texto, autor="usuario"):
    contenedor = tk.Frame(frame_chat, bg="#f0f0f0", pady=5)
    color = "#d4fcd4" if autor == "usuario" else "#d4e4fc"
    nombre = "Tú" if autor == "usuario" else "Agente"

    nombre_label = tk.Label(contenedor, text=nombre, font=("Segoe UI", 9, "italic"), fg="gray", bg="#f0f0f0")
    nombre_label.pack(anchor="w", padx=10)

    burbuja = tk.Label(contenedor, text=texto, bg=color, font=("Segoe UI", 11),
                       wraplength=500, justify=tk.LEFT, padx=10, pady=5)

    if autor == "usuario":
        contenedor.pack(anchor="e", padx=60, fill="x", expand=True)
        burbuja.pack(anchor="e", padx=(100, 20))
    else:
        contenedor.pack(anchor="w", padx=60, fill="x", expand=True)
        burbuja.pack(anchor="w", padx=(20, 100))

    canvas.update_idletasks()
    canvas.yview_moveto(1.0)

def procesar(event=None):
    entrada = entrada_usuario.get().strip()
    if not entrada:
        return
    agregar_burbuja(entrada, "usuario")
    entrada_usuario.delete(0, tk.END)
    threading.Thread(target=generar_respuesta, args=(entrada,)).start()

def generar_respuesta(mensaje):
    iniciar_animacion()
    respuesta = responder_agente(mensaje)
    time.sleep(0.8)
    detener_animacion()

    if isinstance(respuesta, tuple):
        tipo, dato = respuesta
        if tipo == "PREGUNTAR_IDENTIDAD":
            agregar_burbuja(f"Agente: No lo sé aún... ¿quién es {dato}?", "bot")
            esperar_identidad(dato)
            return
        if tipo == "PREGUNTAR_IDENTIDAD_MI":
            agregar_burbuja(f"Agente: No lo sé aún... ¿quién es tu {dato.split(' ', 1)[-1]}?", "bot")
            esperar_identidad(dato)
            return
        if tipo == "PREGUNTAR_FAMILIA":
            agregar_burbuja(f"Agente: No lo sé aún... ¿cómo se llama tu {dato.split(' ', 1)[-1]}?", "bot")
            esperar_identidad(dato)
            return

    elif respuesta == "PREGUNTAR_NOMBRE":
        agregar_burbuja("Agente: No lo sé aún... ¿cómo te llamas?", "bot")
        esperar_identidad("Eres tú")
        return

    elif respuesta == "NO_SE":
        agregar_burbuja("Agente: No lo sé aún... ¿me lo puedes explicar?", "bot")
        esperar_explicacion(mensaje)
        return

    agregar_burbuja(respuesta, "bot")

def esperar_identidad(descripcion):
    def capturar_identidad():
        entrada = entrada_usuario.get().strip()
        if not entrada:
            return
        agregar_burbuja(entrada, "usuario")
        entrada_usuario.delete(0, tk.END)
        guardar_identidad(entrada, descripcion)
        agregar_burbuja(f"Agente: ¡Gracias! Ahora sé que {descripcion} se llama {entrada}.", "bot")

    boton_enviar.config(command=capturar_identidad)
    entrada_usuario.bind("<Return>", lambda event: capturar_identidad())

def esperar_explicacion(pregunta):
    def capturar():
        entrada = entrada_usuario.get().strip()
        if not entrada:
            return
        agregar_burbuja(entrada, "usuario")
        entrada_usuario.delete(0, tk.END)
        aprender_respuesta(pregunta, entrada)
        agregar_burbuja("Agente: ¡Gracias! Lo recordaré para la próxima.", "bot")

    boton_enviar.config(command=capturar)
    entrada_usuario.bind("<Return>", lambda event: capturar())

entrada_usuario.bind("<Return>", procesar)
boton_enviar.config(command=procesar)
ventana.mainloop()
