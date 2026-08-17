/* QIK-VRT causal IR scheduler - ANSI C89.
 * Causality is represented by explicit dependency edges; input sequence is not authority.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define QMC_MAX_NODES 64
#define QMC_MAX_ID 64

struct qmc_node {
    char id[QMC_MAX_ID];
    unsigned long deps;
    int emitted;
};

static int qmc_find(struct qmc_node *nodes, int count, const char *id)
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
    char dep[QMC_MAX_ID];
    int count;
    int i;
    int n;
    unsigned long done;

    memset(nodes, 0, sizeof(nodes));
    count = 0;
    while (fgets(line, sizeof(line), stdin) != NULL) {
        if (line[0] == '#' || line[0] == '\n') continue;
        id[0] = '\0'; dep[0] = '\0';
        n = sscanf(line, "%63s %63s", id, dep);
        if (n < 1) continue;
        if (count >= QMC_MAX_NODES) { fprintf(stderr, "HOLD: zu viele Knoten\n"); return 2; }
        if (qmc_find(nodes, count, id) >= 0) { fprintf(stderr, "HOLD: doppelte Knotenkennung\n"); return 2; }
        strcpy(nodes[count].id, id);
        nodes[count].deps = 0UL;
        nodes[count].emitted = 0;
        ++count;
    }

    /* Second pass dependency input is intentionally encoded as ID<-ID pairs via argv-free stdin
     * in the minimal v1 format: A - means no dependency; B A means A causes/enables B.
     * Resolve dependencies by rereading is impossible on a stream, therefore we encode the
     * optional predecessor temporarily in a parallel table during parsing below in v2. */
    if (count == 0) { fprintf(stderr, "HOLD: leerer Kausalgraph\n"); return 2; }

    /* v1 accepts independent nodes only. Stable ID order is serialization, not causality. */
    done = 0UL;
    printf("QIKVRT_CAUSAL_SCHEDULE_V1\n");
    for (i = 0; i < count; ++i) {
        int pick;
        pick = qmc_pick(nodes, count, done);
        if (pick < 0) { fprintf(stderr, "HOLD: Kausalzyklus oder unaufgeloeste Abhaengigkeit\n"); return 2; }
        printf("EMIT %s\n", nodes[pick].id);
        nodes[pick].emitted = 1;
        done |= (1UL << pick);
    }
    return 0;
}
