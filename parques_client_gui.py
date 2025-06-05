#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente Gráfico de Parqués Distribuido
Sistemas Distribuidos - Proyecto Final
"""

import pygame
import socket
import json
import threading
import time
import sys
import random
import math
import os
from pygame.locals import *

# Inicializar pygame
pygame.init()
pygame.font.init()

# Configuración de la pantalla
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 700
BOARD_SIZE = 600

# Colores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
RED = (255, 50, 50)
BLUE = (50, 50, 255)
GREEN = (50, 180, 50)
YELLOW = (255, 255, 0)
PURPLE = (180, 50, 200)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)

# Mapeo de colores
COLOR_MAP = {
    'rojo': RED,
    'azul': BLUE,
    'verde': GREEN,
    'amarillo': YELLOW
}

# Fuentes
FONT_SMALL = pygame.font.SysFont('Arial', 14)
FONT_MEDIUM = pygame.font.SysFont('Arial', 18)
FONT_LARGE = pygame.font.SysFont('Arial', 24)
FONT_TITLE = pygame.font.SysFont('Arial', 36, bold=True)

class ParquesClientGUI:
    def __init__(self, server_host='localhost', server_port=12345):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.player_id = None
        self.player_name = None
        self.player_color = None
        self.game_state = None
        self.my_turn = False
        
        # Estado del juego local
        self.dice_values = (1, 1)
        self.dice_rolling = False
        self.dice_animation_start = 0
        self.dice_animation_duration = 1000  # ms
        self.status_message = "Conectándose al servidor..."
        self.selected_piece = None
        self.log_messages = []
        self.show_help_screen = False
        
        # UI State
        self.current_screen = "connect"  # connect, lobby, game
        self.can_start_game = False
        self.name_input = ""
        self.input_active = True
        self.animation_offset = 0
        self.animation_timer = 0
        
        # Thread para recibir actualizaciones del servidor
        self.update_thread = None
        self.running = True
        
        # Inicializar pantalla
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Parqués Distribuido")
        
        # Definir colores del mapa con los valores exactos de la imagen
        global COLOR_MAP
        COLOR_MAP = {
            'rojo': (234, 51, 35),      # Rojo brillante
            'verde': (51, 153, 51),     # Verde vibrante
            'amarillo': (255, 204, 0),  # Amarillo oro
            'azul': (0, 102, 204)       # Azul medio
        }
        
        # Modificar los colores globales para que coincidan con el estilo de la imagen
        global RED, GREEN, YELLOW, BLUE
        RED = COLOR_MAP['rojo']
        GREEN = COLOR_MAP['verde']
        YELLOW = COLOR_MAP['amarillo']
        BLUE = COLOR_MAP['azul']
        
        # Cargar sonidos
        self.sound_dice = None
        self.sound_move = None
        self.sound_capture = None
        self.sound_win = None
        
        self.load_sounds()
    
    def load_sounds(self):
        """Carga los archivos de sonido de manera robusta"""
        try:
            # Inicializar el mixer si no está inicializado
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            # Verificar si existe el directorio de recursos
            if not os.path.exists("resources"):
                os.makedirs("resources")
                print("Directorio 'resources' creado")
            
            # Intentar cargar cada sonido individualmente
            sound_files = [
                ("dice_roll.wav", "sound_dice"),
                ("piece_move.wav", "sound_move"),
                ("capture.wav", "sound_capture"),
                ("win.wav", "sound_win")
            ]
            
            for filename, attr_name in sound_files:
                filepath = os.path.join("resources", filename)
                
                # Si el archivo no existe, crear uno vacío
                if not os.path.exists(filepath):
                    print(f"Archivo de sonido '{filename}' no encontrado. Creando uno vacío.")
                    # Crear un archivo WAV mínimo
                    with open(filepath, "wb") as f:
                        # Escribir un encabezado WAV mínimo
                        f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
                
                # Cargar el sonido
                try:
                    setattr(self, attr_name, pygame.mixer.Sound(filepath))
                    print(f"Sonido '{filename}' cargado correctamente")
                except Exception as e:
                    print(f"Error cargando sonido '{filename}': {e}")
                    setattr(self, attr_name, None)
            
        except Exception as e:
            print(f"Error inicializando sonidos: {e}")
            # Establecer todos los sonidos como None
            self.sound_dice = None
            self.sound_move = None
            self.sound_capture = None
            self.sound_win = None
    
    def play_sound(self, sound_obj):
        """Reproduce un sonido de manera segura"""
        if sound_obj is not None and pygame.mixer.get_init():
            try:
                sound_obj.play()
            except Exception as e:
                print(f"Error reproduciendo sonido: {e}")
    
    def connect_to_server(self):
        """Conecta al servidor"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.status_message = f"Conectado al servidor {self.server_host}:{self.server_port}"
            self.add_log(f"Conectado al servidor {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            self.status_message = f"Error conectando al servidor: {e}"
            self.add_log(f"Error conectando al servidor: {e}")
            return False
    
    def send_message(self, message):
        """Envía un mensaje al servidor"""
        try:
            if self.connected and self.socket:
                # Enviar mensaje al servidor
                data = json.dumps(message)
                self.socket.send(data.encode('utf-8'))
                
                # Recibir respuesta completa (puede requerir múltiples lecturas)
                response_data = ""
                self.socket.settimeout(5.0)  # 5 segundos de timeout
                
                # Leer hasta encontrar un JSON completo
                buffer = ""
                json_depth = 0
                in_string = False
                escape_next = False
                
                while True:
                    chunk = self.socket.recv(4096).decode('utf-8')
                    if not chunk:
                        break
                    
                    buffer += chunk
                    
                    # Intentar encontrar un JSON completo
                    try:
                        response = json.loads(buffer)
                        # Si llegamos aquí, el JSON es válido
                        return response
                    except json.JSONDecodeError as e:
                        # Si el error no es por estar incompleto, buscar el primer JSON válido en el buffer
                        if "Expecting value" in str(e) and buffer.strip():
                            # Intenta encontrar donde comienza un JSON válido
                            for i in range(len(buffer)):
                                if buffer[i] in ['{', '[']:
                                    try:
                                        response = json.loads(buffer[i:])
                                        return response
                                    except:
                                        pass
                        
                        # Continuar recibiendo datos si el JSON está incompleto
                        if "Expecting" in str(e) or "Unterminated" in str(e):
                            continue
                        else:
                            # Error de formato, no solo incompleto
                            self.add_log(f"Error decodificando JSON: {str(e)}")
                            self.add_log(f"Datos recibidos: {buffer[:100]}...")
                            return {'status': 'error', 'message': f'Error de formato JSON: {str(e)}'}
                
                # Si llegamos aquí, no pudimos obtener un JSON válido
                self.add_log("Error: No se pudo obtener una respuesta JSON válida")
                return {'status': 'error', 'message': 'No se pudo obtener una respuesta JSON válida'}
                
        except socket.timeout:
            self.add_log("Error: Tiempo de espera agotado al comunicarse con el servidor")
            return {'status': 'error', 'message': 'Tiempo de espera agotado'}
        except ConnectionResetError:
            self.add_log("Error: Conexión cerrada por el servidor")
            self.connected = False
            return {'status': 'error', 'message': 'Conexión perdida'}
        except Exception as e:
            self.add_log(f"Error enviando mensaje: {e}")
            return {'status': 'error', 'message': f'Error de comunicación: {str(e)}'}
        
        return {'status': 'error', 'message': 'Error desconocido en la comunicación'}
    
    def join_game(self, name):
        """Únete al juego"""
        message = {
            'action': 'join',
            'name': name
        }
        
        response = self.send_message(message)
        
        if response and response.get('status') == 'success':
            self.player_name = name
            self.player_id = response.get('player_id')
            self.player_color = response.get('color')
            
            self.add_log(f"¡Te has unido al juego como {name}!")
            self.add_log(f"Tu color es: {self.player_color}")
            self.add_log(f"Jugadores conectados: {response.get('players_count', 0)}")
            
            self.current_screen = "lobby"
            
            # Actualizar estado de can_start
            self.can_start_game = response.get('can_start', False)
            
            if self.can_start_game:
                self.add_log("¡Ya se puede iniciar el juego!")
            else:
                self.add_log("Esperando más jugadores...")
            
            # Iniciar thread para recibir actualizaciones
            self.update_thread = threading.Thread(target=self.update_game_state_loop)
            self.update_thread.daemon = True
            self.update_thread.start()
            
            return True
        else:
            self.add_log(f"Error uniéndose al juego: {response.get('message', 'Error desconocido')}")
            return False
    
    def start_game(self):
        """Inicia el juego"""
        message = {'action': 'start_game'}
        response = self.send_message(message)
        
        if response and response.get('status') == 'success':
            self.add_log("¡El juego ha comenzado!")
            self.game_state = response.get('game_state')
            self.update_turn_status()
            self.current_screen = "game"
            return True
        else:
            self.add_log(f"Error iniciando el juego: {response.get('message', 'Error desconocido')}")
            return False
    
    def roll_dice(self):
        """Lanza los dados"""
        if not self.my_turn:
            self.add_log("¡No es tu turno!")
            return
        
        # Animación de dados
        self.dice_rolling = True
        self.dice_animation_start = pygame.time.get_ticks()
        self.play_sound(self.sound_dice)
        
        message = {'action': 'roll_dice'}
        response = self.send_message(message)
        
        if response and response.get('status') == 'success':
            self.dice_values = (response.get('dice1'), response.get('dice2'))
            is_pair = response.get('is_pair')
            total = response.get('total')
            
            self.add_log(f"🎲 Dados: {self.dice_values[0]} - {self.dice_values[1]} (Total: {total})")
            
            if is_pair:
                self.add_log("¡Sacaste pareja! 🎉")
                
                jail_move = response.get('jail_move')
                if jail_move:
                    if jail_move['success']:
                        self.add_log(f"✅ {jail_move['message']}")
                    else:
                        self.add_log(f"❌ {jail_move['message']}")
                
                if response.get('extra_turn'):
                    self.add_log("¡Puedes tirar de nuevo!")
            
            if response.get('can_move'):
                self.add_log(f"Puedes mover {total} casillas")
            
            if response.get('turn_ended'):
                self.add_log("Tu turno ha terminado")
                self.my_turn = False
                next_player = response.get('next_player')
                if next_player:
                    self.update_current_player(next_player)
            
        else:
            self.add_log(f"Error lanzando dados: {response.get('message', 'Error desconocido')}")
    
    def move_piece(self, piece_id, steps):
        """Mueve una ficha"""
        message = {
            'action': 'move_piece',
            'piece_id': piece_id,
            'steps': steps
        }
        
        response = self.send_message(message)
        
        if response and response.get('status') == 'success':
            self.add_log(f"✅ {response.get('message')}")
            
            self.play_sound(self.sound_move)
                
            # Actualizar estado del juego
            self.game_state = response.get('game_state')
            
            # Verificar si hay ganador
            if response.get('game_ended'):
                winner = response.get('winner')
                if winner:
                    if winner['id'] == self.player_id:
                        self.add_log("🏆 ¡HAS GANADO EL JUEGO! 🏆")
                        self.play_sound(self.sound_win)
                    else:
                        self.add_log(f"🏆 {winner['name']} ha ganado el juego")
                    return
            
            # Cambiar turno
            next_player = response.get('next_player')
            if next_player:
                self.update_current_player(next_player)
                self.my_turn = False
            
        else:
            self.add_log(f"❌ Error moviendo ficha: {response.get('message')}")
    
    def get_game_state(self):
        """Obtiene el estado actual del juego"""
        message = {'action': 'get_state'}
        response = self.send_message(message)
        
        if response and response.get('status') in ['success', 'update']:
            # Actualizar el estado del juego
            self.game_state = response.get('game_state')
            
            # Actualizar bandera de can_start si está presente
            if 'can_start' in response:
                self.can_start_game = response.get('can_start', False)
                
            # Actualizar estado del turno si el juego ha comenzado
            if self.game_state and self.game_state.get('game_started'):
                self.update_turn_status()
                
            return True
        return False
    
    def update_turn_status(self):
        """Actualiza el estado del turno"""
        if self.game_state:
            current_turn = self.game_state.get('current_turn')
            self.my_turn = (current_turn == self.player_id)
            
            if self.my_turn:
                self.add_log(f"🎯 ¡ES TU TURNO, {self.player_name}!")
            else:
                current_player_name = self.get_player_name(current_turn)
                self.add_log(f"⏳ Turno de: {current_player_name}")
    
    def update_current_player(self, player_id):
        """Actualiza el jugador actual"""
        if self.game_state:
            self.game_state['current_turn'] = player_id
            self.update_turn_status()
    
    def get_player_name(self, player_id):
        """Obtiene el nombre de un jugador por su ID"""
        if self.game_state and player_id in self.game_state.get('players', {}):
            return self.game_state['players'][player_id]['name']
        return "Desconocido"
    
    def update_game_state_loop(self):
        """Loop para actualizar el estado del juego periódicamente"""
        while self.running and self.connected:
            if self.current_screen in ["lobby", "game"]:
                self.get_game_state()
            time.sleep(0.5)  # Actualizar cada 0.5 segundos en lugar de 1 segundo
    
    def add_log(self, message):
        """Añade un mensaje al log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_messages.append(f"[{timestamp}] {message}")
        # Mantener solo los últimos 10 mensajes
        if len(self.log_messages) > 10:
            self.log_messages.pop(0)
        print(message)  # También imprimir en consola para debug
    
    def handle_events(self):
        """Maneja los eventos de pygame con soporte mejorado para UI"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
            
            # Conectar pantalla
            if self.current_screen == "connect":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.name_input.strip():
                            if self.connect_to_server():
                                self.join_game(self.name_input.strip())
                    elif event.key == pygame.K_BACKSPACE:
                        self.name_input = self.name_input[:-1]
                    else:
                        if len(self.name_input) < 12 and event.unicode.isprintable():  # Limitar longitud y caracteres válidos
                            self.name_input += event.unicode
                
                # Clic en botón de conexión
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, 390, 200, 50)
                    if button_rect.collidepoint(event.pos) and self.name_input.strip():
                        if self.connect_to_server():
                            self.join_game(self.name_input.strip())
                            
                    # Clic en campo de texto para activarlo
                    input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, 320, 300, 40)
                    self.input_active = input_rect.collidepoint(event.pos)
            
            # Lobby pantalla
            elif self.current_screen == "lobby":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    if self.can_start_game:
                        self.start_game()
                        
                # Clic en botón de inicio
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, 480, 200, 60)
                    if button_rect.collidepoint(event.pos) and self.can_start_game:
                        self.start_game()
                        
            # Juego pantalla
            elif self.current_screen == "game":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_h:
                        self.show_help_screen = not self.show_help_screen
                    elif event.key == pygame.K_r and self.my_turn and not self.dice_rolling:
                        self.roll_dice()
                    # Teclas de números para seleccionar fichas directamente
                    elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4] and self.my_turn:
                        piece_num = event.key - pygame.K_1  # 0-3
                        if self.game_state and self.player_id in self.game_state.get('players', {}):
                            pieces = self.game_state['players'][self.player_id]['pieces']
                            if piece_num < len(pieces):
                                if self.selected_piece == piece_num:
                                    # Si ya estaba seleccionada, intentar mover
                                    if not self.dice_rolling and pieces[piece_num]['position'] != 'home':
                                        if pieces[piece_num]['position'] == 'jail':
                                            # Para salir de la cárcel necesita pares
                                            if self.dice_values[0] == self.dice_values[1]:
                                                self.move_piece(piece_num, 0)
                                        else:
                                            # Mover normalmente
                                            total_steps = self.dice_values[0] + self.dice_values[1]
                                            self.move_piece(piece_num, total_steps)
                                    self.selected_piece = None
                                else:
                                    # Seleccionar esta ficha
                                    self.selected_piece = piece_num
                
                # Seleccionar ficha y mover con el mouse
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Botón izquierdo
                        mouse_pos = pygame.mouse.get_pos()
                        
                        # Si la ayuda está visible, verificar clic en botón cerrar
                        if self.show_help_screen:
                            close_rect = pygame.Rect(SCREEN_WIDTH // 2 - 70, SCREEN_HEIGHT // 2 + 190, 140, 40)
                            if close_rect.collidepoint(mouse_pos):
                                self.show_help_screen = False
                            continue  # No procesar más clics si la ayuda está visible
                        
                        # Botón de dados
                        dice_button_rect = pygame.Rect(680, 500, 180, 45)
                        if dice_button_rect.collidepoint(mouse_pos) and self.my_turn and not self.dice_rolling:
                            self.roll_dice()
                            continue
                            
                        # Seleccionar ficha
                        self.handle_piece_selection(mouse_pos)
        
        return True
    
    def handle_piece_selection(self, mouse_pos):
        """Maneja la selección de fichas con el ratón adaptado al nuevo diseño del tablero"""
        if not self.game_state or not self.my_turn:
            return
            
        # Solo seleccionar fichas si ya tiramos los dados
        if self.dice_rolling:
            return
            
        player = self.game_state['players'].get(self.player_id)
        if not player:
            return
            
        pieces = player['pieces']
        board_offset_x = (SCREEN_WIDTH - BOARD_SIZE) // 2
        board_offset_y = (SCREEN_HEIGHT - BOARD_SIZE) // 2
        
        # Comprobar cada ficha
        for i, piece in enumerate(pieces):
            piece_pos = piece['position']
            
            if piece_pos == 'jail':
                # Posición en la cárcel según el color
                jail_pos = self.get_jail_position(player['color'], i)
                piece_rect = pygame.Rect(jail_pos[0] - 18, jail_pos[1] - 18, 36, 36)
                
                if piece_rect.collidepoint(mouse_pos):
                    if self.selected_piece == i:
                        # Intentar sacar de la cárcel si es par
                        if self.dice_values[0] == self.dice_values[1]:
                            self.move_piece(i, 0)  # 0 porque es salida de cárcel
                        else:
                            self.add_log("Necesitas sacar pares para salir de la cárcel")
                    else:
                        self.selected_piece = i
                        self.add_log(f"Ficha {i+1} seleccionada")
                    return
                    
            elif piece_pos == 'home':
                # No se puede seleccionar una ficha que ya está en casa
                pass
                
            else:
                # Ficha en el tablero
                try:
                    piece_pos = int(piece_pos)
                    x, y = self.translate_server_position_to_board(piece_pos, board_offset_x, board_offset_y)
                    
                    piece_rect = pygame.Rect(x - 15, y - 15, 30, 30)
                    
                    if piece_rect.collidepoint(mouse_pos):
                        if self.selected_piece == i:
                            # Mover la ficha
                            total_steps = self.dice_values[0] + self.dice_values[1]
                            self.move_piece(i, total_steps)
                            self.selected_piece = None
                        else:
                            self.selected_piece = i
                            self.add_log(f"Ficha {i+1} seleccionada")
                        return
                except (ValueError, TypeError) as e:
                    print(f"Error al manejar posición de ficha: {e}")
        
        # Si hizo clic fuera de cualquier ficha, deseleccionar
        self.selected_piece = None
    
    def draw_connect_screen(self):
        """Dibuja la pantalla de conexión con estilo moderno"""
        # Fondo con gradiente
        self.draw_gradient_background()
        
        # Logo y título con efecto de sombra
        title_shadow = FONT_TITLE.render("PARQUÉS DISTRIBUIDO", True, (0, 0, 0, 150))
        title = FONT_TITLE.render("PARQUÉS DISTRIBUIDO", True, (255, 255, 255))
        
        # Dibujar sombra y luego el título
        self.screen.blit(title_shadow, (SCREEN_WIDTH // 2 - title.get_width() // 2 + 3, 103))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        
        # Subtítulo
        subtitle = FONT_LARGE.render("Sistemas Distribuidos - Proyecto Final", True, (180, 180, 200))
        self.screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 160))
        
        # Panel para la entrada de nombre
        login_panel = pygame.Rect(SCREEN_WIDTH // 2 - 200, 220, 400, 250)
        self.draw_glass_panel(login_panel, alpha=180)
        
        # Título del panel
        panel_title = FONT_LARGE.render("INICIAR SESIÓN", True, WHITE)
        self.screen.blit(panel_title, (SCREEN_WIDTH // 2 - panel_title.get_width() // 2, 240))
        
        # Campo de nombre con efecto moderno
        name_prompt = FONT_MEDIUM.render("Ingresa tu nombre:", True, WHITE)
        self.screen.blit(name_prompt, (SCREEN_WIDTH // 2 - 150, 290))
        
        # Campo de texto con efecto de focus
        input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, 320, 300, 40)
        
        # Determinar si el campo está activo para efectos visuales
        active_color = (100, 100, 180) if self.input_active else (60, 60, 100)
        
        # Dibujar campo con efecto 3D
        pygame.draw.rect(self.screen, (30, 30, 50), 
                         (input_rect.x, input_rect.y + 2, input_rect.width, input_rect.height), 0, 5)
        pygame.draw.rect(self.screen, active_color, 
                         (input_rect.x, input_rect.y, input_rect.width, input_rect.height), 0, 5)
        pygame.draw.rect(self.screen, (120, 120, 200), 
                         (input_rect.x, input_rect.y, input_rect.width, input_rect.height), 2, 5)
        
        # Texto del nombre
        name_text = FONT_MEDIUM.render(self.name_input, True, WHITE)
        self.screen.blit(name_text, (input_rect.x + 10, input_rect.y + 10))
        
        # Cursor de texto parpadeante
        if self.input_active and int(time.time() * 2) % 2 == 0:
            cursor_x = input_rect.x + 10 + name_text.get_width()
            pygame.draw.rect(self.screen, WHITE, (cursor_x, input_rect.y + 8, 2, 24))
        
        # Botón de conexión con efecto de hover
        button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, 390, 200, 50)
        
        # Verificar si el mouse está sobre el botón
        mouse_pos = pygame.mouse.get_pos()
        button_hover = button_rect.collidepoint(mouse_pos)
        
        # Color del botón según estado
        button_color = GREEN if self.name_input.strip() else DARK_GRAY
        if button_hover and self.name_input.strip():
            button_color = self.lighten_color(GREEN, 1.2)  # Más brillante al hacer hover
        
        # Dibujar botón con efecto 3D
        pygame.draw.rect(self.screen, self.darken_color(button_color, 0.7), 
                         (button_rect.x, button_rect.y + 3, button_rect.width, button_rect.height), 0, 10)
        pygame.draw.rect(self.screen, button_color, 
                         (button_rect.x, button_rect.y, button_rect.width, button_rect.height), 0, 10)
        
        button_text = FONT_MEDIUM.render("CONECTAR", True, WHITE)
        self.screen.blit(button_text, (SCREEN_WIDTH // 2 - button_text.get_width() // 2, button_rect.y + 15))
        
        # Estado de conexión
        status_panel = pygame.Rect(SCREEN_WIDTH // 2 - 350, 500, 700, 50)
        self.draw_glass_panel(status_panel, alpha=150)
        
        status_text = FONT_MEDIUM.render(self.status_message, True, CYAN if "Conectado" in self.status_message else GRAY)
        self.screen.blit(status_text, (SCREEN_WIDTH // 2 - status_text.get_width() // 2, 515))
        
        # Instrucciones
        inst_panel = pygame.Rect(SCREEN_WIDTH // 2 - 300, 580, 600, 80)
        self.draw_glass_panel(inst_panel, alpha=120)
        
        inst1 = FONT_MEDIUM.render("Escribe tu nombre y presiona ENTER para conectar", True, WHITE)
        self.screen.blit(inst1, (SCREEN_WIDTH // 2 - inst1.get_width() // 2, 600))
        
        # Versión
        version_text = FONT_SMALL.render("v1.0 - 2025", True, GRAY)
        self.screen.blit(version_text, (SCREEN_WIDTH - version_text.get_width() - 10, SCREEN_HEIGHT - 30))
        
        # Dibujar dados decorativos
        self.draw_decorative_dice()
    
    def draw_decorative_dice(self):
        """Dibuja dados decorativos en la pantalla de conexión"""
        # Posiciones para dados decorativos
        dice_positions = [
            (100, 100, 60, random.randint(1, 6), random.uniform(0, 0.5)),
            (SCREEN_WIDTH - 160, 100, 60, random.randint(1, 6), random.uniform(0, 0.5)),
            (150, SCREEN_HEIGHT - 150, 50, random.randint(1, 6), random.uniform(0, 0.5)),
            (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 150, 50, random.randint(1, 6), random.uniform(0, 0.5))
        ]
        
        # Dibujar cada dado con un ángulo aleatorio
        for x, y, size, value, anim in dice_positions:
            self.draw_single_die(x, y, size, value, anim)
    
    def draw_gradient_background(self):
        """Dibuja un fondo con gradiente"""
        # Crear superficie para el gradiente
        gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Colores del gradiente
        color1 = (20, 20, 35)  # Azul oscuro
        color2 = (60, 30, 80)  # Púrpura oscuro
        
        # Dibujar gradiente
        for y in range(SCREEN_HEIGHT):
            # Calcular proporción de mezcla
            ratio = y / SCREEN_HEIGHT
            
            # Interpolar colores
            r = color1[0] * (1 - ratio) + color2[0] * ratio
            g = color1[1] * (1 - ratio) + color2[1] * ratio
            b = color1[2] * (1 - ratio) + color2[2] * ratio
            
            # Dibujar línea de color
            pygame.draw.line(gradient, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
        # Añadir un poco de "ruido" para textura
        for i in range(200):
            x = random.randint(0, SCREEN_WIDTH - 1)
            y = random.randint(0, SCREEN_HEIGHT - 1)
            radius = random.randint(1, 3)
            alpha = random.randint(10, 30)
            pygame.draw.circle(gradient, (255, 255, 255, alpha), (x, y), radius)
        
        # Dibujar el gradiente en la pantalla
        self.screen.blit(gradient, (0, 0))
        
    def draw_glass_panel(self, rect, alpha=150):
        """Dibuja un panel con efecto de vidrio (glassmorphism)"""
        # Crear superficie con transparencia
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        # Color base del panel (semi-transparente)
        panel_color = (60, 60, 80, alpha)
        pygame.draw.rect(panel, panel_color, (0, 0, rect.width, rect.height), 0, 10)
        
        # Añadir borde brillante en la parte superior e izquierda (efecto de luz)
        highlight_color = (255, 255, 255, 30)
        pygame.draw.rect(panel, highlight_color, (0, 0, rect.width, rect.height), 2, 10)
        
        # Añadir un poco de "brillo" en la esquina superior izquierda
        pygame.draw.circle(panel, (255, 255, 255, 15), (15, 15), 20)
        
        # Dibujar el panel en la pantalla
        self.screen.blit(panel, (rect.x, rect.y))
    
    def draw_lobby_screen(self):
        """Dibuja la pantalla de lobby con estilo moderno"""
        # Fondo con gradiente
        self.draw_gradient_background()
        
        # Título con efecto de profundidad
        title_shadow = FONT_TITLE.render("SALA DE ESPERA", True, BLACK)
        title = FONT_TITLE.render("SALA DE ESPERA", True, WHITE)
        self.screen.blit(title_shadow, (SCREEN_WIDTH // 2 - title.get_width() // 2 + 2, 52))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        
        # Panel del jugador
        player_panel = pygame.Rect(SCREEN_WIDTH // 2 - 200, 120, 400, 80)
        self.draw_glass_panel(player_panel)
        
        # Información del jugador
        player_info = FONT_LARGE.render(f"Nombre: {self.player_name}", True, WHITE)
        self.screen.blit(player_info, (SCREEN_WIDTH // 2 - player_info.get_width() // 2, 130))
        
        color_text = FONT_MEDIUM.render(f"Color asignado: ", True, WHITE)
        self.screen.blit(color_text, (SCREEN_WIDTH // 2 - 150, 170))
        
        # Rectángulo de color con efecto 3D
        color_value = COLOR_MAP.get(self.player_color, WHITE)
        pygame.draw.rect(self.screen, self.darken_color(color_value, 0.7), 
                        (SCREEN_WIDTH // 2 + 30, 172, 100, 25), 0, 5)  # Sombra
        pygame.draw.rect(self.screen, color_value, 
                        (SCREEN_WIDTH // 2 + 30, 170, 100, 25), 0, 5)  # Color
        
        # Lista de jugadores en un panel estilizado
        if self.game_state:
            players = self.game_state.get('players', {})
            
            players_panel = pygame.Rect(SCREEN_WIDTH // 2 - 250, 220, 500, 220)
            self.draw_glass_panel(players_panel)
            
            players_title = FONT_LARGE.render("Jugadores conectados:", True, WHITE)
            self.screen.blit(players_title, (SCREEN_WIDTH // 2 - players_title.get_width() // 2, 230))
            
            # Línea separadora
            pygame.draw.line(self.screen, (150, 150, 180, 150), 
                            (players_panel.x + 20, 265), 
                            (players_panel.x + players_panel.width - 20, 265), 2)
            
            # Mostrar jugadores en una cuadrícula 2x2
            player_cards = []
            for player_id, player_info in players.items():
                player_cards.append((player_info['name'], player_info['color']))
            
            # Asegurar que siempre hay 4 espacios (incluso si están vacíos)
            while len(player_cards) < 4:
                player_cards.append(("Esperando...", None))
            
            # Dibujar tarjetas de jugador
            card_width, card_height = 230, 70
            positions = [
                (players_panel.x + 20, 280),
                (players_panel.x + players_panel.width - 20 - card_width, 280),
                (players_panel.x + 20, 360),
                (players_panel.x + players_panel.width - 20 - card_width, 360)
            ]
            
            for i, ((name, color), pos) in enumerate(zip(player_cards, positions)):
                self.draw_player_card(pos[0], pos[1], card_width, card_height, name, color, i)
        
        # Botón de inicio con efectos
        start_panel = pygame.Rect(SCREEN_WIDTH // 2 - 150, 460, 300, 100)
        self.draw_glass_panel(start_panel)
        
        # Verificar hover para efecto
        mouse_pos = pygame.mouse.get_pos()
        button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, 480, 200, 60)
        button_hover = button_rect.collidepoint(mouse_pos)
        
        button_color = GREEN if self.can_start_game else DARK_GRAY
        if button_hover and self.can_start_game:
            button_color = self.lighten_color(GREEN, 1.2)
        
        # Botón con efecto 3D
        pygame.draw.rect(self.screen, self.darken_color(button_color, 0.7), 
                        (button_rect.x, button_rect.y + 3, button_rect.width, button_rect.height), 0, 10)
        pygame.draw.rect(self.screen, button_color, 
                        (button_rect.x, button_rect.y, button_rect.width, button_rect.height), 0, 10)
        
        start_text = FONT_LARGE.render("INICIAR JUEGO", True, WHITE)
        self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, 500))
        
        # Mensajes del sistema
        log_panel = pygame.Rect(SCREEN_WIDTH // 2 - 400, 580, 800, 100)
        self.draw_glass_panel(log_panel)
        self.draw_log_messages(SCREEN_WIDTH // 2 - 390, 590, 780, 80)
        
        # Instrucción
        if self.can_start_game:
            inst = FONT_MEDIUM.render("Presiona ENTER para iniciar el juego", True, CYAN)
            self.screen.blit(inst, (SCREEN_WIDTH // 2 - inst.get_width() // 2, 700))
        else:
            inst = FONT_MEDIUM.render("Esperando a que se conecten más jugadores...", True, GRAY)
            self.screen.blit(inst, (SCREEN_WIDTH // 2 - inst.get_width() // 2, 700))
            
    def draw_player_card(self, x, y, width, height, player_name, color, index):
        """Dibuja una tarjeta de jugador en el lobby"""
        # Fondo de la tarjeta
        card_color = (50, 50, 70, 200)
        if color:  # Si hay un color asignado (jugador real)
            # Usar un tono del color del jugador como fondo
            color_value = COLOR_MAP.get(color, (200, 200, 200))
            card_color = (*self.darken_color(color_value, 0.3), 150)
        
        # Dibujar tarjeta
        card_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(card_surface, card_color, (0, 0, width, height), 0, 10)
        
        # Borde
        border_color = (150, 150, 180, 100) if color else (100, 100, 120, 100)
        pygame.draw.rect(card_surface, border_color, (0, 0, width, height), 2, 10)
        
        # Número de jugador
        num_text = FONT_MEDIUM.render(f"Jugador {index + 1}", True, WHITE)
        card_surface.blit(num_text, (10, 10))
        
        # Nombre del jugador
        name_color = WHITE if color else GRAY
        name_text = FONT_LARGE.render(player_name, True, name_color)
        card_surface.blit(name_text, (20, 35))
        
        # Mostrar color si está asignado
        if color:
            color_value = COLOR_MAP.get(color, WHITE)
            pygame.draw.rect(card_surface, color_value, (width - 50, 10, 30, 30), 0, 5)
        
        # Dibujar la tarjeta en la pantalla
        self.screen.blit(card_surface, (x, y))
    
    def draw_game_screen(self):
        """Dibuja la pantalla de juego con el tablero estilo clásico"""
        # Fondo con color sólido
        self.screen.fill((40, 40, 60))
        
        # Dibujar tablero
        self.draw_board()
        
        # Panel lateral con efecto de vidrio
        panel_rect = pygame.Rect(650, 20, 230, 660)
        self.draw_glass_panel(panel_rect)
        
        # Título del panel
        title = FONT_LARGE.render("PARQUÉS", True, WHITE)
        self.screen.blit(title, (765 - title.get_width() // 2, 35))
        
        # Información del jugador con diseño moderno
        player_panel = pygame.Rect(660, 70, 210, 70)
        self.draw_glass_panel(player_panel, alpha=180)
        
        player_text = FONT_MEDIUM.render(f"{self.player_name}", True, WHITE)
        self.screen.blit(player_text, (765 - player_text.get_width() // 2, 80))
        
        color_text = FONT_SMALL.render(f"Color: ", True, WHITE)
        self.screen.blit(color_text, (670, 110))
        
        color_value = COLOR_MAP.get(self.player_color, WHITE)
        pygame.draw.rect(self.screen, color_value, (720, 110, 80, 20), 0, 5)
        
        # Estado del turno con animación
        if self.game_state:
            current_turn = self.game_state.get('current_turn')
            current_player_name = self.get_player_name(current_turn)
            current_player_color = self.game_state['players'][current_turn]['color']
            
            turn_panel = pygame.Rect(660, 150, 210, 90)
            self.draw_glass_panel(turn_panel, alpha=180)
            
            turn_text = FONT_MEDIUM.render("TURNO ACTUAL:", True, WHITE)
            self.screen.blit(turn_text, (765 - turn_text.get_width() // 2, 160))
            
            player_turn_text = FONT_MEDIUM.render(current_player_name, True, WHITE)
            self.screen.blit(player_turn_text, (765 - player_turn_text.get_width() // 2, 190))
            
            # Color del jugador actual
            color_value = COLOR_MAP.get(current_player_color, WHITE)
            pygame.draw.rect(self.screen, color_value, (765 - 40, 220, 80, 8), 0, 4)
            
            # Indicador de mi turno con animación pulsante
            if self.my_turn:
                pulse_size = (math.sin(pygame.time.get_ticks() * 0.005) + 1) * 5
                my_turn_text = FONT_MEDIUM.render("¡ES TU TURNO!", True, GREEN)
                text_width = my_turn_text.get_width()
                self.screen.blit(my_turn_text, (765 - text_width // 2, 240))
                
                # Indicador animado
                pygame.draw.circle(self.screen, GREEN, (765 - text_width//2 - 15, 250), 5 + pulse_size, 0)
        
        # Dados con mejor diseño
        self.draw_dice(710, 300, 70)
        
        # Botón de tirar dados con efecto de hover
        mouse_pos = pygame.mouse.get_pos()
        dice_button_rect = pygame.Rect(680, 500, 180, 45)
        button_hover = dice_button_rect.collidepoint(mouse_pos)
        
        dice_button_color = GREEN if self.my_turn and not self.dice_rolling else DARK_GRAY
        if button_hover and self.my_turn and not self.dice_rolling:
            dice_button_color = self.lighten_color(GREEN, 1.2)
        
        # Efecto de botón elevado
        pygame.draw.rect(self.screen, self.darken_color(dice_button_color, 0.7), 
                        (dice_button_rect.x, dice_button_rect.y + 5, dice_button_rect.width, dice_button_rect.height), 0, 10)
        pygame.draw.rect(self.screen, dice_button_color, 
                        (dice_button_rect.x, dice_button_rect.y, dice_button_rect.width, dice_button_rect.height), 0, 10)
        
        dice_button_text = FONT_MEDIUM.render("TIRAR DADOS", True, WHITE)
        self.screen.blit(dice_button_text, (680 + 90 - dice_button_text.get_width() // 2, 510))
        
        # Estadísticas de juego
        if self.game_state and self.player_id in self.game_state.get('players', {}):
            stats_panel = pygame.Rect(660, 390, 210, 100)
            self.draw_glass_panel(stats_panel, alpha=180)
            
            stats_title = FONT_SMALL.render("ESTADÍSTICAS", True, WHITE)
            self.screen.blit(stats_title, (765 - stats_title.get_width() // 2, 400))
            
            player = self.game_state['players'][self.player_id]
            
            # Fichas en cárcel
            jail_text = FONT_SMALL.render(f"En cárcel: {player['in_jail']}/4", True, WHITE)
            self.screen.blit(jail_text, (670, 425))
            
            # Barra de progreso para fichas en cárcel
            jail_percent = player['in_jail'] / 4
            pygame.draw.rect(self.screen, DARK_GRAY, (670, 445, 190, 10), 0, 5)
            pygame.draw.rect(self.screen, RED, (670, 445, int(190 * jail_percent), 10), 0, 5)
            
            # Fichas en casa
            home_text = FONT_SMALL.render(f"En casa: {player['finished_pieces']}/4", True, WHITE)
            self.screen.blit(home_text, (670, 465))
            
            # Barra de progreso para fichas en casa
            home_percent = player['finished_pieces'] / 4
            pygame.draw.rect(self.screen, DARK_GRAY, (670, 485, 190, 10), 0, 5)
            pygame.draw.rect(self.screen, GREEN, (670, 485, int(190 * home_percent), 10), 0, 5)
        
        # Mensajes del sistema en panel de cristal
        log_panel = pygame.Rect(660, 560, 210, 110)
        self.draw_glass_panel(log_panel, alpha=180)
        self.draw_log_messages(670, 570, 190, 90)
        
        # Ayuda
        help_text = FONT_SMALL.render("Presiona H para ayuda", True, GRAY)
        self.screen.blit(help_text, (765 - help_text.get_width() // 2, 680))
        
        # Pantalla de ayuda
        if self.show_help_screen:
            self.draw_help_screen()
    
    def draw_board(self, board_offset_x=0, board_offset_y=0):
        """Dibuja el tablero de juego al estilo clásico como en la imagen de referencia"""
        # Tamaño y posición del tablero
        if board_offset_x == 0 and board_offset_y == 0:
            board_offset_x = (SCREEN_WIDTH - BOARD_SIZE) // 2
            board_offset_y = (SCREEN_HEIGHT - BOARD_SIZE) // 2

        # Dibujar el borde exterior del tablero (marrón)
        border_color = (139, 69, 19)  # Marrón
        border_width = 20
        pygame.draw.rect(self.screen, border_color, 
                         (board_offset_x - border_width, board_offset_y - border_width, 
                          BOARD_SIZE + 2*border_width, BOARD_SIZE + 2*border_width), 0, 15)

        # Fondo del tablero (beige claro)
        board_color = (245, 222, 179)  # Beige
        pygame.draw.rect(self.screen, board_color, 
                         (board_offset_x, board_offset_y, BOARD_SIZE, BOARD_SIZE), 0, 10)

        # Dibujar las cárceles en las esquinas
        jail_size = BOARD_SIZE // 4
        jail_colors = {
            'rojo': (1, 0),    # Esquina superior derecha
            'verde': (0, 0),   # Esquina superior izquierda
            'amarillo': (0, 1),  # Esquina inferior izquierda
            'azul': (1, 1)     # Esquina inferior derecha
        }
        
        # Dibujar cárceles
        for color, (col, row) in jail_colors.items():
            jail_x = board_offset_x + col * (BOARD_SIZE - jail_size)
            jail_y = board_offset_y + row * (BOARD_SIZE - jail_size)

            # Color base de la cárcel
            color_value = COLOR_MAP.get(color, WHITE)
            pygame.draw.rect(self.screen, color_value, (jail_x, jail_y, jail_size, jail_size), 0, 0)

            # Área de las fichas (más oscura)
            inner_margin = jail_size // 10
            inner_size = jail_size - 2 * inner_margin
            inner_color = self.darken_color(color_value, 0.8)
            pygame.draw.rect(self.screen, inner_color, 
                             (jail_x + inner_margin, jail_y + inner_margin, 
                              inner_size, inner_size), 0, 0)

        # Dibujar el centro del tablero (cruz de colores)
        # Calcular el centro del tablero
        center_x = board_offset_x + BOARD_SIZE // 2
        center_y = board_offset_y + BOARD_SIZE // 2

        # Tamaño de la cruz del centro
        cross_size = jail_size  # El mismo tamaño que las cárceles
        half_cross = cross_size // 2

        # Puntos para los triángulos, creando la cruz de colores
        # Triángulo superior izquierdo (verde)
        pygame.draw.polygon(self.screen, COLOR_MAP['verde'],
                           [(center_x - half_cross, center_y - half_cross),  # Esquina superior izquierda
                            (center_x, center_y),                           # Centro
                            (center_x - half_cross, center_y)])             # Punto medio izquierdo

        # Triángulo superior derecho (rojo)
        pygame.draw.polygon(self.screen, COLOR_MAP['rojo'],
                           [(center_x + half_cross, center_y - half_cross),  # Esquina superior derecha
                            (center_x, center_y),                           # Centro
                            (center_x + half_cross, center_y)])             # Punto medio derecho

        # Triángulo inferior izquierdo (amarillo)
        pygame.draw.polygon(self.screen, COLOR_MAP['amarillo'],
                           [(center_x - half_cross, center_y + half_cross),  # Esquina inferior izquierda
                            (center_x, center_y),                           # Centro
                            (center_x - half_cross, center_y)])             # Punto medio izquierdo

        # Triángulo inferior derecho (azul)
        pygame.draw.polygon(self.screen, COLOR_MAP['azul'],
                           [(center_x + half_cross, center_y + half_cross),  # Esquina inferior derecha
                            (center_x, center_y),                           # Centro
                            (center_x + half_cross, center_y)])             # Punto medio derecho

        # Dibujar las casillas del tablero
        self.draw_board_squares(board_offset_x, board_offset_y)

        # Dibujar las fichas
        self.draw_pieces(board_offset_x, board_offset_y)
    
    def draw_board_squares(self, board_offset_x, board_offset_y):
        """Dibuja las casillas del tablero como en la imagen de referencia"""
        # Calcular dimensiones
        jail_size = BOARD_SIZE // 4
        square_width = jail_size // 2
        square_height = square_width // 2
        
        # Colores de las casillas por cada segmento
        segment_colors = {
            'rojo': COLOR_MAP['rojo'],
            'verde': COLOR_MAP['verde'],
            'amarillo': COLOR_MAP['amarillo'],
            'azul': COLOR_MAP['azul']
        }
        
        # Dibujar casillas horizontales superiores (entre verde y rojo)
        for i in range(1, 7):
            x = board_offset_x + jail_size + i * square_width
            y = board_offset_y
            color = segment_colors['verde'] if 2 <= i <= 6 else (255, 255, 255)
            pygame.draw.rect(self.screen, color, (x, y, square_width, jail_size // 2), 0)

        # Dibujar casillas horizontales inferiores (entre amarillo y azul)
        for i in range(1, 7):
            x = board_offset_x + jail_size + i * square_width
            y = board_offset_y + BOARD_SIZE - jail_size // 2
            color = segment_colors['azul'] if 2 <= i <= 6 else (255, 255, 255)
            pygame.draw.rect(self.screen, color, (x, y, square_width, jail_size // 2), 0)

        # Dibujar casillas verticales izquierdas (entre verde y amarillo)
        for i in range(1, 7):
            x = board_offset_x
            y = board_offset_y + jail_size + i * square_height
            color = segment_colors['amarillo'] if 2 <= i <= 6 else (255, 255, 255)
            pygame.draw.rect(self.screen, color, (x, y, jail_size // 2, square_height), 0)

        # Dibujar casillas verticales derechas (entre rojo y azul)
        for i in range(1, 7):
            x = board_offset_x + BOARD_SIZE - jail_size // 2
            y = board_offset_y + jail_size + i * square_height
            color = segment_colors['rojo'] if 2 <= i <= 6 else (255, 255, 255)
            pygame.draw.rect(self.screen, color, (x, y, jail_size // 2, square_height), 0)

    def draw_pieces(self, board_offset_x, board_offset_y):
        """Dibuja las fichas en el tablero con estilo 3D con anillos blancos"""
        if not self.game_state:
            return
            
        players = self.game_state.get('players', {})
        
        for player_id, player_info in players.items():
            color = player_info['color']
            pieces = player_info['pieces']
            
            for i, piece in enumerate(pieces):
                position = piece['position']
                base_color = COLOR_MAP.get(color, WHITE)
                
                if position == 'jail':
                    # Obtener posición en la cárcel
                    jail_pos = self.get_jail_position(color, i)
                    
                    # Dibujar ficha con efecto 3D y anillo blanco
                    # Sombra
                    pygame.draw.circle(self.screen, self.darken_color(base_color, 0.5), 
                                     (jail_pos[0] + 3, jail_pos[1] + 3), 18)
                    # Base de la ficha
                    pygame.draw.circle(self.screen, base_color, jail_pos, 18)
                    # Anillo blanco
                    pygame.draw.circle(self.screen, (255, 255, 255), jail_pos, 10)
                    # Interior del color
                    pygame.draw.circle(self.screen, base_color, jail_pos, 6)
                
                elif position == 'home':
                    # No dibujamos las fichas que ya llegaron a casa
                    continue
                else:
                    # Dibujar en el tablero
                    try:
                        # Convertir la posición del servidor al formato de nuestro tablero
                        board_pos = int(position)
                        x, y = self.translate_server_position_to_board(board_pos, board_offset_x, board_offset_y)
                        
                        # Sombra
                        pygame.draw.circle(self.screen, self.darken_color(base_color, 0.5), 
                                         (x + 3, y + 3), 15)
                        # Base de la ficha
                        pygame.draw.circle(self.screen, base_color, (x, y), 15)
                        # Anillo blanco
                        pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 8)
                        # Interior del color
                        pygame.draw.circle(self.screen, base_color, (x, y), 5)
                        
                        # Resaltar si está seleccionada
                        if player_id == self.player_id and self.selected_piece == i:
                            pygame.draw.circle(self.screen, WHITE, (x, y), 18, 2)
                    except (ValueError, TypeError) as e:
                        pass
    
    def draw_dice(self, x, y, size):
        """Dibuja los dados con efectos visuales mejorados"""
        # Animar si están rodando
        if self.dice_rolling:
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.dice_animation_start
            
            if elapsed < self.dice_animation_duration:
                # Durante la animación mostrar valores aleatorios y rotación
                animation_progress = elapsed / self.dice_animation_duration
                shake_amount = (1 - animation_progress) * 10  # Disminuye con el tiempo
                
                # Posiciones con "sacudida" aleatoria
                shake_x1 = x + random.uniform(-shake_amount, shake_amount)
                shake_y1 = y + random.uniform(-shake_amount, shake_amount)
                shake_x2 = x + size + 20 + random.uniform(-shake_amount, shake_amount)
                shake_y2 = y + random.uniform(-shake_amount, shake_amount)
                
                temp_dice1 = random.randint(1, 6)
                temp_dice2 = random.randint(1, 6)
                
                self.draw_single_die(shake_x1, shake_y1, size, temp_dice1, animation_progress)
                self.draw_single_die(shake_x2, shake_y2, size, temp_dice2, animation_progress)
            else:
                # Finalizar animación
                self.dice_rolling = False
                
                self.draw_single_die(x, y, size, self.dice_values[0], 0)
                self.draw_single_die(x + size + 20, y, size, self.dice_values[1], 0)
        else:
            # Dibujar dados con valores actuales
            self.draw_single_die(x, y, size, self.dice_values[0], 0)
            self.draw_single_die(x + size + 20, y, size, self.dice_values[1], 0)
    
    def draw_single_die(self, x, y, size, value, animation_progress=0):
        """Dibuja un dado individual con efectos visuales mejorados"""
        # Calcular rotación para la animación
        rotation_angle = animation_progress * 360  # Grados de rotación
        
        # Colores del dado
        die_color = (230, 230, 230)  # Blanco ligeramente grisáceo
        dot_color = (30, 30, 30)     # Negro suave
        
        # Crear superficie para el dado
        die_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Fondo del dado (con sombra)
        pygame.draw.rect(die_surface, (30, 30, 40, 100), (4, 4, size, size), 0, 10)  # Sombra
        pygame.draw.rect(die_surface, die_color, (0, 0, size, size), 0, 10)  # Dado
        
        # Efecto de borde
        pygame.draw.rect(die_surface, (200, 200, 200), (0, 0, size, size), 2, 10)
        
        # Efecto de luz en la esquina
        pygame.draw.circle(die_surface, (255, 255, 255, 100), (size//4, size//4), size//10)
        
        # Dibujar puntos según el valor
        dot_radius = size // 10
        positions = []
        
        if value == 1:
            positions = [(0.5, 0.5)]
        elif value == 2:
            positions = [(0.25, 0.25), (0.75, 0.75)]
        elif value == 3:
            positions = [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)]
        elif value == 4:
            positions = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
        elif value == 5:
            positions = [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)]
        elif value == 6:
            positions = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.5), (0.75, 0.5), (0.25, 0.75), (0.75, 0.75)]
        
        for px, py in positions:
            dot_x = int(px * size)
            dot_y = int(py * size)
            
            # Dibujar punto con efecto 3D
            pygame.draw.circle(die_surface, (10, 10, 10), (dot_x + 1, dot_y + 1), dot_radius)  # Sombra
            pygame.draw.circle(die_surface, dot_color, (dot_x, dot_y), dot_radius)  # Punto
        
        # Aplicar rotación si está en animación
        if animation_progress > 0:
            die_surface = pygame.transform.rotate(die_surface, rotation_angle)
            # Recalcular tamaño después de rotación
            new_rect = die_surface.get_rect(center=(x + size//2, y + size//2))
            self.screen.blit(die_surface, new_rect.topleft)
        else:
            # Sin rotación
            self.screen.blit(die_surface, (x, y))
    
    def draw_log_messages(self, x, y, width, height):
        """Dibuja los mensajes del log con estilo moderno"""
        # Título
        log_title = FONT_SMALL.render("MENSAJES", True, WHITE)
        self.screen.blit(log_title, (x + width//2 - log_title.get_width()//2, y))
        
        # Línea separadora
        pygame.draw.line(self.screen, (100, 100, 120, 128), 
                         (x, y + 20), (x + width, y + 20), 1)
        
        # Mensajes
        msg_y = y + 25
        for msg in self.log_messages[-5:]:  # Mostrar solo los últimos 5 mensajes
            # Detectar tipos de mensajes especiales para colorear
            text_color = WHITE
            if "tu turno" in msg.lower() or "¡es tu turno" in msg.lower():
                text_color = GREEN
            elif "capturó" in msg.lower():
                text_color = ORANGE
            elif "error" in msg.lower():
                text_color = RED
            elif "ganado" in msg.lower() or "victoria" in msg.lower():
                text_color = YELLOW
                
            # Extraer timestamp si existe
            if "[" in msg and "]" in msg:
                timestamp_end = msg.find("]") + 1
                timestamp = msg[:timestamp_end]
                message = msg[timestamp_end:].strip()
                
                # Timestamp en gris
                time_surface = FONT_SMALL.render(timestamp, True, GRAY)
                self.screen.blit(time_surface, (x, msg_y))
                
                # Mensaje con color según tipo
                message_surface = FONT_SMALL.render(message, True, text_color)
                
                # Verificar si el mensaje es demasiado largo
                if message_surface.get_width() > width - 5:
                    # Truncar y añadir "..."
                    truncated_len = 20  # Longitud máxima aproximada
                    if len(message) > truncated_len:
                        message = message[:truncated_len] + "..."
                    message_surface = FONT_SMALL.render(message, True, text_color)
                
                self.screen.blit(message_surface, (x, msg_y + 15))
                msg_y += 35
            else:
                # Si no tiene timestamp, mostrar el mensaje completo
                text_surface = FONT_SMALL.render(msg, True, text_color)
                
                # Truncar si es necesario
                if text_surface.get_width() > width - 10:
                    truncated_len = 25
                    if len(msg) > truncated_len:
                        msg = msg[:truncated_len] + "..."
                    text_surface = FONT_SMALL.render(msg, True, text_color)
                
                self.screen.blit(text_surface, (x, msg_y))
                msg_y += 20
            
            if msg_y > y + height - 10:
                break
    
    def draw_help_screen(self):
        """Dibuja la pantalla de ayuda adaptada al nuevo diseño del tablero"""
        # Fondo semitransparente
        help_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        help_surface.fill((0, 0, 20, 230))  # Azul muy oscuro semi-transparente
        self.screen.blit(help_surface, (0, 0))
        
        # Ventana de ayuda con efecto de vidrio
        help_rect = pygame.Rect(SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 250, 600, 500)
        self.draw_glass_panel(help_rect, alpha=200)
        
        # Título con borde brillante
        title_rect = pygame.Rect(help_rect.x + 20, help_rect.y + 20, help_rect.width - 40, 50)
        pygame.draw.rect(self.screen, (80, 60, 120), title_rect, 0, 10)
        pygame.draw.rect(self.screen, (120, 100, 180), title_rect, 2, 10)
        
        help_title = FONT_LARGE.render("CÓMO JUGAR AL PARQUÉS", True, WHITE)
        self.screen.blit(help_title, (SCREEN_WIDTH // 2 - help_title.get_width() // 2, help_rect.y + 30))
        
        # Instrucciones con iconos y mejor formato
        instructions = [
            ("🎯", "El objetivo es llevar tus 4 fichas desde la cárcel hasta casa"),
            ("🎲", "Lanza dos dados en tu turno para mover tus fichas"),
            ("🔑", "Para sacar una ficha de la cárcel, debes sacar pares"),
            ("👣", "Mueve una ficha la suma total de los dados"),
            ("⚔️", "Si caes en casilla ocupada, envías la ficha rival a la cárcel"),
            ("🛡️", "Las casillas con ★ son seguras (nadie puede ser capturado)"),
            ("🔄", "Si sacas pares, tienes un turno adicional"),
            ("🏆", "Gana el primer jugador que lleve todas sus fichas a casa")
        ]
        
        y_offset = help_rect.y + 90
        for icon, text in instructions:
            # Icono
            icon_text = FONT_LARGE.render(icon, True, WHITE)
            self.screen.blit(icon_text, (help_rect.x + 40, y_offset))
            
            # Texto de instrucción
            instr_text = FONT_MEDIUM.render(text, True, WHITE)
            self.screen.blit(instr_text, (help_rect.x + 80, y_offset + 5))
            
            y_offset += 35
        
        # Sección de controles
        controls_title = FONT_MEDIUM.render("CONTROLES:", True, YELLOW)
        self.screen.blit(controls_title, (help_rect.x + 40, y_offset + 20))
        
        controls = [
            ("🖱️ Clic en TIRAR DADOS", "Lanzar los dados (o presiona R)"),
            ("🖱️ Clic en una ficha", "Seleccionar/Mover una ficha"),
            ("🔢 Teclas 1-4", "Seleccionar fichas por número"),
            ("🔤 Tecla H", "Mostrar/Ocultar esta ayuda")
        ]
        
        y_offset += 50
        for icon_text, control_text in controls:
            icon_surface = FONT_MEDIUM.render(icon_text, True, CYAN)
            self.screen.blit(icon_surface, (help_rect.x + 40, y_offset))
            
            text_surface = FONT_MEDIUM.render(control_text, True, WHITE)
            self.screen.blit(text_surface, (help_rect.x + 240, y_offset))
            
            y_offset += 30
        
        # Explicación del tablero
        board_title = FONT_MEDIUM.render("TABLERO:", True, YELLOW)
        self.screen.blit(board_title, (help_rect.x + 40, y_offset + 20))
        
        board_info = [
            "• Las casillas están numeradas como en un tablero tradicional",
            "• Cada jugador tiene un color y un camino específico",
            "• Las casillas con ★ son seguras contra capturas",
            "• Las fichas comienzan en las cárceles (esquinas)",
            "• El centro tiene los 4 colores en forma de cruz"
        ]
        
        y_offset += 50
        for info in board_info:
            info_text = FONT_SMALL.render(info, True, WHITE)
            self.screen.blit(info_text, (help_rect.x + 40, y_offset))
            y_offset += 25
        
        # Botón para cerrar
        close_rect = pygame.Rect(SCREEN_WIDTH // 2 - 70, help_rect.y + help_rect.height - 60, 140, 40)
        
        # Efecto de hover para el botón cerrar
        mouse_pos = pygame.mouse.get_pos()
        hover = close_rect.collidepoint(mouse_pos)
        
        button_color = (100, 60, 140) if not hover else (120, 80, 160)
        pygame.draw.rect(self.screen, button_color, close_rect, 0, 10)
        pygame.draw.rect(self.screen, (150, 120, 200), close_rect, 2, 10)
        
        close_text = FONT_MEDIUM.render("CERRAR (H)", True, WHITE)
        self.screen.blit(close_text, (SCREEN_WIDTH // 2 - close_text.get_width() // 2, close_rect.y + 10))
    
    def draw_star(self, x, y, size, color):
        """Dibuja una estrella para marcar casillas seguras"""
        points = []
        for i in range(5):
            # Puntos externos
            angle_ext = math.pi/2 + i * 2*math.pi/5
            points.append((x + size * math.cos(angle_ext), y - size * math.sin(angle_ext)))
            
            # Puntos internos
            angle_int = angle_ext + math.pi/5
            points.append((x + size/2 * math.cos(angle_int), y - size/2 * math.sin(angle_int)))
        
        pygame.draw.polygon(self.screen, color, points)
    
    def get_jail_position(self, color, index):
        """Obtiene la posición de una ficha en la cárcel"""
        board_offset_x = (SCREEN_WIDTH - BOARD_SIZE) // 2
        board_offset_y = (SCREEN_HEIGHT - BOARD_SIZE) // 2
        jail_size = BOARD_SIZE // 4
        
        # Calcular posiciones para cada color
        positions = {
            'rojo': [(board_offset_x + BOARD_SIZE - jail_size//2 - 25, board_offset_y + jail_size//2 - 25),
                     (board_offset_x + BOARD_SIZE - jail_size//2 + 25, board_offset_y + jail_size//2 - 25),
                     (board_offset_x + BOARD_SIZE - jail_size//2 - 25, board_offset_y + jail_size//2 + 25),
                     (board_offset_x + BOARD_SIZE - jail_size//2 + 25, board_offset_y + jail_size//2 + 25)],
            'verde': [(board_offset_x + jail_size//2 - 25, board_offset_y + jail_size//2 - 25),
                      (board_offset_x + jail_size//2 + 25, board_offset_y + jail_size//2 - 25),
                      (board_offset_x + jail_size//2 - 25, board_offset_y + jail_size//2 + 25),
                      (board_offset_x + jail_size//2 + 25, board_offset_y + jail_size//2 + 25)],
            'amarillo': [(board_offset_x + jail_size//2 - 25, board_offset_y + BOARD_SIZE - jail_size//2 - 25),
                         (board_offset_x + jail_size//2 + 25, board_offset_y + BOARD_SIZE - jail_size//2 - 25),
                         (board_offset_x + jail_size//2 - 25, board_offset_y + BOARD_SIZE - jail_size//2 + 25),
                         (board_offset_x + jail_size//2 + 25, board_offset_y + BOARD_SIZE - jail_size//2 + 25)],
            'azul': [(board_offset_x + BOARD_SIZE - jail_size//2 - 25, board_offset_y + BOARD_SIZE - jail_size//2 - 25),
                    (board_offset_x + BOARD_SIZE - jail_size//2 + 25, board_offset_y + BOARD_SIZE - jail_size//2 - 25),
                    (board_offset_x + BOARD_SIZE - jail_size//2 - 25, board_offset_y + BOARD_SIZE - jail_size//2 + 25),
                    (board_offset_x + BOARD_SIZE - jail_size//2 + 25, board_offset_y + BOARD_SIZE - jail_size//2 + 25)]
        }
        
        if color in positions and index < len(positions[color]):
            return positions[color][index]
        
        # Posición por defecto si algo falla
        return (board_offset_x + BOARD_SIZE//2, board_offset_y + BOARD_SIZE//2)
    
    def translate_server_position_to_board(self, server_position, board_offset_x, board_offset_y):
        """Traduce una posición del servidor a coordenadas en nuestro tablero"""
        # Tamaño de las casillas y áreas
        jail_size = BOARD_SIZE // 4
        square_width = jail_size // 2
        square_height = square_width // 2
        
        # Límites para cada lado del tablero (posiciones del servidor)
        # Estos valores deberían ajustarse según la numeración real del servidor
        top_min, top_max = 0, 17
        right_min, right_max = 18, 35
        bottom_min, bottom_max = 36, 53
        left_min, left_max = 54, 71
        
        # Mapear la posición del servidor a nuestro tablero
        x, y = 0, 0
        
        try:
            # Parte superior (entre verde y rojo)
            if top_min <= server_position <= top_max:
                rel_pos = server_position - top_min
                x = board_offset_x + jail_size + (rel_pos + 1) * square_width + square_width // 2
                y = board_offset_y + jail_size // 4
            
            # Parte derecha (entre rojo y azul)
            elif right_min <= server_position <= right_max:
                rel_pos = server_position - right_min
                x = board_offset_x + BOARD_SIZE - jail_size // 4
                y = board_offset_y + jail_size + rel_pos * square_height + square_height // 2
            
            # Parte inferior (entre azul y amarillo)
            elif bottom_min <= server_position <= bottom_max:
                rel_pos = server_position - bottom_min
                x = board_offset_x + BOARD_SIZE - jail_size - rel_pos * square_width - square_width // 2
                y = board_offset_y + BOARD_SIZE - jail_size // 4
            
            # Parte izquierda (entre amarillo y verde)
            elif left_min <= server_position <= left_max:
                rel_pos = server_position - left_min
                x = board_offset_x + jail_size // 4
                y = board_offset_y + BOARD_SIZE - jail_size - rel_pos * square_height - square_height // 2
            
            # Caminos hacia el centro (simplificados, ajustar según servidor)
            elif 72 <= server_position <= 77:  # Camino verde
                rel_pos = server_position - 72
                x = board_offset_x + jail_size + square_width // 2
                y = board_offset_y + jail_size // 2 + rel_pos * square_height + square_height // 2
            
            elif 78 <= server_position <= 83:  # Camino rojo
                rel_pos = server_position - 78
                x = board_offset_x + BOARD_SIZE - jail_size - rel_pos * square_width - square_width // 2
                y = board_offset_y + jail_size + square_height // 2
            
            elif 84 <= server_position <= 89:  # Camino amarillo
                rel_pos = server_position - 84
                x = board_offset_x + jail_size + rel_pos * square_width + square_width // 2
                y = board_offset_y + BOARD_SIZE - jail_size - square_height // 2
            
            elif 90 <= server_position <= 95:  # Camino azul
                rel_pos = server_position - 90
                x = board_offset_x + BOARD_SIZE - jail_size - square_width // 2
                y = board_offset_y + BOARD_SIZE - jail_size - rel_pos * square_height - square_height // 2
            
            # Si no se encuentra en ningún rango conocido, mostrar en el centro
            else:
                x = board_offset_x + BOARD_SIZE // 2
                y = board_offset_y + BOARD_SIZE // 2
                print(f"Posición desconocida: {server_position}")
                
        except Exception as e:
            print(f"Error mapeando posición {server_position}: {e}")
            # Posición por defecto en caso de error
            x = board_offset_x + BOARD_SIZE // 2
            y = board_offset_y + BOARD_SIZE // 2
            
        return (x, y)
    
    def lighten_color(self, color, factor=1.5):
        """Aclara un color multiplicando sus componentes por un factor"""
        r, g, b = color
        return (min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor)))
        
    def darken_color(self, color, factor=0.5):
        """Oscurece un color multiplicando sus componentes por un factor"""
        r, g, b = color
        return (int(r * factor), int(g * factor), int(b * factor))
    
    def update_animation(self):
        """Actualiza las animaciones y efectos visuales"""
        current_time = pygame.time.get_ticks()
        self.animation_timer = current_time
        self.animation_offset = (current_time // 30) % 5
        
        # Actualizar efectos de partículas u otros elementos animados
        if self.current_screen == "game" and self.my_turn:
            # Efectos visuales adicionales cuando es el turno del jugador
            if random.random() < 0.02:  # Ocasionalmente añadir un efecto de destello
                self.add_highlight_effect()
    
    def add_highlight_effect(self):
        """Añade un efecto de destello visual en el turno del jugador"""
        # Esta función es un placeholder para futuras mejoras visuales
        pass
    
    def disconnect(self):
        """Desconecta del servidor"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        print("Desconectado del servidor")
    
    def run(self):
        """Ejecuta el bucle principal del juego"""
        clock = pygame.time.Clock()
        fps_display = False  # Para mostrar/ocultar FPS (útil para debugging)
        
        while self.running:
            # Tiempo al inicio del frame
            frame_start = time.time()
            
            # Manejar eventos
            if not self.handle_events():
                break
                
            # Actualizar animaciones
            self.update_animation()
            
            # Dibujar pantalla actual
            if self.current_screen == "connect":
                self.draw_connect_screen()
            elif self.current_screen == "lobby":
                self.draw_lobby_screen()
            elif self.current_screen == "game":
                self.draw_game_screen()
            
            # Mostrar FPS para debugging (opcional)
            if fps_display:
                fps = clock.get_fps()
                fps_text = FONT_SMALL.render(f"FPS: {fps:.1f}", True, WHITE)
                self.screen.blit(fps_text, (10, 10))
            
            # Actualizar pantalla
            pygame.display.flip()
            
            # Controlar FPS
            clock.tick(60)
            
            # Calcular tiempo real del frame
            frame_time = time.time() - frame_start
            
            # Mostrar mensajes de advertencia si el rendimiento es bajo
            if frame_time > 0.05:  # Más de 50 ms por frame (menos de 20 FPS)
                print(f"¡Advertencia: Frame lento! {frame_time*1000:.1f} ms")
        
        # Limpiar recursos
        self.disconnect()
        pygame.quit()

def main():
    """Función principal"""
    print("🎮 Cliente Gráfico de Parqués - Sistemas Distribuidos")
    print("="*60)
    print("Versión Tablero Clásico")
    print("Diseñado para verse como un tablero tradicional de Parqués/Parchís")
    print("="*60)
    
    # Configuración del servidor
    server_host = input("Host del servidor (Enter para localhost): ").strip()
    if not server_host:
        server_host = 'localhost'
    
    try:
        server_port = input("Puerto del servidor (Enter para 12345): ").strip()
        server_port = int(server_port) if server_port else 12345
    except ValueError:
        print("⚠️ Puerto inválido, usando 12345")
        server_port = 12345
    
    # Mostrar mensaje de inicio
    print("\nIniciando juego con interfaz gráfica de tablero clásico...")
    print("✨ Disfruta del auténtico estilo visual del Parqués tradicional ✨")
    
    # Iniciar cliente
    client = ParquesClientGUI(server_host, server_port)
    client.run()

if __name__ == "__main__":
    main()