#!/usr/bin/env python3

import argparse
from chat_server import ChatServer

def main():
    parser = argparse.ArgumentParser(description="Chat Server")
    parser.add_argument('--port', type=int, required=True, help='Server port number')
    parser.add_argument('--workers', type=int, default=2, help='Number of worker threads')
    parser.add_argument('--format', choices=['json', 'protobuf'], default='json', help='Message format')
    args = parser.parse_args()

    server = ChatServer('127.0.0.1', args.port, args.workers, args.format)
    try:
        server.start()
    except KeyboardInterrupt:
        print("키보드 인터럽트로 서버를 종료합니다.")
    finally:
        server.handle_shutdown()
        
if __name__ == '__main__':
    main()