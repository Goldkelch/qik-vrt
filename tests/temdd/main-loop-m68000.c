/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
#include <stdio.h>
extern unsigned long temdd_effect_ack_done_call(unsigned long flags);

int main(void) {
    unsigned long flags;
    unsigned long observed;
    for (flags = 0; flags < 256; ++flags) {
        observed = temdd_effect_ack_done_call(flags);
        if (observed != (flags == 255UL ? 1UL : 0UL))
            return (int)(10UL + flags);
    }
    puts("TEMDD_MAIN_LOOP_M68000_EXECUTED vectors=256");
    return 0;
}
