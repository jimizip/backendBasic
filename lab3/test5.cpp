#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <unistd.h>

#include <iostream>
#include <string>

using namespace std;

int main() {
    int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    // 에러 확인 코드 추가
    if (s < 0) {
        cout << "소켓 생성 실패" << endl;
        return 1;
    }

    struct sockaddr_in sin;
    memset(&sin, 0, sizeof(sin));
    sin.sin_family = AF_INET;
    sin.sin_port = htons(10001);
    sin.sin_addr.s_addr = inet_addr("127.0.0.1");

    // 입력 받기
    string input;
    while (cin >> input) {
        int numBytes = sendto(s, input.c_str(), input.length(), 0, (struct sockaddr *) &sin, sizeof(sin));
        // 에러 확인 코드 추가
        if (numBytes < 0) {
            cout << "전송 실패" << endl;
            continue;
        }
        cout << "Sent: " << numBytes << endl;

        char buf2[65536];
        memset(&sin, 0, sizeof(sin));
        socklen_t sin_size = sizeof(sin);
        numBytes = recvfrom(s, buf2, sizeof(buf2), 0, (struct sockaddr *) &sin, &sin_size);
        // 에러 확인 코드 추가
        if (numBytes < 0) {
            cout << "수신 실패" << endl;
            continue;
        }
        cout << "Recevied: " << numBytes << endl;
        cout << "From " << inet_ntoa(sin.sin_addr) << endl;
        // 수신된 데이터 출력
        cout << string(buf2, numBytes) << endl;
    }
    close(s);
    return 0;
}
