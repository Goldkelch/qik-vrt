/* QIK-VRT Universal Understanding Compiler Language V1 - ANSI C89 frontend.
 *
 * Universal frontend:
 *   QIKU1 source -> validated textual decision plan.
 *
 * Optional target mode:
 *   --target-megast additionally requires repo exact HEAD/TREE binding and
 *   limits NEXT to NOOP/HOLD/REOBSERVE/REQUEST_AUTHORITY. The resulting plan
 *   is intentionally consumable by the existing M68000 lowerer/emitter.
 *
 * Causality is explicit in CAUSE. Source-line order has no causal authority.
 * The distinction kernel is a compiler invariant, not source-redefinable data.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define QIKU_LINE 1024
#define QIKU_TOKEN 256
#define QIKU_INTENT 512

struct qiku_unit {
    char kind[QIKU_TOKEN];
    char rid[QIKU_TOKEN];
    char subject_scheme[QIKU_TOKEN];
    char subject_id[QIKU_TOKEN];
    char subject_version[QIKU_TOKEN];
    char subject_state[QIKU_TOKEN];
    char intent[QIKU_INTENT];
    char auth_state[QIKU_TOKEN];
    char auth_id[QIKU_TOKEN];
    char evid_type[QIKU_TOKEN];
    char evid_digest[QIKU_TOKEN];
    char state[QIKU_TOKEN];
    char effect_state[QIKU_TOKEN];
    char effect_id[QIKU_TOKEN];
    char next_action[QIKU_TOKEN];
    char proof[QIKU_TOKEN];
    char cause[QIKU_TOKEN];
};

static void qiku_chomp(char *s)
{
    size_t n;
    n = strlen(s);
    while (n > 0U && (s[n - 1U] == '\n' || s[n - 1U] == '\r')) {
        s[n - 1U] = '\0';
        --n;
    }
}

static int qiku_copy(char *dst, size_t cap, const char *src)
{
    size_t n;
    n = strlen(src);
    if (n == 0U || n + 1U > cap) return 0;
    memcpy(dst, src, n + 1U);
    return 1;
}

static int qiku_hex(const char *s, size_t n)
{
    size_t i;
    if (s == NULL || strlen(s) != n) return 0;
    for (i = 0U; i < n; ++i) {
        if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return 0;
    }
    return 1;
}

static int qiku_allowed(const char *value, const char *const *items, size_t count)
{
    size_t i;
    for (i = 0U; i < count; ++i) if (strcmp(value, items[i]) == 0) return 1;
    return 0;
}

static int qiku_productive_intent(const char *intent)
{
    static const char *const verbs[] = {
        "EXECUTE", "CREATE", "UPDATE", "CLOSE", "DISPATCH", "PERSIST"
    };
    size_t i;
    for (i = 0U; i < sizeof(verbs) / sizeof(verbs[0]); ++i) {
        size_t n;
        n = strlen(verbs[i]);
        if (strncmp(intent, verbs[i], n) == 0 && intent[n] == ' ') return 1;
    }
    return 0;
}

static int qiku_safe_nonbound_action(const char *action)
{
    return strcmp(action, "HOLD") == 0 || strcmp(action, "NOOP") == 0 ||
           strcmp(action, "REOBSERVE") == 0 || strcmp(action, "REQUEST_AUTHORITY") == 0;
}

static int qiku_target_action(const char *action)
{
    return qiku_safe_nonbound_action(action);
}

static int qiku_read_prefixed(FILE *in, const char *prefix, char *dst, size_t cap)
{
    char line[QIKU_LINE];
    size_t n;
    if (fgets(line, sizeof(line), in) == NULL) return 0;
    qiku_chomp(line);
    n = strlen(prefix);
    if (strncmp(line, prefix, n) != 0) return 0;
    return qiku_copy(dst, cap, line + n);
}

static int qiku_parse(FILE *in, struct qiku_unit *u, char *reason, size_t cap)
{
    char line[QIKU_LINE];
    char value[QIKU_LINE];
    int n;

    if (fgets(line, sizeof(line), in) == NULL) { strncpy(reason, "LEERE_QUELLE", cap); return 0; }
    qiku_chomp(line);
    if (strcmp(line, "QIKU1") != 0) { strncpy(reason, "MAGIC_UNGUELTIG", cap); return 0; }

    if (!qiku_read_prefixed(in, "KIND ", u->kind, sizeof(u->kind))) { strncpy(reason, "KIND_FEHLT", cap); return 0; }
    if (!qiku_read_prefixed(in, "RID ", u->rid, sizeof(u->rid))) { strncpy(reason, "RID_FEHLT", cap); return 0; }

    if (!qiku_read_prefixed(in, "SUBJECT ", value, sizeof(value))) { strncpy(reason, "SUBJECT_FEHLT", cap); return 0; }
    n = sscanf(value, "%255s %255s %255s %255s", u->subject_scheme, u->subject_id, u->subject_version, u->subject_state);
    if (n != 4) { strncpy(reason, "SUBJECT_UNGUELTIG", cap); return 0; }

    if (!qiku_read_prefixed(in, "INTENT ", u->intent, sizeof(u->intent))) { strncpy(reason, "INTENT_FEHLT", cap); return 0; }

    if (!qiku_read_prefixed(in, "AUTH ", value, sizeof(value))) { strncpy(reason, "AUTH_FEHLT", cap); return 0; }
    n = sscanf(value, "%255s %255s", u->auth_state, u->auth_id);
    if (n != 2) { strncpy(reason, "AUTH_UNGUELTIG", cap); return 0; }

    if (!qiku_read_prefixed(in, "EVID ", value, sizeof(value))) { strncpy(reason, "EVID_FEHLT", cap); return 0; }
    n = sscanf(value, "%255s %255s", u->evid_type, u->evid_digest);
    if (n != 2) { strncpy(reason, "EVID_UNGUELTIG", cap); return 0; }

    if (!qiku_read_prefixed(in, "STATE ", u->state, sizeof(u->state))) { strncpy(reason, "STATE_FEHLT", cap); return 0; }

    if (!qiku_read_prefixed(in, "EFFECT ", value, sizeof(value))) { strncpy(reason, "EFFECT_FEHLT", cap); return 0; }
    n = sscanf(value, "%255s %255s", u->effect_state, u->effect_id);
    if (n != 2) { strncpy(reason, "EFFECT_UNGUELTIG", cap); return 0; }

    if (!qiku_read_prefixed(in, "NEXT ", u->next_action, sizeof(u->next_action))) { strncpy(reason, "NEXT_FEHLT", cap); return 0; }
    if (!qiku_read_prefixed(in, "PROOF ", u->proof, sizeof(u->proof))) { strncpy(reason, "PROOF_FEHLT", cap); return 0; }
    if (!qiku_read_prefixed(in, "CAUSE ", u->cause, sizeof(u->cause))) { strncpy(reason, "CAUSE_FEHLT", cap); return 0; }

    if (fgets(line, sizeof(line), in) == NULL) { strncpy(reason, "END_FEHLT", cap); return 0; }
    qiku_chomp(line);
    if (strcmp(line, "END") != 0) { strncpy(reason, "END_UNGUELTIG", cap); return 0; }

    while (fgets(line, sizeof(line), in) != NULL) {
        qiku_chomp(line);
        if (line[0] != '\0') { strncpy(reason, "NACH_END_NICHT_LEER", cap); return 0; }
    }
    reason[0] = '\0';
    return 1;
}

static int qiku_semantic(const struct qiku_unit *u, int target_megast, char *reason, size_t cap)
{
    static const char *const kinds[] = {
        "OBSERVE", "DECIDE", "REQUEST", "AUTHORIZE", "ACT", "ACK", "HOLD", "NOOP", "ERROR"
    };
    static const char *const auths[] = {"BOUND", "MISSING", "STALE", "OUT_OF_SCOPE"};
    static const char *const effects[] = {
        "NONE", "REQUESTED", "EXECUTED", "OBSERVED", "ACKNOWLEDGED", "REJECTED", "UNKNOWN"
    };
    int productive;

    if (!qiku_allowed(u->kind, kinds, sizeof(kinds) / sizeof(kinds[0]))) {
        strncpy(reason, "KIND_UNBEKANNT", cap); return 0;
    }
    if (!qiku_allowed(u->auth_state, auths, sizeof(auths) / sizeof(auths[0]))) {
        strncpy(reason, "AUTH_STATUS_UNBEKANNT", cap); return 0;
    }
    if (!qiku_allowed(u->effect_state, effects, sizeof(effects) / sizeof(effects[0]))) {
        strncpy(reason, "EFFECT_STATUS_UNBEKANNT", cap); return 0;
    }
    if (strchr(u->intent, ' ') == NULL) { strncpy(reason, "INTENT_UNGUELTIG", cap); return 0; }
    if (!qiku_hex(u->evid_digest, 64U)) { strncpy(reason, "EVID_DIGEST_UNGUELTIG", cap); return 0; }
    if (!qiku_hex(u->proof, 64U)) { strncpy(reason, "PROOF_UNGUELTIG", cap); return 0; }
    if (strcmp(u->cause, u->rid) == 0) { strncpy(reason, "SELBSTKAUSALITAET", cap); return 0; }

    productive = qiku_productive_intent(u->intent);
    if (productive && strcmp(u->auth_state, "BOUND") != 0) {
        strncpy(reason, "PRODUKTIVE_ABSICHT_OHNE_AUTORITAET", cap); return 0;
    }
    if (productive && strcmp(u->state, "UNKNOWN") == 0) {
        strncpy(reason, "UNKNOWN_DARF_NICHT_WIRKEN", cap); return 0;
    }
    if (strcmp(u->auth_state, "BOUND") != 0 && !qiku_safe_nonbound_action(u->next_action)) {
        strncpy(reason, "UNBEFUGTE_FORTSETZUNG", cap); return 0;
    }
    if (strcmp(u->effect_state, "ACKNOWLEDGED") == 0 && strcmp(u->kind, "ACK") != 0) {
        strncpy(reason, "ACKNOWLEDGED_ERFORDERT_ACK", cap); return 0;
    }

    if (target_megast) {
        if (strcmp(u->subject_scheme, "repo") != 0 || strchr(u->subject_id, '/') == NULL) {
            strncpy(reason, "MEGAST_REPO_BINDUNG_ERFORDERLICH", cap); return 0;
        }
        if (!qiku_hex(u->subject_version, 40U) || !qiku_hex(u->subject_state, 40U)) {
            strncpy(reason, "MEGAST_EXACT_HEAD_TREE_ERFORDERLICH", cap); return 0;
        }
        if (!qiku_target_action(u->next_action)) {
            strncpy(reason, "MEGAST_AKTION_NICHT_UNTERSTUETZT", cap); return 0;
        }
    }

    reason[0] = '\0';
    return 1;
}

static void qiku_emit(const struct qiku_unit *u, int target_megast)
{
    printf("QIKVRT_UNIVERSAL_PLAN_V1\n");
    printf("DISTINCTION_KERNEL=1-0=1;1-1=0;x=y;z=0;x=1;y=1\n");
    printf("SEMANTIC_CHAIN=DISTINCTION>RELATION>BINDING_CONTEXT>AUTHORITY>CAUSAL_ORDER>PERMITTED_EFFECT_OR_FAIL_CLOSED>REOBSERVATION>PROOF\n");
    printf("TYPE_INVARIANTS=DISTINCTION!=RELATION;RELATION!=CAUSALITY;CAUSALITY!=SEQUENCE;ZERO_RESULT!=NO_EFFECT\n");
    printf("ZERO_RESULT_SEMANTICS=FORMAL_ONLY\n");
    printf("EMPIRICAL_QUANTUM_CAUSALITY=NOT_ESTABLISHED_BY_CALCULUS\n");
    printf("RID=%s\n", u->rid);
    printf("SUBJECT_SCHEME=%s\n", u->subject_scheme);
    printf("SUBJECT_ID=%s\n", u->subject_id);
    printf("SUBJECT_VERSION=%s\n", u->subject_version);
    printf("SUBJECT_STATE=%s\n", u->subject_state);
    if (strcmp(u->subject_scheme, "repo") == 0) {
        printf("BINDING=%s@%s:%s\n", u->subject_id, u->subject_version, u->subject_state);
    } else {
        printf("BINDING=%s:%s@%s:%s\n", u->subject_scheme, u->subject_id, u->subject_version, u->subject_state);
    }
    printf("INTENT=%s\n", u->intent);
    printf("AUTHORITY=AUTH=%s:%s\n", u->auth_state, u->auth_id);
    printf("EVIDENCE=%s:%s\n", u->evid_type, u->evid_digest);
    printf("STATE=%s\n", u->state);
    printf("EFFECT=%s:%s\n", u->effect_state, u->effect_id);
    printf("CAUSE=%s\n", u->cause);
    printf("NEXT_ACTION=%s\n", u->next_action);
    printf("PROOF=%s\n", u->proof);
    printf("TARGET_PROFILE=%s\n", target_megast ? "MEGAST_M68000_V1" : "UNIVERSAL_FRONTEND_V1");
    printf("ADMISSION=VALIDATED\n");
}

int main(int argc, char **argv)
{
    FILE *in;
    int target_megast;
    const char *path;
    struct qiku_unit unit;
    char reason[128];

    in = stdin;
    target_megast = 0;
    path = NULL;
    memset(&unit, 0, sizeof(unit));
    memset(reason, 0, sizeof(reason));

    if (argc == 2) {
        if (strcmp(argv[1], "--target-megast") == 0) target_megast = 1;
        else path = argv[1];
    } else if (argc == 3 && strcmp(argv[1], "--target-megast") == 0) {
        target_megast = 1;
        path = argv[2];
    } else if (argc > 1) {
        fprintf(stderr, "usage: %s [--target-megast] [source]\n", argv[0]);
        return 64;
    }

    if (path != NULL) {
        in = fopen(path, "r");
        if (in == NULL) { fprintf(stderr, "HOLD: DATEI_NICHT_LESBAR\n"); return 66; }
    }

    if (!qiku_parse(in, &unit, reason, sizeof(reason))) {
        if (in != stdin) fclose(in);
        fprintf(stderr, "HOLD: %s\n", reason);
        return 2;
    }
    if (in != stdin) fclose(in);

    if (!qiku_semantic(&unit, target_megast, reason, sizeof(reason))) {
        fprintf(stderr, "HOLD: %s\n", reason);
        return 2;
    }

    qiku_emit(&unit, target_megast);
    return 0;
}
