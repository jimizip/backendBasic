#!/usr/bin/env python3
import threading

class Config:
    def __init__(self, host, port, num_workers, format):
        self.host = host # 서버 호스트 주소
        self.port = port # 서버 포트 번호
        self.num_workers = num_workers # 워커 스레드 수
        self.format = format # 메시지 형식 (JSON, Protobuf)
        self.lock = threading.Lock() # 쓰레드 간 동기화를 위한 lock