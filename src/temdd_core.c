/* TEMDD v0.1 C90 deterministic semantic kernel. */
#include "temdd_core.h"
temdd_state temdd_transition(temdd_state state, temdd_event event) {
    if (state == TEMDD_DONE) return TEMDD_DONE;
    if (event == TEMDD_EVENT_BLOCKER) return TEMDD_SUCCESSOR_REQUIRED;
    if (event == TEMDD_EVENT_EVIDENCE) return TEMDD_CONTINUE;
    return TEMDD_HOLD;
}
int temdd_done(const int predicates[6]) {
    int i;
    if (!predicates) return 0;
    for (i = 0; i < 6; ++i) if (!predicates[i]) return 0;
    return 1;
}
