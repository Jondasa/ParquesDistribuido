#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de instalación para Parqués Distribuido
"""

import os
import sys
import subprocess
import platform
import time

def check_python_version():
    """Verifica la versión de Python."""
    print("Verificando versión de Python...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        print("⚠️ ERROR: Se requiere Python 3.6 o superior.")
        print(f"Tu versión actual es: Python {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    else:
        print(f"✅ Usando Python {version.major}.{version.minor}.{version.micro}")

def install_dependencies():
    """Instala las dependencias necesarias."""
    print("\nInstalando dependencias...")
    
    try:
        # Instalar pygame
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
        print("✅ Pygame instalado correctamente")
        
    except subprocess.CalledProcessError:
        print("⚠️ Error al instalar dependencias. Intenta instalar manualmente:")
        print("pip install pygame")
        sys.exit(1)

def create_resource_directory():
    """Crea un directorio para recursos del juego."""
    print("\nCreando directorio de recursos...")
    
    if not os.path.exists("resources"):
        os.makedirs("resources")
        print("✅ Directorio 'resources' creado")
    else:
        print("✅ Directorio 'resources' ya existe")

def create_sound_files():
    """Crea archivos de sonido básicos para el juego."""
    print("\nVerificando archivos de sonido...")
    
    # Lista de archivos de sonido necesarios
    sound_files = [
        "dice_roll.wav",
        "piece_move.wav",
        "capture.wav",
        "win.wav"
    ]
    
    # Verificar y crear archivos vacíos si no existen
    for sound_file in sound_files:
        sound_path = os.path.join("resources", sound_file)
        if not os.path.exists(sound_path):
            try:
                # Crear un archivo de sonido vacío
                with open(sound_path, "wb") as f:
                    # Escribir un encabezado WAV mínimo
                    f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
                print(f"✅ Archivo de sonido '{sound_file}' creado")
            except Exception as e:
                print(f"⚠️ No se pudo crear el archivo de sonido '{sound_file}': {e}")
        else:
            print(f"✅ Archivo de sonido '{sound_file}' ya existe")

def run_game():
    """Ejecuta el juego."""
    print("\n" + "="*60)
    print("🎮 PARQUÉS DISTRIBUIDO - SISTEMAS DISTRIBUIDOS")
    print("="*60)
    print("\nEl juego está listo para ejecutarse.")
    print("\nOpciones:")
    print("1. Iniciar servidor")
    print("2. Iniciar cliente")
    print("3. Salir")
    
    option = input("\nSelecciona una opción (1-3): ").strip()
    
    if option == "1":
        print("\nIniciando servidor...")
        if platform.system() == "Windows":
            os.system("python parques_server_improved.py")
        else:
            os.system("python3 parques_server_improved.py")
    elif option == "2":
        print("\nIniciando cliente gráfico...")
        if platform.system() == "Windows":
            os.system("python parques_client_gui.py")
        else:
            os.system("python3 parques_client_gui.py")
    elif option == "3":
        print("\n¡Gracias por usar Parqués Distribuido!")
        sys.exit(0)
    else:
        print("\nOpción no válida. Saliendo...")
        sys.exit(1)

def main():
    print("🎲 Configuración de Parqués Distribuido")
    print("="*60)
    
    check_python_version()
    install_dependencies()
    create_resource_directory()
    create_sound_files()
    run_game()

if __name__ == "__main__":
    main()