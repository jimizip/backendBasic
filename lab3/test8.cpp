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
    // 에러 코드 추가
    if (s < 0) {
        cerr << "소켓 생성 실패" << endl;
        return 1;
    }

    struct sockaddr_in sin;
    memset(&sin, 0, sizeof(sin));
    sin.sin_family = AF_INET;
    sin.sin_addr.s_addr = INADDR_ANY;
    sin.sin_port = htons(10000 + 201);

    if (bind(s, (struct sockaddr *) &sin, sizeof(sin)) < 0) {
        cerr << strerror(errno) << endl;
        return 0;
    }

    char buffer[65536];
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);

    while (true) {
        memset(buffer, 0, sizeof(buffer));
        int numBytes = recvfrom(s, buffer, sizeof(buffer), 0, (struct sockaddr *) &client_addr, &client_addr_len);
        
        // 에러 코드 추가
        if (numBytes < 0) {
            cerr << "recvfrom 실패: " << strerror(errno) << endl;
            continue;
        }

        cout << "Received: " << numBytes << endl;
        cout << "From " << inet_ntoa(client_addr.sin_addr) << endl;
        cout << "Data: " << string(buffer, numBytes) << endl;

        // 메시지 에코
        int send_len = sendto(s, buffer, numBytes, 0, (struct sockaddr *)&client_addr, client_addr_len);
        if (send_len < 0) {
            cerr << "sendto 실패: " << strerror(errno) << endl;
        } else {
            cout << "Sent: " << send_len << endl;
        }
    }

    close(s);
    return 0;
}
