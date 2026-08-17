/* QIK-VRT Metagrammatik des Verstehens - ANSI C (C89/C90) Compiler-Frontend.
 *
 * Pipeline: Quelle -> Lexer -> Parser -> AST -> Semantik -> Entscheidungsplan.
 * Fail-closed: jeder Syntax-/Bindungs-/Autoritaetsfehler endet in HOLD.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define QMC_MAX_LINE 4096
#define QMC_MAX_TOKEN 512
#define QMC_TOKEN_COUNT 10

struct qmc_ast {
    char kind[QMC_MAX_TOKEN];
    char rid[QMC_MAX_TOKEN];
    char binding[QMC_MAX_TOKEN];
    char intent[QMC_MAX_TOKEN];
    char authority[QMC_MAX_TOKEN];
    char evidence[QMC_MAX_TOKEN];
    char state[QMC_MAX_TOKEN];
    char effect[QMC_MAX_TOKEN];
    char next_action[QMC_MAX_TOKEN];
    char proof[QMC_MAX_TOKEN];
};

static int qmc_copy(char *dst, size_t cap, const char *src, size_t len)
{
    if (len + 1U > cap) return 0;
    memcpy(dst, src, len);
    dst[len] = '\0';
    return 1;
}

static int qmc_hex(const char *s, size_t n)
{
    size_t i;
    if (s == NULL || strlen(s) != n) return 0;
    for (i = 0U; i < n; ++i) {
        if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return 0;
    }
    return 1;
}

static int qmc_lex(const char *line, char tokens[QMC_TOKEN_COUNT][QMC_MAX_TOKEN])
{
    const char *p;
    const char *start;
    int index;

    index = 0;
    p = line;
    start = line;
    for (;;) {
        if (*p == '|' || *p == '\0' || *p == '\n' || *p == '\r') {
            if (index >= QMC_TOKEN_COUNT) return 0;
            if (!qmc_copy(tokens[index], QMC_MAX_TOKEN, start, (size_t)(p - start))) return 0;
            ++index;
            if (*p != '|') break;
            start = p + 1;
        }
        ++p;
    }
    return index == QMC_TOKEN_COUNT;
}

static int qmc_prefix(const char *s, const char *prefix, const char **value)
{
    size_t n;
    n = strlen(prefix);
    if (strncmp(s, prefix, n) != 0) return 0;
    *value = s + n;
    return **value != '\0';
}

static int qmc_parse_binding(const char *s)
{
    const char *at;
    const char *colon;
    const char *slash;
    char head[41];
    char tree[41];

    slash = strchr(s, '/');
    at = strchr(s, '@');
    colon = at ? strchr(at + 1, ':') : NULL;
    if (slash == NULL || at == NULL || colon == NULL || slash > at) return 0;
    if ((size_t)(colon - at - 1) != 40U || strlen(colon + 1) != 40U) return 0;
    if (!qmc_copy(head, sizeof(head), at + 1, 40U)) return 0;
    if (!qmc_copy(tree, sizeof(tree), colon + 1, 40U)) return 0;
    return qmc_hex(head, 40U) && qmc_hex(tree, 40U);
}

static int qmc_parse(char tokens[QMC_TOKEN_COUNT][QMC_MAX_TOKEN], struct qmc_ast *ast)
{
    memcpy(ast->kind, tokens[0], QMC_MAX_TOKEN);
    memcpy(ast->rid, tokens[1], QMC_MAX_TOKEN);
    memcpy(ast->binding, tokens[2], QMC_MAX_TOKEN);
    memcpy(ast->intent, tokens[3], QMC_MAX_TOKEN);
    memcpy(ast->authority, tokens[4], QMC_MAX_TOKEN);
    memcpy(ast->evidence, tokens[5], QMC_MAX_TOKEN);
    memcpy(ast->state, tokens[6], QMC_MAX_TOKEN);
    memcpy(ast->effect, tokens[7], QMC_MAX_TOKEN);
    memcpy(ast->next_action, tokens[8], QMC_MAX_TOKEN);
    memcpy(ast->proof, tokens[9], QMC_MAX_TOKEN);
    return 1;
}

static int qmc_productive_verb(const char *intent)
{
    static const char *const verbs[] = {"EXECUTE", "CREATE", "UPDATE", "CLOSE", "DISPATCH", "PERSIST"};
    size_t i;
    for (i = 0U; i < sizeof(verbs) / sizeof(verbs[0]); ++i) {
        size_t n;
        n = strlen(verbs[i]);
        if (strncmp(intent, verbs[i], n) == 0 && intent[n] == ' ') return 1;
    }
    return 0;
}

static int qmc_semantic(const struct qmc_ast *ast, char *reason, size_t cap)
{
    const char *auth;
    const char *proof;
    const char *next;
    int productive;

    if (ast->rid[0] == '\0') { strncpy(reason, "RID_FEHLT", cap); return 0; }
    if (!qmc_parse_binding(ast->binding)) { strncpy(reason, "BINDUNG_UNGUELTIG", cap); return 0; }
    if (strchr(ast->intent, ' ') == NULL) { strncpy(reason, "ABSICHT_UNGUELTIG", cap); return 0; }
    if (!qmc_prefix(ast->authority, "AUTH=", &auth)) { strncpy(reason, "AUTORITAET_UNGUELTIG", cap); return 0; }
    if (!qmc_prefix(ast->next_action, "NEXT=", &next)) { strncpy(reason, "NEXT_UNGUELTIG", cap); return 0; }
    if (!qmc_prefix(ast->proof, "PROOF=", &proof) || !qmc_hex(proof, 64U)) { strncpy(reason, "BEWEIS_UNGUELTIG", cap); return 0; }

    productive = strcmp(ast->kind, "ACT") == 0 || qmc_productive_verb(ast->intent);
    if (productive && strncmp(auth, "BOUND:", 6U) != 0) {
        strncpy(reason, "PRODUKTIVE_WIRKUNG_OHNE_AUTORITAET", cap); return 0;
    }
    if (strncmp(auth, "BOUND:", 6U) != 0 && strcmp(next, "HOLD") != 0 && strcmp(next, "NOOP") != 0 && strcmp(next, "REOBSERVE") != 0 && strcmp(next, "REQUEST_AUTHORITY") != 0) {
        strncpy(reason, "UNBEFUGTE_FORTSETZUNG", cap); return 0;
    }
    if (strcmp(ast->state, "STATE=UNKNOWN") == 0 && productive) {
        strncpy(reason, "UNKNOWN_DARF_NICHT_WIRKEN", cap); return 0;
    }
    if (strncmp(ast->effect, "EFFECT=ACKNOWLEDGED:", 20U) == 0 && strcmp(ast->kind, "ACK") != 0) {
        strncpy(reason, "ACK_ERFORDERT_ACK_NACHRICHT", cap); return 0;
    }
    reason[0] = '\0';
    return 1;
}

static void qmc_emit_plan(const struct qmc_ast *ast)
{
    const char *next;
    if (!qmc_prefix(ast->next_action, "NEXT=", &next)) next = "HOLD";
    printf("QIKVRT_METAGRAMMAR_PLAN_V1\n");
    printf("RID=%s\n", ast->rid);
    printf("BINDING=%s\n", ast->binding);
    printf("INTENT=%s\n", ast->intent);
    printf("AUTHORITY=%s\n", ast->authority);
    printf("STATE=%s\n", ast->state);
    printf("EFFECT=%s\n", ast->effect);
    printf("NEXT_ACTION=%s\n", next);
    printf("PROOF=%s\n", ast->proof);
    printf("ADMISSION=VALIDATED\n");
}

int main(int argc, char **argv)
{
    FILE *in;
    char line[QMC_MAX_LINE];
    char tokens[QMC_TOKEN_COUNT][QMC_MAX_TOKEN];
    char reason[128];
    struct qmc_ast ast;

    in = stdin;
    if (argc > 2) { fprintf(stderr, "Verwendung: %s [datei]\n", argv[0]); return 64; }
    if (argc == 2) {
        in = fopen(argv[1], "r");
        if (in == NULL) { fprintf(stderr, "HOLD: DATEI_NICHT_LESBAR\n"); return 66; }
    }
    if (fgets(line, sizeof(line), in) == NULL) {
        if (in != stdin) fclose(in);
        fprintf(stderr, "HOLD: LEERE_QUELLE\n"); return 2;
    }
    if (in != stdin) fclose(in);
    memset(tokens, 0, sizeof(tokens));
    memset(&ast, 0, sizeof(ast));
    if (!qmc_lex(line, tokens)) { fprintf(stderr, "HOLD: LEXER_ERWARTET_10_FELDER\n"); return 2; }
    if (!qmc_parse(tokens, &ast)) { fprintf(stderr, "HOLD: PARSER_FEHLER\n"); return 2; }
    if (!qmc_semantic(&ast, reason, sizeof(reason))) { fprintf(stderr, "HOLD: %s\n", reason); return 2; }
    qmc_emit_plan(&ast);
    return 0;
}
