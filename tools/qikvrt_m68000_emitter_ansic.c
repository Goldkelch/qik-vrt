/* QIK-VRT minimal Motorola 68000 emitter - ANSI C89.
 * Supported v1 instructions: MOVEQ, NOP, RTS.
 * Output is raw big-endian 68000 instruction bytes on stdout.
 */
#include <stdio.h>
#include <string.h>

static int emit_word(unsigned int word)
{
    if (putchar((int)((word >> 8) & 0xffU)) == EOF) return 0;
    if (putchar((int)(word & 0xffU)) == EOF) return 0;
    return 1;
}

static int parse_dreg(const char *s)
{
    if (s[0] != 'D' || s[1] < '0' || s[1] > '7' || s[2] != '\0') return -1;
    return (int)(s[1] - '0');
}

int main(void)
{
    char line[256];
    char op[32];
    char arg1[32];
    int value;

    while (fgets(line, sizeof(line), stdin) != NULL) {
        int n;
        if (line[0] == '#' || line[0] == '\n') continue;
        op[0] = '\0'; arg1[0] = '\0'; value = 0;
        n = sscanf(line, "%31s %31s %d", op, arg1, &value);

        if (strcmp(op, "NOP") == 0 && n == 1) {
            if (!emit_word(0x4e71U)) return 3;
        } else if (strcmp(op, "RTS") == 0 && n == 1) {
            if (!emit_word(0x4e75U)) return 3;
        } else if (strcmp(op, "MOVEQ") == 0 && n == 3) {
            int reg;
            unsigned int word;
            reg = parse_dreg(arg1);
            if (reg < 0 || value < -128 || value > 127) {
                fprintf(stderr, "HOLD: unzulaessiges MOVEQ\n");
                return 2;
            }
            word = 0x7000U | ((unsigned int)reg << 9) | ((unsigned int)value & 0xffU);
            if (!emit_word(word)) return 3;
        } else {
            fprintf(stderr, "HOLD: unbekannte oder unzulaessige M68000-IR\n");
            return 2;
        }
    }
    if (ferror(stdin) || ferror(stdout)) return 3;
    return 0;
}
