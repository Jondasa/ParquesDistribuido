#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor de Parqués Distribuido Mejorado
Sistemas Distribuidos - Proyecto Final
"""

import socket
import threading
import json
import random
import time
from datetime import datetime

class ParquesGame:
    def __init__(self):
        self.players = {}  # {player_id: {name, color, pieces, position}}
        self.board = self.init_board()
        self.current_turn = None
        self.game_started = False
        self.turn_order = []
        self.dice_attempts = 0
        self.max_players = 4
        self.colors = ['rojo', 'azul', 'amarillo', 'verde']
        self.used_colors = set()
        self.last_activity = time.time()
        self.game_log = []
        
    def init_board(self):
        """Inicializa el tablero con 96 casillas"""
        board = {}
        # Casillas normales (0-95)
        for i in range(96):
            board[i] = {'type': 'normal', 'player': None}
        
        # Casillas de seguro (cada 12 casillas + algunas especiales)
        safe_squares = [5, 12, 17, 22, 29, 34, 39, 46, 51, 56, 63, 68, 73, 80, 85, 90]
        for square in safe_squares:
            if square < 96:
                board[square]['type'] = 'safe'
        
        # Casillas de salida para cada color
        board[5]['type'] = 'exit'    # Rojo
        board[22]['type'] = 'exit'   # Verde  
        board[51]['type'] = 'exit'   # Azul
        board[68]['type'] = 'exit'   # Amarillo
        
        return board
    
    def add_player(self, player_id, name):
        """Añade un jugador al juego"""
        if len(self.players) >= self.max_players or self.game_started:
            return False, "Juego lleno o ya iniciado"
            
        if len(self.used_colors) >= len(self.colors):
            return False, "No hay colores disponibles"
            
        # Asignar color disponible
        available_colors = [c for c in self.colors if c not in self.used_colors]
        color = available_colors[0]
        self.used_colors.add(color)
        
        self.players[player_id] = {
            'name': name,
            'color': color,
            'pieces': [{'position': 'jail', 'id': i} for i in range(4)],
            'in_jail': 4,
            'finished_pieces': 0
        }
        
        self.add_log(f"Jugador {name} se unió con color {color}")
        return True, f"Jugador {name} añadido con color {color}"
    
    def remove_player(self, player_id):
        """Elimina a un jugador del juego"""
        if player_id in self.players:
            player_name = self.players[player_id]['name']
            player_color = self.players[player_id]['color']
            
            del self.players[player_id]
            self.used_colors.discard(player_color)
            
            # Actualizar orden de turnos si es necesario
            if player_id in self.turn_order:
                self.turn_order.remove(player_id)
            
            # Cambiar turno si era el turno del jugador eliminado
            if self.current_turn == player_id and self.turn_order:
                self.current_turn = self.turn_order[0]
            
            self.add_log(f"Jugador {player_name} se desconectó")
            return True
        return False
    
    def can_start_game(self):
        """Verifica si se puede iniciar el juego (mínimo 2 jugadores)"""
        return len(self.players) >= 2
    
    def start_game(self):
        """Inicia el juego determinando el orden de turnos"""
        if not self.can_start_game():
            return False, "Se necesitan al menos 2 jugadores"
            
        self.game_started = True
        
        # Determinar orden inicial con dados
        initial_rolls = {}
        roll_results = []
        for player_id in self.players:
            dice1, dice2 = random.randint(1, 6), random.randint(1, 6)
            total = dice1 + dice2
            initial_rolls[player_id] = total
            roll_results.append(f"{self.players[player_id]['name']}: {dice1}+{dice2}={total}")
        
        # Ordenar por mayor puntuación
        sorted_players = sorted(initial_rolls.items(), key=lambda x: x[1], reverse=True)
        self.turn_order = [player_id for player_id, _ in sorted_players]
        self.current_turn = self.turn_order[0]
        self.dice_attempts = 0
        
        # Registrar en el log
        self.add_log(f"Juego iniciado. Tiradas iniciales: {', '.join(roll_results)}")
        self.add_log(f"Primer turno: {self.players[self.current_turn]['name']}")
        
        return True, f"Juego iniciado. Primer turno: {self.players[self.current_turn]['name']}"
    
    def roll_dice(self):
        """Lanza los dados"""
        return random.randint(1, 6), random.randint(1, 6)
    
    def is_pair(self, dice1, dice2):
        """Verifica si los dados forman una pareja"""
        return dice1 == dice2
    
    def can_move_from_jail(self, dice1, dice2):
        """Verifica si se puede sacar una ficha de la cárcel"""
        return self.is_pair(dice1, dice2)
    
    def move_piece_from_jail(self, player_id):
        """Mueve una ficha de la cárcel a la casilla de salida"""
        player = self.players[player_id]
        
        # Buscar primera ficha en cárcel
        for piece in player['pieces']:
            if piece['position'] == 'jail':
                # Determinar casilla de salida según color
                exit_positions = {'rojo': 5, 'verde': 22, 'azul': 51, 'amarillo': 68}
                exit_pos = exit_positions[player['color']]
                
                piece['position'] = exit_pos
                player['in_jail'] -= 1
                
                self.add_log(f"{player['name']} sacó una ficha a la casilla {exit_pos}")
                return True, f"Ficha movida a casilla {exit_pos}"
        
        return False, "No hay fichas en cárcel"
    
    def move_piece(self, player_id, piece_id, steps):
        """Mueve una ficha en el tablero"""
        player = self.players[player_id]
        
        if piece_id >= len(player['pieces']):
            return False, "Ficha inválida"
            
        piece = player['pieces'][piece_id]
        
        if piece['position'] == 'jail':
            return False, "La ficha está en la cárcel"
            
        if piece['position'] == 'home':
            return False, "La ficha ya llegó a casa"
        
        current_pos = piece['position']
        new_pos = (current_pos + steps) % 96
        
        # Verificar si la nueva posición está ocupada por otro jugador
        target_occupied = False
        target_player = None
        target_piece = None
        
        for other_id, other_player in self.players.items():
            if other_id != player_id:
                for i, other_piece in enumerate(other_player['pieces']):
                    if other_piece['position'] == new_pos:
                        target_occupied = True
                        target_player = other_id
                        target_piece = i
                        # Verificar si está en casilla segura
                        if self.board[new_pos]['type'] in ['safe', 'exit']:
                            target_occupied = False
                        break
        
        # Si hay captura, enviar ficha enemiga a cárcel
        if target_occupied:
            self.send_to_jail(target_player, new_pos)
            self.add_log(f"{player['name']} capturó una ficha de {self.players[target_player]['name']}")
        
        # Mover la ficha
        piece['position'] = new_pos
        self.add_log(f"{player['name']} movió ficha {piece_id} a la posición {new_pos}")
        
        # Verificar si llegó a casa (simplificado: casilla 95+)
        if new_pos >= 92:  # Últimas casillas antes de casa
            piece['position'] = 'home'
            player['finished_pieces'] += 1
            self.add_log(f"{player['name']} llevó una ficha a casa. Tiene {player['finished_pieces']} fichas en casa")
        
        return True, f"Ficha movida a posición {new_pos}"
    
    def send_to_jail(self, player_id, position):
        """Envía una ficha específica a la cárcel"""
        player = self.players[player_id]
        for i, piece in enumerate(player['pieces']):
            if piece['position'] == position:
                piece['position'] = 'jail'
                player['in_jail'] += 1
                self.add_log(f"Ficha {i} de {player['name']} enviada a la cárcel")
                break
    
    def next_turn(self):
        """Pasa al siguiente turno"""
        if not self.turn_order:
            return
            
        current_index = self.turn_order.index(self.current_turn)
        next_index = (current_index + 1) % len(self.turn_order)
        self.current_turn = self.turn_order[next_index]
        self.dice_attempts = 0
        
        self.add_log(f"Turno de {self.players[self.current_turn]['name']}")
        self.last_activity = time.time()
    
    def check_winner(self):
        """Verifica si hay un ganador"""
        for player_id, player in self.players.items():
            if player['finished_pieces'] >= 4:
                self.add_log(f"¡{player['name']} ha ganado el juego!")
                return player_id, player['name']
        return None, None
    
    def add_log(self, message):
        """Añade un mensaje al log del juego"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.game_log.append(log_entry)
        
        # Mantener solo los últimos 100 mensajes
        if len(self.game_log) > 100:
            self.game_log.pop(0)
        
        print(log_entry)
    
    def get_game_state(self):
        """Obtiene el estado actual del juego"""
        return {
            'players': self.players,
            'current_turn': self.current_turn,
            'game_started': self.game_started,
            'turn_order': self.turn_order,
            'dice_attempts': self.dice_attempts,
            'board': self.board,
            'game_log': self.game_log[-10:]  # Últimos 10 mensajes
        }

class ParquesServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.game = ParquesGame()
        self.lock = threading.Lock()
        self.running = True
        self.last_broadcast = None  # Almacena el último mensaje de broadcast
    
    def start_server(self):
        """Inicia el servidor"""
        try:
            # Intentar varias veces en caso de error "Address already in use"
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    self.socket.bind((self.host, self.port))
                    break  # Si tiene éxito, salir del bucle
                except OSError as e:
                    if e.errno == 98 and attempt < max_attempts - 1:  # Address already in use
                        print(f"Puerto {self.port} ocupado, esperando 2 segundos e intentando de nuevo...")
                        self.socket.close()
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        time.sleep(2)
                    else:
                        raise  # Re-lanzar la excepción si es otro error o último intento
            
            self.socket.listen(4)
            print(f"Servidor Parqués iniciado en {self.host}:{self.port}")
            print("Esperando jugadores...")
            
            # Iniciar thread para verificar inactividad
            inactive_checker = threading.Thread(target=self.check_inactive_players)
            inactive_checker.daemon = True
            inactive_checker.start()
            
            while self.running:
                try:
                    self.socket.settimeout(1.0)  # Timeout para poder detener el servidor
                    client_socket, address = self.socket.accept()
                    print(f"Cliente conectado desde {address}")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error aceptando conexión: {e}")
                
        except KeyboardInterrupt:
            print("\nDeteniendo servidor...")
        except Exception as e:
            print(f"Error en el servidor: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Detiene el servidor"""
        self.running = False
        self.socket.close()
        print("Servidor detenido")
    
    def check_inactive_players(self):
        """Verifica y desconecta jugadores inactivos"""
        while self.running:
            try:
                time.sleep(30)  # Verificar cada 30 segundos
                
                with self.lock:
                    current_time = time.time()
                    
                    # Si el juego está iniciado y no ha habido actividad por 5 minutos
                    if self.game.game_started and (current_time - self.game.last_activity) > 300:
                        # Si es el turno de un jugador por más de 2 minutos, pasar al siguiente
                        if self.game.current_turn:
                            self.game.add_log(f"Tiempo de inactividad excedido, pasando turno")
                            self.game.next_turn()
            except Exception as e:
                print(f"Error verificando inactividad: {e}")
    
    def handle_client(self, client_socket, address):
        """Maneja las conexiones de los clientes"""
        player_id = f"{address[0]}:{address[1]}"
        
        try:
            while self.running:
                try:
                    client_socket.settimeout(1.0)  # Timeout para detectar desconexiones
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    message = json.loads(data)
                    response = self.process_message(player_id, message)
                    
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    error_response = {'status': 'error', 'message': 'Mensaje inválido'}
                    client_socket.send(json.dumps(error_response).encode('utf-8'))
                    
        except Exception as e:
            print(f"Error manejando cliente {address}: {e}")
        finally:
            # Limpiar al desconectar
            with self.lock:
                if player_id in self.clients:
                    del self.clients[player_id]
                    
                # Eliminar jugador del juego si estaba conectado
                if player_id in self.game.players:
                    self.game.remove_player(player_id)
                    
            client_socket.close()
            print(f"Cliente {address} desconectado")
    
    def process_message(self, player_id, message):
        """Procesa los mensajes de los clientes"""
        with self.lock:
            action = message.get('action')
            
            if action == 'join':
                return self.handle_join(player_id, message.get('name', 'Jugador'))
            
            elif action == 'start_game':
                return self.handle_start_game()
            
            elif action == 'roll_dice':
                return self.handle_roll_dice(player_id)
            
            elif action == 'move_piece':
                return self.handle_move_piece(player_id, message)
            
            elif action == 'get_state':
                return self.handle_get_state()
            
            elif action == 'chat':
                return self.handle_chat(player_id, message.get('message', ''))
            
            else:
                return {'status': 'error', 'message': 'Acción no reconocida'}
    
    def handle_join(self, player_id, name):
        """Maneja la unión de un jugador"""
        success, message = self.game.add_player(player_id, name)
        
        if success:
            self.clients[player_id] = {'name': name}
            
            # Verificar si se puede iniciar el juego
            can_start = self.game.can_start_game()
            
            response = {
                'status': 'success',
                'message': message,
                'player_id': player_id,
                'color': self.game.players[player_id]['color'],
                'players_count': len(self.game.players),
                'can_start': can_start
            }
            
            # Si hay 2 o más jugadores, actualizar a todos los clientes
            if can_start:
                self.broadcast_game_state()
        else:
            response = {'status': 'error', 'message': message}
        
        return response
        
    def broadcast_game_state(self):
        """Envía el estado actual del juego a todos los clientes conectados"""
        # Este método se llamará cuando ocurra un cambio importante, como un nuevo jugador
        game_state = self.game.get_game_state()
        
        # Agregar bandera de can_start para todos los clientes
        can_start = self.game.can_start_game()
        
        update_message = {
            'status': 'update',
            'game_state': game_state,
            'can_start': can_start,
            'players_count': len(self.game.players)
        }
        
        # No enviar a través de sockets directamente, ya que no tenemos referencia a ellos aquí
        # En su lugar, almacenar el mensaje para que los clientes lo reciban en su próxima solicitud
        self.last_broadcast = update_message
    
    def handle_start_game(self):
        """Maneja el inicio del juego"""
        success, message = self.game.start_game()
        
        if success:
            return {
                'status': 'success',
                'message': message,
                'game_state': self.game.get_game_state()
            }
        else:
            return {'status': 'error', 'message': message}
    
    def handle_roll_dice(self, player_id):
        """Maneja el lanzamiento de dados"""
        if not self.game.game_started:
            return {'status': 'error', 'message': 'El juego no ha comenzado'}
        
        if self.game.current_turn != player_id:
            return {'status': 'error', 'message': 'No es tu turno'}
        
        dice1, dice2 = self.game.roll_dice()
        is_pair = self.game.is_pair(dice1, dice2)
        
        # Actualizar tiempo de actividad
        self.game.last_activity = time.time()
        
        # Registrar en el log
        player_name = self.game.players[player_id]['name']
        self.game.add_log(f"{player_name} tiró {dice1} y {dice2} (Total: {dice1 + dice2})")
        
        response = {
            'status': 'success',
            'dice1': dice1,
            'dice2': dice2,
            'is_pair': is_pair,
            'total': dice1 + dice2
        }
        
        # Si tiene fichas en cárcel y saca pareja, puede sacar ficha
        player = self.game.players[player_id]
        if player['in_jail'] > 0 and is_pair:
            success, msg = self.game.move_piece_from_jail(player_id)
            response['jail_move'] = {'success': success, 'message': msg}
            
            # Si saca pareja, puede tirar de nuevo
            response['extra_turn'] = True
        else:
            self.game.dice_attempts += 1
            
            # Si no puede sacar de cárcel y no tiene fichas fuera, pierde turno
            if player['in_jail'] == 4:
                if self.game.dice_attempts >= 3:
                    self.game.next_turn()
                    response['turn_ended'] = True
                    response['next_player'] = self.game.current_turn
            else:
                # Puede mover fichas normales
                response['can_move'] = True
        
        return response
    
    def handle_move_piece(self, player_id, message):
        """Maneja el movimiento de fichas"""
        if self.game.current_turn != player_id:
            return {'status': 'error', 'message': 'No es tu turno'}
        
        piece_id = message.get('piece_id', 0)
        steps = message.get('steps', 0)
        
        # Actualizar tiempo de actividad
        self.game.last_activity = time.time()
        
        success, msg = self.game.move_piece(player_id, piece_id, steps)
        
        if success:
            # Verificar ganador
            winner_id, winner_name = self.game.check_winner()
            
            response = {
                'status': 'success',
                'message': msg,
                'game_state': self.game.get_game_state()
            }
            
            if winner_id:
                response['winner'] = {'id': winner_id, 'name': winner_name}
                response['game_ended'] = True
            else:
                # Pasar turno
                self.game.next_turn()
                response['next_player'] = self.game.current_turn
            
            return response
        else:
            return {'status': 'error', 'message': msg}
    
    def handle_get_state(self):
        """Devuelve el estado actual del juego"""
        # Si hay un mensaje de broadcast pendiente, incluirlo en la respuesta
        if self.last_broadcast:
            response = self.last_broadcast
            self.last_broadcast = None  # Limpiar después de enviar
            return response
        
        # De lo contrario, enviar el estado normal
        return {
            'status': 'success',
            'game_state': self.game.get_game_state(),
            'can_start': self.game.can_start_game(),
            'players_count': len(self.game.players)
        }
    
    def handle_chat(self, player_id, message):
        """Maneja mensajes de chat entre jugadores"""
        if not message.strip() or player_id not in self.game.players:
            return {'status': 'error', 'message': 'Mensaje inválido'}
        
        player_name = self.game.players[player_id]['name']
        self.game.add_log(f"Chat - {player_name}: {message}")
        
        return {
            'status': 'success',
            'message': 'Mensaje enviado',
            'game_state': self.game.get_game_state()
        }

def main():
    print("🎲 Servidor Parqués Mejorado - Sistemas Distribuidos")
    print("="*60)
    
    # Configuración del servidor
    host = input("Host para escuchar (Enter para todas las interfaces): ").strip()
    if not host:
        host = '0.0.0.0'
    
    try:
        port = input("Puerto para escuchar (Enter para 12345): ").strip()
        port = int(port) if port else 12345
    except ValueError:
        port = 12345
    
    server = ParquesServer(host, port)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()