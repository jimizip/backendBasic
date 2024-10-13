#include <fstream>
#include <string>
#include <iostream>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <unistd.h>
#include "person.pb.h"

using namespace std;
using namespace mju;

int main()
{
    // Person 객체 p를 생성하고 데이터를 설정
    Person *p = new Person;
    p->set_name("MJ Kim");
    p->set_id(12345678);

    Person::PhoneNumber* phone = p->add_phones();
    phone->set_number("010-111-1234");
    phone->set_type(Person::MOBILE);

    phone = p->add_phones();
    phone->set_number("02-100-1000");
    phone->set_type(Person::HOME);
    
    // p를 serialize하여 문자열 s를 생성
    const string s = p->SerializeAsString();
    cout << "Length:" << s.length() << endl;

    // UDP 소켓을 생성하고 설정
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) return 1;

    struct sockaddr_in sin;
    memset(&sin, 0, sizeof(sin));
    sin.sin_family = AF_INET;
    sin.sin_port = htons(10001);
    sin.sin_addr.s_addr = inet_addr("127.0.0.1");
    
    // sendto() 함수를 사용하여 s를 UDP echo server로 전송
    int numBytes = sendto(sock, s.c_str(), s.length(), 0, (struct sockaddr *) &sin, sizeof(sin));
    cout << "Sent: " << numBytes << " bytes" << endl;

    // recvfrom() 함수를 사용하여 echo server로부터 데이터를 받아 buf2에 저장
    char buf2[65536];
    memset(&sin, 0, sizeof(sin));
    socklen_t sin_size = sizeof(sin);
    numBytes = recvfrom(sock, buf2, sizeof(buf2), 0, (struct sockaddr *) &sin, &sin_size);
    cout << "Received: " << numBytes << " bytes" << endl;
    cout << "From " << inet_ntoa(sin.sin_addr) << endl;

    // 받은 데이터(buf2)를 사용하여 새로운 Person 객체 p2를 생성
    Person *p2 = new Person;
    bool success = p2->ParseFromArray(buf2, numBytes);
    // 성공적으로 파싱되면 p2의 내용을 출력
    if (success) {
        cout << "Name:" << p2->name() << endl;
        cout << "ID:" << p2->id() << endl;
        for (int i = 0; i < p2->phones_size(); ++i) {
            cout << "Type:" << p2->phones(i).type() << endl;
            cout << "Phone:" << p2->phones(i).number() << endl;
        }
    } else {
        cerr << "파싱 실패" << endl;
    }

    close(sock);
    return 0;
}

