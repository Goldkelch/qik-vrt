/* QIK-VRT Metagrammatik des Verstehens - ANSI C (C89/C90) Kern.
 *
 * Zweck: kompakte Terminalprojektion lexikalisch, syntaktisch und semantisch
 * fail-closed pruefen. Die kanonische JSON-Huelle bleibt autoritativ.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#define QMG_MAX_LINE 4096
#define QMG_MAX_FIELD 512
#define QMG_FIELD_COUNT 9

struct qmg_message {
    char kind[QMG_MAX_FIELD];
    char rid[QMG_MAX_FIELD];
    char binding[QMG_MAX_FIELD];
    char intent[QMG_MAX_FIELD];
    char authority[QMG_MAX_FIELD];
    char evidence[QMG_MAX_FIELD];
    char state[QMG_MAX_FIELD];
    char effect[QMG_MAX_FIELD];
    char proof[QMG_MAX_FIELD];
};

static int qmg_is_hex_n(const char *s, size_t n)
{
    size_t i;
    if (s == NULL || strlen(s) != n) return 0;
    for (i = 0; i < n; ++i) {
        if (!((s[i] >= '0' && s[i] <= '9') ||
              (s[i] >= 'a' && s[i] <= 'f'))) return 0;
    }
    return 1;
}

static int qmg_in_set(const char *s, const char *const *set, size_t n)
{
    size_t i;
    for (i = 0; i < n; ++i) {
        if (strcmp(s, set[i]) == 0) return 1;
    }
    return 0;
}

static int qmg_copy(char *dst, size_t cap, const char *src, size_t len)
{
    if (len + 1 > cap) return 0;
    memcpy(dst, src, len);
    dst[len] = '\0';
    return 1;
}

static int qmg_split_fields(const char *line, struct qmg_message *m)
{
    char *out[QMG_FIELD_COUNT];
    const char *p;
    const char *start;
    int index;

    out[0] = m->kind;
    out[1] = m->rid;
    out[2] = m->binding;
    out[3] = m->intent;
    out[4] = m->authority;
    out[5] = m->evidence;
    out[6] = m->state;
    out[7] = m->effect;
    out[8] = m->proof;

    index = 0;
    start = line;
    p = line;
    for (;;) {
        if (*p == '|' || *p == '\0' || *p == '\n' || *p == '\r') {
            if (index >= QMG_FIELD_COUNT) return 0;
            if (!qmg_copy(out[index], QMG_MAX_FIELD, start, (size_t)(p - start))) return 0;
            ++index;
            if (*p != '|') break;
            start = p + 1;
        }
        ++p;
    }
    return index == QMG_FIELD_COUNT;
}

static int qmg_validate_binding(const char *binding)
{
    const char *at;
    const char *colon;
    const char *slash;
    char head[41];
    char tree[41];

    at = strchr(binding, '@');
    colon = at ? strchr(at + 1, ':') : NULL;
    slash = strchr(binding, '/');
    if (at == NULL || colon == NULL || slash == NULL || slash > at) return 0;
    if ((size_t)(colon - at - 1) != 40U) return 0;
    if (strlen(colon + 1) != 40U) return 0;
    if (!qmg_copy(head, sizeof(head), at + 1, 40U)) return 0;
    if (!qmg_copy(tree, sizeof(tree), colon + 1, 40U)) return 0;
    return qmg_is_hex_n(head, 40U) && qmg_is_hex_n(tree, 40U);
}

static int qmg_prefix_value(const char *field, const char *prefix, const char **value)
{
    size_t n;
    n = strlen(prefix);
    if (strncmp(field, prefix, n) != 0) return 0;
    *value = field + n;
    return **value != '\0';
}

static int qmg_validate_semantics(const struct qmg_message *m, char *error, size_t cap)
{
    static const char *const kinds[] = {
        "OBSERVE", "DECIDE", "REQUEST", "AUTHORIZE", "ACT",
        "ACK", "HOLD", "NOOP", "ERROR"
    };
    static const char *const verbs[] = {
        "OBSERVE", "CLASSIFY", "BIND", "DECIDE", "EXECUTE", "TEST",
        "REOBSERVE", "ACK", "PERSIST", "CREATE", "UPDATE", "CLOSE", "DISPATCH"
    };
    const char *auth;
    const char *evid;
    const char *state;
    const char *effect;
    const char *next;
    const char *proof;
    const char *space;
    char verb[QMG_MAX_FIELD];
    int auth_bound;
    int productive;

    if (!qmg_in_set(m->kind, kinds, sizeof(kinds) / sizeof(kinds[0]))) {
        strncpy(error, "ungueltige Nachrichtenart", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (m->rid[0] == '\0') {
        strncpy(error, "RID fehlt", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!qmg_validate_binding(m->binding)) {
        strncpy(error, "BINDUNG muss REPO@40HEX:40HEX sein", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    space = strchr(m->intent, ' ');
    if (space == NULL || space == m->intent || *(space + 1) == '\0') {
        strncpy(error, "ABSICHT muss VERB OBJEKT sein", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!qmg_copy(verb, sizeof(verb), m->intent, (size_t)(space - m->intent)) ||
        !qmg_in_set(verb, verbs, sizeof(verbs) / sizeof(verbs[0]))) {
        strncpy(error, "ungueltiges Verb", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!qmg_prefix_value(m->authority, "AUTH=", &auth) || strchr(auth, ':') == NULL) {
        strncpy(error, "AUTORITAET ungueltig", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!qmg_prefix_value(m->evidence, "EVID=", &evid) || strchr(evid, ':') == NULL) {
        strncpy(error, "EVIDENZ ungueltig", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!qmg_prefix_value(m->state, "STATE=", &state)) {
        strncpy(error, "ZUSTAND ungueltig", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!qmg_prefix_value(m->effect, "EFFECT=", &effect) || strchr(effect, ':') == NULL) {
        strncpy(error, "WIRKUNG ungueltig", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!qmg_prefix_value(m->proof, "PROOF=", &proof) || !qmg_is_hex_n(proof, 64U)) {
        strncpy(error, "BEWEIS muss SHA256 sein", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }

    auth_bound = strncmp(auth, "BOUND:", 6U) == 0;
    productive = strcmp(m->kind, "ACT") == 0 || strcmp(verb, "EXECUTE") == 0 ||
                 strcmp(verb, "CREATE") == 0 || strcmp(verb, "UPDATE") == 0 ||
                 strcmp(verb, "CLOSE") == 0 || strcmp(verb, "DISPATCH") == 0;

    if (productive && !auth_bound) {
        strncpy(error, "produktive Wirkung ohne gebundene Autoritaet", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (!auth_bound) {
        next = strstr(state, "NEXT=");
        if (next != NULL && strstr(next, "EXECUTE") != NULL) {
            strncpy(error, "ungebundene Autoritaet darf EXECUTE nicht zulassen", cap - 1U); error[cap - 1U] = '\0'; return 0;
        }
    }
    if (strncmp(effect, "ACKNOWLEDGED:", 13U) == 0 && strcmp(m->kind, "ACK") != 0) {
        strncpy(error, "ACKNOWLEDGED erfordert Nachrichtenart ACK", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    if (strcmp(state, "UNKNOWN") == 0 && productive) {
        strncpy(error, "UNKNOWN darf nicht produktiv wirken", cap - 1U); error[cap - 1U] = '\0'; return 0;
    }
    return 1;
}

static void qmg_emit_ast(const struct qmg_message *m)
{
    printf("QMG_AST_V1\n");
    printf("  ART=%s\n", m->kind);
    printf("  RID=%s\n", m->rid);
    printf("  BINDUNG=%s\n", m->binding);
    printf("  ABSICHT=%s\n", m->intent);
    printf("  AUTORITAET=%s\n", m->authority);
    printf("  EVIDENZ=%s\n", m->evidence);
    printf("  ZUSTAND=%s\n", m->state);
    printf("  WIRKUNG=%s\n", m->effect);
    printf("  BEWEIS=%s\n", m->proof);
}

int main(int argc, char **argv)
{
    char line[QMG_MAX_LINE];
    char error[256];
    struct qmg_message message;
    FILE *in;

    in = stdin;
    if (argc > 2) {
        fprintf(stderr, "Verwendung: %s [datei]\n", argv[0]);
        return 64;
    }
    if (argc == 2) {
        in = fopen(argv[1], "r");
        if (in == NULL) {
            fprintf(stderr, "ERROR: Datei nicht lesbar\n");
            return 66;
        }
    }
    if (fgets(line, sizeof(line), in) == NULL) {
        if (in != stdin) fclose(in);
        fprintf(stderr, "HOLD: keine Nachricht\n");
        return 2;
    }
    if (in != stdin) fclose(in);
    memset(&message, 0, sizeof(message));
    if (!qmg_split_fields(line, &message)) {
        fprintf(stderr, "HOLD: erwartet genau neun Felder\n");
        return 2;
    }
    if (!qmg_validate_semantics(&message, error, sizeof(error))) {
        fprintf(stderr, "HOLD: %s\n", error);
        return 2;
    }
    qmg_emit_ast(&message);
    printf("VALID\n");
    return 0;
}
