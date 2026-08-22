/* QIK-VRT validated-plan to M68000 capsule IR lowerer - ANSI C89.
 *
 * ABI v1 (default): D0 = decision code; RTS.
 * ABI v2 (--semantic-witness-v2): D1 semantic flags, D2 effect lifecycle,
 * D0 decision code; RTS.
 * ABI v3 (--causal-time-v3): preserves ABI-v2 registers and additionally:
 *   D3 = causal-order witness
 *        0 NO_EXPLICIT_PREDECESSOR
 *        1 EXPLICIT_PREDECESSOR_BOUND
 *
 * D3 is deliberately not a wall-clock timestamp, elapsed duration, quality,
 * success, authority or proof of physical causality. It records only whether
 * the validated plan carries an explicit causal predecessor. Thus:
 *   CAUSALITY != SEQUENCE
 *   TIMESTAMP_ORDER != CAUSAL_ORDER
 *   LATER != CAUSED_BY
 *
 * All profiles remain nonproductive and preserve the four-action D0 ABI.
 */
#include <stdio.h>
#include <string.h>

#define QIK_LINE 1024
#define QIK_TOKEN 256

static void chomp(char *s)
{
    size_t n;
    n = strlen(s);
    while (n > 0U && (s[n - 1U] == '\n' || s[n - 1U] == '\r')) { s[n - 1U] = '\0'; --n; }
}

static int copy_value(char *dst, size_t cap, const char *src)
{
    size_t n;
    n = strlen(src);
    if (n == 0U || n + 1U > cap) return 0;
    memcpy(dst, src, n + 1U);
    return 1;
}

static int decision_code(const char *next)
{
    if (strcmp(next, "NOOP") == 0) return 0;
    if (strcmp(next, "HOLD") == 0) return 1;
    if (strcmp(next, "REOBSERVE") == 0) return 2;
    if (strcmp(next, "REQUEST_AUTHORITY") == 0) return 3;
    return -1;
}

static int effect_code(const char *effect)
{
    if (strcmp(effect, "NONE") == 0) return 0;
    if (strcmp(effect, "REQUESTED") == 0) return 1;
    if (strcmp(effect, "EXECUTED") == 0) return 2;
    if (strcmp(effect, "OBSERVED") == 0) return 3;
    if (strcmp(effect, "ACKNOWLEDGED") == 0) return 4;
    if (strcmp(effect, "REJECTED") == 0) return 5;
    if (strcmp(effect, "UNKNOWN") == 0) return 6;
    return -1;
}

int main(int argc, char **argv)
{
    char line[QIK_LINE], next[QIK_TOKEN], authority[QIK_TOKEN], effect[QIK_TOKEN], cause[QIK_TOKEN];
    int admitted, found_next, found_kernel, found_types, found_authority, found_effect, found_cause;
    int profile, code;
    static const char kernel[] = "DISTINCTION_KERNEL=1-0=1;1-1=0;x=y;z=0;x=1;y=1";
    static const char types[] = "TYPE_INVARIANTS=DISTINCTION!=RELATION;RELATION!=CAUSALITY;CAUSALITY!=SEQUENCE;ZERO_RESULT!=NO_EFFECT";

    profile = 1;
    if (argc == 2 && strcmp(argv[1], "--semantic-witness-v2") == 0) profile = 2;
    else if (argc == 2 && strcmp(argv[1], "--causal-time-v3") == 0) profile = 3;
    else if (argc != 1) { fprintf(stderr, "usage: %s [--semantic-witness-v2|--causal-time-v3]\n", argv[0]); return 64; }

    next[0]=authority[0]=effect[0]=cause[0]='\0';
    admitted=found_next=found_kernel=found_types=found_authority=found_effect=found_cause=0;

    while (fgets(line, sizeof(line), stdin) != NULL) {
        chomp(line);
        if (strncmp(line, "NEXT_ACTION=", 12U) == 0) {
            if (!copy_value(next,sizeof(next),line+12)) { fprintf(stderr,"HOLD: NEXT_ACTION_UNGUELTIG\n"); return 2; }
            found_next=1;
        } else if (strcmp(line,kernel)==0) found_kernel=1;
        else if (strcmp(line,types)==0) found_types=1;
        else if (strncmp(line,"AUTHORITY=AUTH=",15U)==0) {
            const char *p=line+15; size_t n=strcspn(p,":");
            if(n==0U||n+1U>sizeof(authority)||p[n]!=':'){fprintf(stderr,"HOLD: AUTHORITY_UNGUELTIG\n");return 2;}
            memcpy(authority,p,n); authority[n]='\0'; found_authority=1;
        } else if (strncmp(line,"EFFECT=",7U)==0) {
            const char *p=line+7; size_t n=strcspn(p,":");
            if(n==0U||n+1U>sizeof(effect)||p[n]!=':'){fprintf(stderr,"HOLD: EFFECT_UNGUELTIG\n");return 2;}
            memcpy(effect,p,n); effect[n]='\0'; found_effect=1;
        } else if (strncmp(line,"CAUSE=",6U)==0) {
            if(!copy_value(cause,sizeof(cause),line+6)){fprintf(stderr,"HOLD: CAUSE_UNGUELTIG\n");return 2;}
            found_cause=1;
        } else if (strcmp(line,"ADMISSION=VALIDATED")==0) admitted=1;
    }

    if(!found_next||!admitted){fprintf(stderr,"HOLD: PLAN_NICHT_VALIDIERT\n");return 2;}
    code=decision_code(next);
    if(code<0){fprintf(stderr,"HOLD: M68000_ABI_AKTION_NICHT_UNTERSTUETZT\n");return 2;}

    if(profile>=2){
        int flags,ecode;
        if(!found_kernel||!found_types||!found_authority||!found_effect||!found_cause){fprintf(stderr,"HOLD: SEMANTIC_WITNESS_UNVOLLSTAENDIG\n");return 2;}
        ecode=effect_code(effect);
        if(ecode<0){fprintf(stderr,"HOLD: EFFECT_STATUS_UNBEKANNT\n");return 2;}
        flags=1|2;
        if(strcmp(authority,"BOUND")==0) flags|=4;
        if(strcmp(cause,"-")!=0) flags|=8;
        printf("MOVEQ D1 %d\n",flags);
        printf("MOVEQ D2 %d\n",ecode);
        if(profile>=3) printf("MOVEQ D3 %d\n",strcmp(cause,"-")==0?0:1);
    }

    printf("MOVEQ D0 %d\n",code);
    printf("RTS\n");
    return 0;
}
