/* QIK-VRT MLP M68000 semantic request kernel.
 *
 * Pure 68000 assembly leaf routine.  It does not execute an external effect.
 * It reports the initial OPEN_FIREFOX request as:
 *   D0=3 REQUEST_AUTHORITY
 *   D1=3 semantic kernel + type-boundary witnesses, authority not yet bound
 *   D2=1 REQUESTED
 *
 * Exact instruction bytes:
 *   MOVEQ #3,D1  72 03
 *   MOVEQ #1,D2  74 01
 *   MOVEQ #3,D0  70 03
 *   RTS           4E 75
 */

        .text
        .even
        .globl  _mlp_request_firefox
_mlp_request_firefox:
        moveq   #3,d1
        moveq   #1,d2
        moveq   #3,d0
        rts
