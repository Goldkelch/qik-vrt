/* Independent C90 carrier for QIK-VRT core invariant v1. */
#include <stdio.h>
typedef enum { EFFECT_NACK=0, EFFECT_ACK_CONTINUE=1, EFFECT_ACK_DONE=2, EFFECT_ACK_ISOLATE=3, EFFECT_ACK_BLOCK=4 } effect_state;
static effect_state decide(int t,int b,int i,int r) {
    if (!t) return EFFECT_NACK;
    if (b) return EFFECT_ACK_BLOCK;
    if (i) return EFFECT_ACK_ISOLATE;
    if (r) return EFFECT_ACK_DONE;
    return EFFECT_ACK_CONTINUE;
}
int main(void) {
    int t,b,i,r;
    for(t=0;t<=1;++t) for(b=0;b<=1;++b) for(i=0;i<=1;++i) for(r=0;r<=1;++r) {
        effect_state s=decide(t,b,i,r);
        printf("%d %d %d %d %d %d\n",t,b,i,r,(int)s,s==EFFECT_ACK_DONE);
    }
    return 0;
}
