#include <chrono>
#include <iostream>
#include <thread>
#include <mutex>

using namespace std;
mutex m;
mutex m2;

int sum = 0;
void f() {
    for (int i = 0; i < 10 * 1000 * 1000; ++i) {
        // unique_lock<mutex> ul(m);
        m.lock();
        m2.lock();
        ++sum;
        m.unlock();
        m2.unlock();

    }
}
int main() {
    thread t(f);
    for (int i = 0; i < 10 * 1000 * 1000; ++i) {
        // unique_lock<mutex> ul(m);
        m.lock();
        m2.lock();
        ++sum;
        m.unlock();
        m2.unlock();
    }
    t.join();
    cout << "Sum: " << sum << endl;
}
