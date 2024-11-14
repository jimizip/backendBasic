#!/usr/bin/env python3

# 필요한 모듈
import socket
import select
import threading
import queue
import message_pb2 as pb
from collections import defaultdict
from message_handlers import MessageHandlers
from config import Config
from utils import NetworkUtils
class ChatServer:
    # 서버 초기화
    def __init__(self, host, port, num_workers, format):
        self.config = Config(host, port, num_workers, format)
        self.message_handlers = MessageHandlers(self)
        self.server_socket = None
        self.clients = {} 
        self.rooms = {}
        self.next_room_id = 1 # 다음 생성될 방의 ID
        self.message_queue = queue.Queue() # 메세지 처리 큐
        self.cv = threading.Condition()
        self.messages_available = False
        self.running = True
        self.worker_threads = []  # worker 스레드 리스트
        
    # 서버 시작: 서버 소켓 생성 및 설정
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.config.host, self.config.port))
        self.server_socket.listen(5)
        print(f"Port 번호 {self.config.port}에서 서버 동작 중")

        # 워커 스레드 생성 및 시작
        for i in range(self.config.num_workers):
            thread = threading.Thread(target=self.worker, args=(i,), daemon=True)
            thread.start()
            self.worker_threads.append(thread)  # 추가: worker 스레드 저장
            print(f"메시지 작업 쓰레드 #{i} 생성")

        # 클라이언트 연결 수락
        try:
            while self.running:
                try:
                    readable, _, _ = select.select([self.server_socket], [], [], 0.1)
                    if not self.running:
                        break
                    if self.server_socket in readable:
                        client_socket, addr = self.server_socket.accept()
                        print(f"새로운 클라이언트 접속 [{addr}:None]")
                        self.clients[client_socket] = {
                            'addr': addr,
                            'name': f"{addr[0]}:{addr[1]}",
                            'room': None
                        }
                        threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
                except OSError:
                    if not self.running:
                        break
                    else:
                        raise
        except KeyboardInterrupt:
            print("키보드 인터럽트로 서버를 종료합니다.")
        finally:
            if self.running:
                self.handle_shutdown()

    # 워커 쓰레드    
    def worker(self, worker_id):
        while self.running:
            try:
                with self.cv:
                    if not self.running:
                        break
                    if not self.messages_available:
                        self.cv.wait(timeout=0.5)  # 0.5초마다 running 상태 확인
                        continue
                    try:
                        client_socket, message = self.message_queue.get_nowait()
                        self.messages_available = not self.message_queue.empty()
                    except queue.Empty:
                        continue
                self.handle_command(client_socket, message)
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
       
        print(f"메시지 작업 쓰레드 #{worker_id} 종료")

        
    # 클라이언트 제거
    def remove_client(self, client_socket):
        with self.config.lock:
            if client_socket in self.clients:
                room_id = self.clients[client_socket]['room']
                if room_id:
                    self.rooms[room_id]['members'].remove(client_socket)
                    if not self.rooms[room_id]['members']:
                        del self.rooms[room_id]
                del self.clients[client_socket]
            client_socket.close()

    # 클라이언트 연결
    def handle_client(self, client_socket):
        while self.running:
            try:
                message = NetworkUtils.receive_message(client_socket, self.config.format)
                if message:
                    with self.cv:
                        self.message_queue.put((client_socket, message))
                        self.messages_available = True
                        self.cv.notify()
                else:
                    break
            except Exception as e:
                print(f"Error handling client: {e}")
                break
        if self.running:
            self.remove_client(client_socket)

    # 받은 메세지 처리
    def handle_command(self, client_socket, message):
        
        if self.config.format == 'json':
            message_type = message['type']
        else:
            if isinstance(message, dict) and 'type' in message and 'message' in message:
                message_type = pb.Type.MessageType.Name(message['type'])
                actual_message = message['message']
            else:
                print(f"Unexpected message format: {type(message)}")
                return
        
        if message_type in ['CSName', 'CS_NAME']:
            self.message_handlers.handle_name(client_socket, actual_message if self.config.format == 'protobuf' else message)
        elif message_type in ['CSRooms', 'CS_ROOMS']:
            self.message_handlers.handle_rooms(client_socket)
        elif message_type in ['CSCreateRoom', 'CS_CREATE_ROOM']:
            self.message_handlers.handle_create_room(client_socket, actual_message if self.config.format == 'protobuf' else message)
        elif message_type in ['CSJoinRoom', 'CS_JOIN_ROOM']:
            self.message_handlers.handle_join_room(client_socket, actual_message if self.config.format == 'protobuf' else message)
        elif message_type in ['CSLeaveRoom', 'CS_LEAVE_ROOM']:
            self.message_handlers.handle_leave_room(client_socket)
        elif message_type in ['CSChat', 'CS_CHAT']:
            self.message_handlers.handle_chat(client_socket, actual_message if self.config.format == 'protobuf' else message)
        elif message_type in ['CSShutdown', 'CS_SHUTDOWN']:
            self.handle_shutdown()
        else:
            print(f"Unknown message type: {message_type}")

    # /shutdown
    def handle_shutdown(self):
        with self.config.lock:
            if not self.running:
                print("Shutdown already in progress")
                return
            
            print("서버 중지가 요청됨")
            self.running = False
        
        print("Main thread 종료 중")


        # 1단계: 클라이언트에게 종료 메시지 전송 및 연결 종료
        if self.config.format == 'json':
            message = {
                "type": "SCSystemMessage",
                "text": "채팅 서버가 닫힙니다."
            }
        else:  # protobuf
            message = pb.SCSystemMessage()
            message.text = "채팅 서버가 닫힙니다."
    
        for client_socket in list(self.clients.keys()):
            try:
                NetworkUtils.send_message(client_socket, message, self.config.format)
                client_socket.close()
            except Exception as e:
                print(f"Error sending shutdown message to client: {e}")
            finally:
                self.remove_client(client_socket)

        # 2단계: 서버 소켓 닫기
        if self.server_socket and not self.server_socket._closed:
            try:
                self.server_socket.close()
            except Exception as e:
                print(f"Error closing server socket: {e}")

        # 3단계: worker 스레드에게 종료 신호 보내기
        with self.cv:
            self.cv.notify_all()

        # 4단계: worker 스레드 종료 대기
        for thread in self.worker_threads:
            if thread != threading.current_thread():
                print(f"작업 쓰레드 join() 시작")
                thread.join(timeout=5)  # 5초 동안 대기
                print(f"작업 쓰레드 join() 완료")

        print("서버가 정상적으로 종료되었습니다.")