#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de Conexión para Parqués
Este script crea un mini-cliente y servidor simplificados para verificar que la comunicación funciona correctamente.
"""

import socket
import json
import threading
import time
import sys

# Configuración por defecto
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 12345

class MiniServer:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        
    def start(self):
        """Inicia el servidor mini"""
        try:
            # Intentar varias veces en caso de error "Address already in use"
            for attempt in range(5):
                try:
                    self.socket.bind((self.host, self.port))
                    break
                except OSError as e:
                    if "Address already in use" in str(e) and attempt < 4:
                        print(f"Puerto {self.port} ocupado, esperando 2 segundos...")
                        self.socket.close()
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        time.sleep(2)
                    else:
                        raise
            
            self.socket.listen(1)
            print(f"Mini servidor iniciado en {self.host}:{self.port}")
            
            # Aceptar una conexión
            client_socket, address = self.socket.accept()
            print(f"Cliente conectado desde {address}")
            
            # Manejar la conexión
            self.handle_client(client_socket, address)
            
        except Exception as e:
            print(f"Error en el mini servidor: {e}")
        finally:
            self.socket.close()
            print("Mini servidor detenido")
    
    def handle_client(self, client_socket, address):
        """Maneja una conexión de cliente"""
        try:
            # Recibir mensaje
            data = client_socket.recv(1024).decode('utf-8')
            print(f"Mensaje recibido: {data}")
            
            # Intentar parsear como JSON
            try:
                message = json.loads(data)
                print(f"Mensaje JSON: {message}")
                
                # Crear respuesta
                response = {
                    "status": "success",
                    "message": "Prueba exitosa",
                    "received": message
                }
                
                # Enviar respuesta
                json_response = json.dumps(response)
                client_socket.sendall(json_response.encode('utf-8'))
                print(f"Respuesta enviada: {json_response}")
                
            except json.JSONDecodeError:
                # Enviar error si el mensaje no es JSON válido
                error_response = {"status": "error", "message": "Mensaje JSON inválido"}
                client_socket.sendall(json.dumps(error_response).encode('utf-8'))
                print(f"Error: Mensaje no es JSON válido. Respuesta enviada: {json.dumps(error_response)}")
                
        except Exception as e:
            print(f"Error manejando cliente: {e}")
        finally:
            client_socket.close()
            print(f"Cliente {address} desconectado")

class MiniClient:
    def __init__(self, server_host=DEFAULT_HOST, server_port=DEFAULT_PORT):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
    
    def connect_and_test(self):
        """Conecta al servidor y realiza una prueba simple"""
        try:
            print(f"Conectando a {self.server_host}:{self.server_port}...")
            
            # Crear socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print("✅ Conexión establecida")
            
            # Crear mensaje de prueba
            test_message = {
                "action": "test",
                "data": "Hola servidor, esto es una prueba"
            }
            
            # Enviar mensaje
            json_message = json.dumps(test_message)
            self.socket.sendall(json_message.encode('utf-8'))
            print(f"Mensaje enviado: {json_message}")
            
            # Recibir respuesta
            self.socket.settimeout(5.0)  # 5 segundos de timeout
            
            response_data = self.socket.recv(4096).decode('utf-8')
            print(f"Datos recibidos (raw): {response_data}")
            
            # Intentar parsear la respuesta
            try:
                response = json.loads(response_data)
                print(f"✅ Respuesta JSON válida: {response}")
                
                if response.get("status") == "success":
                    print("✅ Prueba exitosa! La comunicación funciona correctamente.")
                else:
                    print(f"⚠️ El servidor respondió con error: {response.get('message', 'Error desconocido')}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error al decodificar JSON: {e}")
                print(f"Datos recibidos no son JSON válido: {response_data}")
            
        except socket.timeout:
            print("❌ Error: Tiempo de espera agotado")
        except ConnectionRefusedError:
            print("❌ Error: Conexión rechazada. Verifica que el servidor esté en ejecución.")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            if self.socket:
                self.socket.close()
                print("Socket cerrado")

def run_server_test():
    """Ejecuta el test del servidor"""
    # Solicitar configuración
    host = input(f"Host para el servidor (Enter para {DEFAULT_HOST}): ").strip()
    if not host:
        host = DEFAULT_HOST
    
    try:
        port = input(f"Puerto para el servidor (Enter para {DEFAULT_PORT}): ").strip()
        port = int(port) if port else DEFAULT_PORT
    except ValueError:
        print(f"Puerto inválido, usando {DEFAULT_PORT}")
        port = DEFAULT_PORT
    
    # Crear y ejecutar el mini servidor
    server = MiniServer(host, port)
    server.start()

def run_client_test():
    """Ejecuta el test del cliente"""
    # Solicitar configuración
    host = input(f"Host del servidor (Enter para {DEFAULT_HOST}): ").strip()
    if not host:
        host = DEFAULT_HOST
    
    try:
        port = input(f"Puerto del servidor (Enter para {DEFAULT_PORT}): ").strip()
        port = int(port) if port else DEFAULT_PORT
    except ValueError:
        print(f"Puerto inválido, usando {DEFAULT_PORT}")
        port = DEFAULT_PORT
    
    # Crear y ejecutar el mini cliente
    client = MiniClient(host, port)
    client.connect_and_test()

def main():
    print("🔍 Test de Conexión para Parqués")
    print("="*60)
    print("\nEste script verifica que la comunicación cliente-servidor funciona correctamente.")
    print("Elige una opción:")
    print("1. Iniciar servidor de prueba")
    print("2. Iniciar cliente de prueba")
    print("3. Salir")
    
    option = input("\nSelecciona una opción (1-3): ").strip()
    
    if option == "1":
        run_server_test()
    elif option == "2":
        run_client_test()
    else:
        print("Saliendo...")

if __name__ == "__main__":
    main()