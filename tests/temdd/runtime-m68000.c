/* TEMDD v0.1 executable M68000 backend vector test. */
#include <stdio.h>
extern int temdd_transition_call(int event);
int main(void) {
    static const int expected[4] = {0, 1, 2, 0};
    int event;
    for (event = 0; event < 4; ++event) {
        int observed = temdd_transition_call(event);
        if (observed != expected[event]) return 10 + event;
    }
    puts("TEMDD_M68000_EXECUTED vectors=4");
    return 0;
}
