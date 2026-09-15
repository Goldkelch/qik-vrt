#include "temdd_core.h"
int main(void) {
 int no[6]={1,1,1,1,1,0}; int yes[6]={1,1,1,1,1,1};
 if (temdd_transition(TEMDD_HOLD,TEMDD_EVENT_EVIDENCE)!=TEMDD_CONTINUE) return 1;
 if (temdd_transition(TEMDD_CONTINUE,TEMDD_EVENT_BLOCKER)!=TEMDD_SUCCESSOR_REQUIRED) return 2;
 if (temdd_done(no)) return 3;
 if (!temdd_done(yes)) return 4;
 return 0;
}
