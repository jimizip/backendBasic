#!/usr/bin/env python3

import json
import struct
import message_pb2 as pb

class NetworkUtils:

    # 클라이언트로부터 메세지 받기
    @staticmethod
    def receive_message(client_socket, format):
        try:
            if format == 'json':
                # 메세지 길이 받기
                length_bytes = client_socket.recv(2)
                if not length_bytes:
                    return None
                length = int.from_bytes(length_bytes, byteorder='big')
                
                # 메세지 본문 받기
                message_bytes = b''
                while len(message_bytes) < length:
                    chunk = client_socket.recv(length - len(message_bytes))
                    if not chunk:
                        return None  # 연결이 끊어진 경우
                    message_bytes += chunk
                
                try:
                    message = json.loads(message_bytes.decode('utf-8'))
                    if 'type' not in message:
                        print(f"Invalid JSON message format: {message}")
                        return None
                    return message
                except json.JSONDecodeError as e:
                    print(f"JSON decoding error: {e}")
                    return None
            else:  # Protobuf
                # Type 메시지 수신
                type_length = struct.unpack('>H', client_socket.recv(2))[0]
                type_bytes = client_socket.recv(type_length)
                type_message = pb.Type()
                type_message.ParseFromString(type_bytes)

                # 실제 메시지 수신
                message_length = struct.unpack('>H', client_socket.recv(2))[0]
                message_bytes = client_socket.recv(message_length)
                actual_message = NetworkUtils.create_protobuf_message(type_message.type)
                if actual_message:
                    actual_message.ParseFromString(message_bytes)
                    return {'type': type_message.type, 'message': actual_message}
                else:
                    print(f"Unknown message type: {type_message.type}")
                    return None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None

    @staticmethod
    def send_message(client_socket, message, format):
        try:
            if format == 'json':
                if isinstance(message, dict) and 'type' in message:
                    serialized = json.dumps(message).encode('utf-8')
                else:
                    serialized = json.dumps({'type': message.__class__.__name__, 'data': message}).encode('utf-8')
                length = len(serialized)
                client_socket.sendall(length.to_bytes(2, byteorder='big') + serialized)
            else:
                serialized = NetworkUtils.serialize_protobuf_message(message)
                client_socket.sendall(serialized)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
        
    # [시스템 메세지]
    @staticmethod
    def send_system_message(client_socket, text, format):
        if format == 'json':
            message = {
                'type': 'SCSystemMessage',
                'text': text
            }
        else:
            message = pb.SCSystemMessage()
            message.text = text
        NetworkUtils.send_message(client_socket, message, format)

    # 브로드캐스트
    @staticmethod
    def broadcast_to_room(room, clients, text, exclude, format):
        for client_socket in room['members']:
            if client_socket != exclude:
                if format == 'json':
                    message = {
                        'type': 'SCChat',
                        'member': clients[client_socket]['name'],
                        'text': text
                    }
                else:
                    message = pb.SCChat()
                    message.member = clients[client_socket]['name']
                    message.text = text
                NetworkUtils.send_message(client_socket, message, format)
        
    # 타입에서 객체로
    @staticmethod
    def create_protobuf_message(message_type):
        type_to_message = {
            pb.Type.MessageType.CS_NAME: pb.CSName(),
            pb.Type.MessageType.CS_ROOMS: pb.CSRooms(),
            pb.Type.MessageType.CS_CREATE_ROOM: pb.CSCreateRoom(),
            pb.Type.MessageType.CS_JOIN_ROOM: pb.CSJoinRoom(),
            pb.Type.MessageType.CS_LEAVE_ROOM: pb.CSLeaveRoom(),
            pb.Type.MessageType.CS_CHAT: pb.CSChat(),
            pb.Type.MessageType.CS_SHUTDOWN: pb.CSShutdown()
        }
        message = type_to_message.get(message_type)

        if message is None:
            print(f"Unknown message type: {message_type}")
        return message

    # 객체에서 타입으로
    @staticmethod
    def get_protobuf_message_type(message):
        type_mapping = {
            pb.SCSystemMessage: pb.Type.MessageType.SC_SYSTEM_MESSAGE,
            pb.SCRoomsResult: pb.Type.MessageType.SC_ROOMS_RESULT,
            pb.SCChat: pb.Type.MessageType.SC_CHAT,
        }
        message_type = type_mapping.get(type(message))
        if message_type is None:
            raise ValueError(f"Unknown message type: {type(message)}")
        return message_type

    @staticmethod
    def serialize_protobuf_message(message):
        if isinstance(message, pb.Type):
            return message.SerializeToString()
        else:
            type_message = pb.Type()
            type_message.type = NetworkUtils.get_protobuf_message_type(message)
            type_bytes = type_message.SerializeToString()
            message_bytes = message.SerializeToString()
            return (struct.pack('>H', len(type_bytes)) + type_bytes +
                    struct.pack('>H', len(message_bytes)) + message_bytes)
        