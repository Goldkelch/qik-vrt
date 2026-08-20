/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * QIK-VRT MLP Atari/TOS front end, ANSI C89 source.
 *
 * The program creates only a REQUESTED host handoff record.  It does not
 * launch Firefox and it does not claim an external effect.
 */
#include <stdio.h>
#include <string.h>

extern long gemdos();
extern long mlp_request_firefox();

#define GEMDOS_CCONWS 9
#define GEMDOS_FCREATE 60
#define GEMDOS_FWRITE 64
#define GEMDOS_FCLOSE 62
#define GEMDOS_PTERM 76

static const char request_body[] =
    "QIKMLP1\r\n"
    "PROGRAM MLP\r\n"
    "ACTION OPEN_FIREFOX\r\n"
    "STATE REQUESTED\r\n"
    "AUTHORITY MISSING\r\n"
    "EFFECT REQUESTED\r\n"
    "END\r\n";

static int write_request(void)
{
    long handle;
    long wrote;
    handle = gemdos(GEMDOS_FCREATE, "C:\\MLP.OPEN", 0);
    if (handle < 0L)
        return 1;
    wrote = gemdos(GEMDOS_FWRITE, (int)handle,
                   (long)strlen(request_body), request_body);
    gemdos(GEMDOS_FCLOSE, (int)handle);
    if (wrote != (long)strlen(request_body))
        return 1;
    return 0;
}

int main(void)
{
    long decision;
    gemdos(GEMDOS_CCONWS,
        "\033E"
        "MLP - Machine Learning Program\r\n"
        "QIK-VRT / Tested Event Model Driven Development\r\n\r\n"
        "Preparing bounded Firefox EFFECT_ACK terminal request...\r\n");

    decision = mlp_request_firefox();
    if ((decision & 0xffffL) != 3L) {
        gemdos(GEMDOS_CCONWS, "HOLD: M68000 decision mismatch.\r\n");
        gemdos(GEMDOS_PTERM, 1);
        return 1;
    }

    if (write_request() != 0) {
        gemdos(GEMDOS_CCONWS, "HOLD: cannot persist C:\\MLP.OPEN.\r\n");
        gemdos(GEMDOS_PTERM, 1);
        return 1;
    }

    gemdos(GEMDOS_CCONWS,
        "REQUESTED. Waiting for host authority and reobservation.\r\n"
        "REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED\r\n");
    gemdos(GEMDOS_PTERM, 0);
    return 0;
}
