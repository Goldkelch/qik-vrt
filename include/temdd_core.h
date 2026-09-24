#ifndef QIKVRT_TEMDD_CORE_H
#define QIKVRT_TEMDD_CORE_H
typedef enum { TEMDD_HOLD=0, TEMDD_CONTINUE=1, TEMDD_SUCCESSOR_REQUIRED=2, TEMDD_DONE=3 } temdd_state;
typedef enum { TEMDD_EVENT_UNKNOWN=0, TEMDD_EVENT_EVIDENCE=1, TEMDD_EVENT_BLOCKER=2 } temdd_event;
temdd_state temdd_transition(temdd_state state, temdd_event event);
int temdd_done(const int predicates[6]);
#endif
