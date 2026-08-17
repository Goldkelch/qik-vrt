/* QIK-VRT validated-plan to M68000 capsule IR lowerer - ANSI C89.
 * ABI v1: return decision code in D0, then RTS.
 * 0 NOOP, 1 HOLD, 2 REOBSERVE, 3 REQUEST_AUTHORITY.
 * Unsupported actions fail closed and emit no executable IR.
 */
#include <stdio.h>
#include <string.h>

int main(void)
{
    char line[1024];
    char next[256];
    int admitted;
    int found;
    int code;

    next[0] = '\0';
    admitted = 0;
    found = 0;
    while (fgets(line, sizeof(line), stdin) != NULL) {
        if (strncmp(line, "NEXT_ACTION=", 12U) == 0) {
            size_t n;
            n = strlen(line + 12);
            while (n > 0U && (line[12 + n - 1U] == '\n' || line[12 + n - 1U] == '\r')) --n;
            if (n == 0U || n >= sizeof(next)) { fprintf(stderr, "HOLD: NEXT_ACTION_UNGUELTIG\n"); return 2; }
            memcpy(next, line + 12, n);
            next[n] = '\0';
            found = 1;
        }
        if (strcmp(line, "ADMISSION=VALIDATED\n") == 0 || strcmp(line, "ADMISSION=VALIDATED\r\n") == 0 || strcmp(line, "ADMISSION=VALIDATED") == 0) admitted = 1;
    }
    if (!found || !admitted) { fprintf(stderr, "HOLD: PLAN_NICHT_VALIDIERT\n"); return 2; }

    if (strcmp(next, "NOOP") == 0) code = 0;
    else if (strcmp(next, "HOLD") == 0) code = 1;
    else if (strcmp(next, "REOBSERVE") == 0) code = 2;
    else if (strcmp(next, "REQUEST_AUTHORITY") == 0) code = 3;
    else { fprintf(stderr, "HOLD: M68000_ABI_AKTION_NICHT_UNTERSTUETZT\n"); return 2; }

    printf("MOVEQ D0 %d\n", code);
    printf("RTS\n");
    return 0;
}
