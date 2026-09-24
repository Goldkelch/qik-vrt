/* Enumeration and ASCII I/O only: shared C90/MC68000 ABI harness. */
#include <stdio.h>
extern unsigned long full_core(unsigned long, unsigned long, unsigned long);
extern unsigned long full_admit(unsigned long, unsigned long, unsigned long);
int main(void)
{
    unsigned long m, r, d, result;
    for (m = 0; m < 262144UL; ++m)
        for (r = 0; r < 6UL; ++r)
            for (d = 0; d < 6UL; ++d) {
                result = full_core(m, r, d);
                if (result > 5UL || putchar((int)('0' + result)) == EOF)
                    return 1;
            }
    for (r = 0; r < 6UL; ++r)
        for (d = 0; d < 6UL; ++d)
            for (m = 0; m < 512UL; ++m) {
                result = full_admit(r, d, m);
                if (result > 1UL || putchar((int)('0' + result)) == EOF)
                    return 1;
            }
    return fflush(stdout) == 0 ? 0 : 1;
}
