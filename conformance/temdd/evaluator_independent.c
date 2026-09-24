/*
 * TEMDD v1 independent C90 decision evaluator.
 * Reads the bounded canonical JSON profile from stdin and emits one canonical
 * JSON decision. It shares no evaluator implementation code with the Python
 * evaluator or the conformance runner.
 */
#include <stdio.h>
#include <string.h>

#define INPUT_CAP 8192
#define VALUE_CAP 256

static int find_bool(const char *json, const char *needle, int *value)
{
    const char *p = strstr(json, needle);
    if (p == NULL) return 0;
    p += strlen(needle);
    if (strncmp(p, "true", 4) == 0) {
        *value = 1;
        return 1;
    }
    if (strncmp(p, "false", 5) == 0) {
        *value = 0;
        return 1;
    }
    return 0;
}

static int find_string(const char *json, const char *needle, char *out, size_t cap)
{
    const char *p = strstr(json, needle);
    const char *end;
    size_t n;
    if (p == NULL) return 0;
    p += strlen(needle);
    end = strchr(p, '"');
    if (end == NULL) return 0;
    n = (size_t)(end - p);
    if (n == 0 || n >= cap) return 0;
    memcpy(out, p, n);
    out[n] = '\0';
    return 1;
}

static void emit(const char *result, const char *code)
{
    printf("{\"code\":\"%s\",\"result\":\"%s\"}\n", code, result);
}

int main(void)
{
    char json[INPUT_CAP + 1];
    char model[VALUE_CAP];
    char policy_version[VALUE_CAP];
    char evaluator_version[VALUE_CAP];
    char evidence_subject[VALUE_CAP];
    char subject[VALUE_CAP];
    size_t n;
    int valid, allow, fresh, replay, duplicate;

    n = fread(json, 1, INPUT_CAP, stdin);
    if (ferror(stdin) || (!feof(stdin) && n == INPUT_CAP)) {
        emit("FAIL", "MALFORMED_INPUT");
        return 0;
    }
    json[n] = '\0';

    if (!find_bool(json, "\"valid\":", &valid)
        || !find_bool(json, "\"allow\":", &allow)
        || !find_bool(json, "\"fresh\":", &fresh)
        || !find_bool(json, "\"replay\":", &replay)
        || !find_bool(json, "\"duplicate\":", &duplicate)
        || !find_string(json, "\"model_version\":\"", model, sizeof(model))
        || !find_string(json, "\"policy_version\":\"", policy_version, sizeof(policy_version))
        || !find_string(json, "\"evaluator_version\":\"", evaluator_version, sizeof(evaluator_version))
        || !find_string(json, "\"subject_digest\":\"", evidence_subject, sizeof(evidence_subject))
        || !find_string(json, "\"subject\":{\"digest\":\"", subject, sizeof(subject))) {
        emit("FAIL", "MALFORMED_INPUT");
        return 0;
    }

    if (strcmp(model, "1") != 0
        || strcmp(policy_version, "1") != 0
        || strcmp(evaluator_version, "1") != 0) {
        emit("HOLD_UNVERIFIED", "VERSION_MISMATCH");
    } else if (!valid) {
        emit("FAIL", "INVALID");
    } else if (strcmp(evidence_subject, subject) != 0) {
        emit("HOLD_UNVERIFIED", "SUBJECT_MISMATCH");
    } else if (!fresh) {
        emit("HOLD_UNVERIFIED", "INSUFFICIENT_EVIDENCE");
    } else if (replay) {
        emit("FAIL", "REPLAY");
    } else if (duplicate) {
        emit("FAIL", "DUPLICATE");
    } else if (!allow) {
        emit("FAIL", "POLICY_VIOLATION");
    } else {
        emit("PASS", "ACCEPT");
    }
    return 0;
}
