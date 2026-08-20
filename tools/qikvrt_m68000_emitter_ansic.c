/* QIK-VRT four-capsule Motorola 68000 emitter - ANSI C89.
 * Accepted capsule IR is exactly:
 *   MOVEQ D0 <0|1|2|3>
 *   RTS
 * The complete capsule is validated before any raw big-endian bytes are emitted.
 */
#include <stdio.h>
#include <string.h>

static int emit_word(unsigned int word)
{
    if (putchar((int)((word >> 8) & 0xffU)) == EOF) return 0;
    if (putchar((int)(word & 0xffU)) == EOF) return 0;
    return 1;
}

static int blank_or_comment(const char *line)
{
    const char *p;
    p = line;
    while (*p == ' ' || *p == '\t' || *p == '\r') ++p;
    return *p == '\0' || *p == '\n' || *p == '#';
}

int main(void)
{
    char line[256];
    char op[32];
    char arg1[32];
    char extra[32];
    int value;
    int state;
    int code;

    state = 0;
    code = -1;

    while (fgets(line, sizeof(line), stdin) != NULL) {
        int n;
        if (blank_or_comment(line)) continue;
        op[0] = '\0';
        arg1[0] = '\0';
        extra[0] = '\0';
        value = 0;

        if (state == 0) {
            n = sscanf(line, "%31s %31s %d %31s", op, arg1, &value, extra);
            if (n != 3 || strcmp(op, "MOVEQ") != 0 || strcmp(arg1, "D0") != 0 || value < 0 || value > 3) {
                fprintf(stderr, "HOLD: unzulaessige Vier-Kapsel-IR\n");
                return 2;
            }
            code = value;
            state = 1;
        } else if (state == 1) {
            n = sscanf(line, "%31s %31s", op, extra);
            if (n != 1 || strcmp(op, "RTS") != 0) {
                fprintf(stderr, "HOLD: Vier-Kapsel-IR ohne exaktes RTS\n");
                return 2;
            }
            state = 2;
        } else {
            fprintf(stderr, "HOLD: zusaetzliche M68000-IR ausserhalb der Kapsel\n");
            return 2;
        }
    }

    if (ferror(stdin)) return 3;
    if (state != 2 || code < 0) {
        fprintf(stderr, "HOLD: unvollstaendige Vier-Kapsel-IR\n");
        return 2;
    }

    if (!emit_word(0x7000U | ((unsigned int)code & 0xffU))) return 3;
    if (!emit_word(0x4e75U)) return 3;
    if (ferror(stdout)) return 3;
    return 0;
}
