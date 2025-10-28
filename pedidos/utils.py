from urllib.parse import quote

def enviar_whatsapp(cliente, mensaje):
    if not cliente or not cliente.telefono:
        return None

    # Normalizar número
    numero = cliente.telefono.strip().replace(" ", "").replace("-", "")
    if numero.startswith("0"):
        numero = numero[1:]
    if not numero.startswith("595"):
        numero = f"595{numero}"

    # Limpiar saltos de línea y usar solo \n
    mensaje = mensaje.replace("\r\n", "\n").replace("\r", "\n")

    # Codificar todo (emojis, acentos y saltos de línea)
    mensaje_codificado = quote(mensaje, safe='')

    enlace = f"https://wa.me/{numero}?text={mensaje_codificado}"
    return enlace
