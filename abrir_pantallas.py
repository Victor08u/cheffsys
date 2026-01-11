import subprocess
import time
import pygetwindow as gw
import pyautogui

# Rutas y URLs
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
url_pantalla1 = "http://localhost:8000"           # Página principal
url_pantalla2 = "http://localhost:8000/pedidos"   # Página de cocina/pedidos

# --- 1️⃣ Abrir la primera ventana (pantalla 1) ---
subprocess.Popen([
    chrome_path,
    "--new-window", url_pantalla1,
    "--window-position=0,0",
    "--window-size=1366,768"
])
time.sleep(4)  # Esperar para que Chrome cree la ventana

# --- 2️⃣ Abrir la segunda ventana (pantalla 2) ---
subprocess.Popen([
    chrome_path,
    "--new-window", url_pantalla2,
    "--window-position=1367,0",   # segunda pantalla
    "--window-size=1280,1024"
])
time.sleep(5)

# --- 3️⃣ Buscar la ventana que contiene 'pedidos' y moverla ---
ventanas = gw.getWindowsWithTitle("Pedidos")  # Busca por título de pestaña
if not ventanas:
    ventanas = gw.getWindowsWithTitle("localhost:8000/pedidos")  # alternativa

if ventanas:
    ventana2 = ventanas[0]
    ventana2.moveTo(1367, 0)   # posición inicial del segundo monitor
    ventana2.maximize()
    pyautogui.hotkey("f11")    # pantalla completa
else:
    print("⚠️ No se encontró la ventana de pedidos para moverla.")
