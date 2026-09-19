#include <stdio.h>
extern int qikvrt_core_invariant_m68000(int,int,int,int);
int main(void) {
    int t,b,i,r;
    for(t=0;t<=1;++t) for(b=0;b<=1;++b) for(i=0;i<=1;++i) for(r=0;r<=1;++r) {
        int s=qikvrt_core_invariant_m68000(t,b,i,r);
        printf("%d %d %d %d %d %d\n",t,b,i,r,s,s==2);
    }
    return 0;
}
