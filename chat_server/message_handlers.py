#!/usr/bin/env python3
import message_pb2 as pb
from utils import NetworkUtils

class MessageHandlers:

    # 서버 초기화
    def __init__(self, server):
        self.server = server
        self.send_message = lambda client_socket, message: NetworkUtils.send_message(client_socket, message, server.config.format)
        self.send_system_message = lambda client_socket, text: NetworkUtils.send_system_message(client_socket, text, server.config.format)
        self.broadcast_to_room = lambda room, text, exclude: NetworkUtils.broadcast_to_room(room, server.clients, text, exclude, server.config.format)
    
    # /name
    def handle_name(self, client_socket, message):
        with self.server.config.lock:
            old_name = self.server.clients[client_socket]['name']
            
            if self.server.config.format == 'json':
                new_name = message['name']
            else:  # protobuf
                new_name = message.name
            
            self.server.clients[client_socket]['name'] = new_name
            
            system_message = f"이름이 {new_name}으로 변경되었습니다."
            self.send_system_message(client_socket, system_message)
            
            # 현재 방에 있다면 다른 클라이언트에게 이름 변경 알림
            if self.server.clients[client_socket]['room']:
                room_id = self.server.clients[client_socket]['room']
                room_message = f"{old_name}님의 이름이 {new_name}으로 변경되었습니다."
                self.broadcast_to_room(self.server.rooms[room_id], room_message, exclude=client_socket)
            
            # 결과 메시지 전송
            if self.server.config.format == 'json':
                result_message = {
                    'type': 'SCSystemMessage',
                    'text': '이름이 성공적으로 변경되었습니다.'
                }
            else:  # protobuf
                result_message = pb.SCSystemMessage()
                result_message.text = '이름이 성공적으로 변경되었습니다.'
            self.send_message(client_socket, result_message)

    # /rooms
    def handle_rooms(self, client_socket):
        with self.server.config.lock:
            rooms_info = []
            for room_id, room in self.server.rooms.items():
                rooms_info.append({
                    'roomId': room_id,
                    'title': room['title'],
                    'members': [self.server.clients[client]['name'] for client in room['members']]
                })
            
            # format에 맞게 응답
            if self.server.config.format == 'json':
                message = {
                    'type': 'SCRoomsResult',
                    'rooms': rooms_info
                }
            else:
                message = pb.SCRoomsResult()
                for room_info in rooms_info:
                    room = message.rooms.add()
                    room.roomId = room_info['roomId']
                    room.title = room_info['title']
                    room.members.extend(room_info['members'])
            
            self.send_message(client_socket, message)

    # /create
    def handle_create_room(self, client_socket, message):
        with self.server.config.lock:
            if self.server.clients[client_socket]['room']:
                error_message = "대화 방에 있을 때는 방을 개설할 수 없습니다."
                self.send_system_message(client_socket, error_message)

                return
            
            title = message['title'] if self.server.config.format == 'json' else message.title
            room_id = self.server.next_room_id
            self.server.next_room_id += 1
            
            self.server.rooms[room_id] = {
                'title': title,
                'members': set([client_socket])
            }
            self.server.clients[client_socket]['room'] = room_id
            
            system_message = f"방제[{title}] 방에 입장했습니다."
            self.send_system_message(client_socket, system_message)
            print(f"방[{room_id}]: 생성. 방제 {title}")

            if self.server.config.format == 'json':
                result_message = {'type': 'SCSystemMessage', 'text': '방이 성공적으로 생성되었습니다.'}
            else:
                result_message = pb.SCSystemMessage()
                result_message.text = '방이 성공적으로 생성되었습니다.'
            self.send_message(client_socket, result_message)

    # /join
    def handle_join_room(self, client_socket, message):
        with self.server.config.lock:
            # 이미 방에 있는 경우
            if self.server.clients[client_socket]['room']:
                error_message = "대화 방에 있을 때는 다른 방에 들어갈 수 없습니다."
                self.send_system_message(client_socket, error_message)
                
                return
            
            room_id = message['roomId'] if self.server.config.format == 'json' else message.roomId
            if room_id not in self.server.rooms:
                error_message = "대화방이 존재하지 않습니다."
                self.send_system_message(client_socket, error_message)
                
                return
            
            # 클라이언트를 방에 추가
            self.server.rooms[room_id]['members'].add(client_socket)
            self.server.clients[client_socket]['room'] = room_id
            
            # 입장 메세지
            system_message = f"방제[{self.server.rooms[room_id]['title']}] 방에 입장했습니다."
            self.send_system_message(client_socket, system_message)
            
            # 다른 클라이언트들에게 입장 메세지
            join_message = f"[{self.server.clients[client_socket]['name']}] 님이 입장했습니다."
            self.broadcast_to_room(self.server.rooms[room_id], join_message, exclude=client_socket)

            if self.server.config.format == 'json':
                result_message = {'type': 'SCSystemMessage', 'text': '방에 성공적으로 입장했습니다.'}
            else:
                result_message = pb.SCSystemMessage()
                result_message.text = '방에 성공적으로 입장했습니다.'
            self.send_message(client_socket, result_message)

    # /leave
    def handle_leave_room(self, client_socket):
        with self.server.config.lock:
            room_id = self.server.clients[client_socket]['room']
            # 현재 방에 들어가있지 않은 경우
            if not room_id:
                error_message = "현재 대화방에 들어가 있지 않습니다."
                self.send_system_message(client_socket, error_message)
                
                return
            
            room_title = self.server.rooms[room_id]['title']
            # 클라이언트를 방에서 제거
            self.server.rooms[room_id]['members'].remove(client_socket)
            self.server.clients[client_socket]['room'] = None
            
            # 방의 다른 클라이언트들에게 퇴장 메세지
            leave_message = f"[{self.server.clients[client_socket]['name']}] 님이 퇴장했습니다."
            self.broadcast_to_room(self.server.rooms[room_id], leave_message, exclude=client_socket)
            
            system_message = f"방제[{room_title}] 대화 방에서 퇴장했습니다."
            self.send_system_message(client_socket, system_message)
            
            # 방에 아무도 없으면 방 삭제
            if not self.server.rooms[room_id]['members']:
                del self.server.rooms[room_id]
                print(f"방[{room_id}]: 명시적 /leave 명령으로 인한 방폭")

            if self.server.config.format == 'json':
                result_message = {'type': 'SCSystemMessage', 'text': '방에서 성공적으로 퇴장했습니다.'}
            else:
                result_message = pb.SCSystemMessage()
                result_message.text = '방에서 성공적으로 퇴장했습니다.'
            self.send_message(client_socket, result_message)
 
    # 채팅 기능
    def handle_chat(self, client_socket, message):
        with self.server.config.lock:
            room_id = self.server.clients[client_socket]['room']
            # 방에 들어가있지 않은 경우
            if not room_id:
                self.send_system_message(client_socket, "현재 대화방에 들어가 있지 않습니다.")
                return
            
            text = message['text'] if self.server.config.format == 'json' else message.text
            chat_message = f"[{self.server.clients[client_socket]['name']}] {text}"
            # 방의 다른 클라이언트들에게 채팅 메세지 브로드 캐스트
            self.broadcast_to_room(self.server.rooms[room_id], chat_message, exclude=client_socket)