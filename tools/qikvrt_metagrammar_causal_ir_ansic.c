/* QIK-VRT causal IR scheduler - ANSI C89.
 * Explicit dependency edges define causality. Input sequence has no causal authority.
 */
#include <stdio.h>
#include <string.h>

#define QMC_MAX_NODES 32
#define QMC_MAX_ID 64

struct qmc_node {
    char id[QMC_MAX_ID];
    char predecessor[QMC_MAX_ID];
    unsigned long deps;
    int emitted;
};

static int qmc_find(const struct qmc_node *nodes, int count, const char *id)
{
    int i;
    for (i = 0; i < count; ++i) if (strcmp(nodes[i].id, id) == 0) return i;
    return -1;
}

static int qmc_ready(const struct qmc_node *n, unsigned long done)
{
    return (n->deps & ~done) == 0UL;
}

static int qmc_pick(struct qmc_node *nodes, int count, unsigned long done)
{
    int i;
    int best;
    best = -1;
    for (i = 0; i < count; ++i) {
        if (!nodes[i].emitted && qmc_ready(&nodes[i], done)) {
            if (best < 0 || strcmp(nodes[i].id, nodes[best].id) < 0) best = i;
        }
    }
    return best;
}

int main(void)
{
    struct qmc_node nodes[QMC_MAX_NODES];
    char line[512];
    char id[QMC_MAX_ID];
    char pred[QMC_MAX_ID];
    int count;
    int i;
    int n;
    unsigned long done;

    memset(nodes, 0, sizeof(nodes));
    count = 0;
    while (fgets(line, sizeof(line), stdin) != NULL) {
        if (line[0] == '#' || line[0] == '\n') continue;
        id[0] = '\0'; pred[0] = '\0';
        n = sscanf(line, "%63s %63s", id, pred);
        if (n < 1) continue;
        if (count >= QMC_MAX_NODES) { fprintf(stderr, "HOLD: zu viele Knoten\n"); return 2; }
        if (qmc_find(nodes, count, id) >= 0) { fprintf(stderr, "HOLD: doppelte Knotenkennung\n"); return 2; }
        strcpy(nodes[count].id, id);
        if (n == 2 && strcmp(pred, "-") != 0) strcpy(nodes[count].predecessor, pred);
        ++count;
    }
    if (count == 0) { fprintf(stderr, "HOLD: leerer Kausalgraph\n"); return 2; }

    for (i = 0; i < count; ++i) {
        int p;
        nodes[i].deps = 0UL;
        nodes[i].emitted = 0;
        if (nodes[i].predecessor[0] != '\0') {
            p = qmc_find(nodes, count, nodes[i].predecessor);
            if (p < 0) { fprintf(stderr, "HOLD: unbekannte Ursache %s\n", nodes[i].predecessor); return 2; }
            nodes[i].deps |= (1UL << p);
        }
    }

    done = 0UL;
    printf("QIKVRT_CAUSAL_SCHEDULE_V1\n");
    for (i = 0; i < count; ++i) {
        int pick;
        pick = qmc_pick(nodes, count, done);
        if (pick < 0) { fprintf(stderr, "HOLD: Kausalzyklus\n"); return 2; }
        printf("EMIT %s\n", nodes[pick].id);
        nodes[pick].emitted = 1;
        done |= (1UL << pick);
    }
    return 0;
}
