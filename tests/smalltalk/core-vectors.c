/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Reuse the existing exhaustive test snapshot constructor; no second C oracle. */
#define main qikvrt_existing_test_main
#include "../test_effect_ack_core.c"
#undef main
int main(void)
{
    unsigned long mask;
    int decision;
    qikvrt_effect_ack_input input;
    for (mask = 0UL; mask < (1UL << 19); ++mask) {
        for (decision = 0; decision < 5; ++decision) {
            input = input_from_mask(mask, (qikvrt_effect_ack_decision)decision);
            if (putchar((int)qikvrt_effect_ack_evaluate(&input)) == EOF) {
                return 74;
            }
        }
    }
    return fflush(stdout) == 0 ? 0 : 74;
}
