#include <stdio.h>

typedef struct {
    int repository_processing;
    int durable_readback;
    int chat_trigger;
    int observation;
    int continuation;
    int fresh_validation;
} qikvrt_state;

static int closed(qikvrt_state s)
{
    return s.repository_processing && s.durable_readback && s.chat_trigger &&
           s.observation && s.continuation && s.fresh_validation;
}

static const char *status(qikvrt_state s)
{
    return closed(s) ? "CLOSED" : "HOLD_UNVERIFIED";
}

int main(void)
{
    qikvrt_state current = {1, 1, 0, 0, 0, 0};
    qikvrt_state witness = {1, 1, 1, 1, 1, 1};
    if (closed(current)) return 1;
    if (!closed(witness)) return 2;
    puts(status(current));
    puts(status(witness));
    return 0;
}
