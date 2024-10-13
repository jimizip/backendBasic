import json
import sys
import socket

def main(argv):
    obj1 = {
        'name': 'DK Moon',
        'id': 12345678,
        'work': {
            'name': 'Myongji Unviversity',
            'address': '116 Myongji-ro'
        }
    }
    s = json.dumps(obj1)

    # UDP 소켓 생성
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    
    # 데이터 전송
    sock.sendto(bytes(s, encoding='utf-8'), ('127.0.0.1', 10001))
    
    # 데이터 수신
    data, sender = sock.recvfrom(65536)
    
    # 수신된 데이터를 디코딩하고 JSON으로 파싱하여 obj2 생성
    received_str = data.decode('utf-8')
    obj2 = json.loads(received_str)

    print(obj2['name'], obj2['id'], obj2['work']['address'])
    print(obj1 == obj2)

    sock.close()

if __name__ == '__main__':
    main(sys.argv)
