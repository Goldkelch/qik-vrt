/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann.
 *
 * Bounded QIK-VRT IP bootstrap decision kernel.
 * This is strict ANSI C90 and is cross-compiled to MC68000 machine bytes.
 * It is NOT a complete POSIX operating system or TCP/IP stack.
 */
#ifdef QIKVRT_IP_BOOTSTRAP_SELFTEST
#include <stdio.h>
#endif

#define QIKVRT_D0_NOOP              0
#define QIKVRT_D0_HOLD              1
#define QIKVRT_D0_REOBSERVE         2
#define QIKVRT_D0_REQUEST_AUTHORITY 3

#define QIKVRT_SERVICE_HTTP_PROXY   (1UL << 0)
#define QIKVRT_SERVICE_SMTP         (1UL << 1)
#define QIKVRT_SERVICE_DNS          (1UL << 2)
#define QIKVRT_SERVICE_SNMP         (1UL << 3)
#define QIKVRT_SERVICE_SSH          (1UL << 4)
#define QIKVRT_SERVICE_SQL          (1UL << 5)
#define QIKVRT_SERVICE_EFFECT_ACK   (1UL << 6)
#define QIKVRT_SERVICE_FIREFOX      (1UL << 7)
#define QIKVRT_SERVICE_TCP_MESH     (1UL << 8)
#define QIKVRT_SERVICE_MIRROR       (1UL << 9)

#define QIKVRT_FLAG_MIRROR_EQUAL              (1UL << 0)
#define QIKVRT_FLAG_EXTERNAL_DEPLOY_AUTHORITY (1UL << 1)

#define QIKVRT_LOCAL_REQUIRED \
    (QIKVRT_SERVICE_HTTP_PROXY | QIKVRT_SERVICE_SMTP | QIKVRT_SERVICE_DNS | \
     QIKVRT_SERVICE_SNMP | QIKVRT_SERVICE_SSH | QIKVRT_SERVICE_SQL | \
     QIKVRT_SERVICE_EFFECT_ACK | QIKVRT_SERVICE_FIREFOX | \
     QIKVRT_SERVICE_TCP_MESH)

int qikvrt_boot_decide(unsigned long service_mask, unsigned long flags)
{
    if ((service_mask & QIKVRT_LOCAL_REQUIRED) != QIKVRT_LOCAL_REQUIRED) {
        return QIKVRT_D0_HOLD;
    }
    if ((service_mask & QIKVRT_SERVICE_MIRROR) == 0UL ||
        (flags & QIKVRT_FLAG_MIRROR_EQUAL) == 0UL) {
        return QIKVRT_D0_REOBSERVE;
    }
    if ((flags & QIKVRT_FLAG_EXTERNAL_DEPLOY_AUTHORITY) == 0UL) {
        return QIKVRT_D0_REQUEST_AUTHORITY;
    }
    return QIKVRT_D0_NOOP;
}

unsigned long qikvrt_boot_word(unsigned long service_mask, unsigned long flags)
{
    return ((service_mask & 0xffffUL) << 16) |
           ((flags & 0xffUL) << 8) |
           (unsigned long)qikvrt_boot_decide(service_mask, flags);
}

#ifdef QIKVRT_IP_BOOTSTRAP_SELFTEST
int main(void)
{
    unsigned long local_mask;
    unsigned long full_mask;
    local_mask = QIKVRT_LOCAL_REQUIRED;
    full_mask = local_mask | QIKVRT_SERVICE_MIRROR;

    if (qikvrt_boot_decide(local_mask & ~QIKVRT_SERVICE_SQL, 0UL) != QIKVRT_D0_HOLD) {
        return 11;
    }
    if (qikvrt_boot_decide(local_mask, 0UL) != QIKVRT_D0_REOBSERVE) {
        return 12;
    }
    if (qikvrt_boot_decide(full_mask, QIKVRT_FLAG_MIRROR_EQUAL) !=
        QIKVRT_D0_REQUEST_AUTHORITY) {
        return 13;
    }
    if (qikvrt_boot_decide(
            full_mask,
            QIKVRT_FLAG_MIRROR_EQUAL | QIKVRT_FLAG_EXTERNAL_DEPLOY_AUTHORITY) !=
        QIKVRT_D0_NOOP) {
        return 14;
    }
    puts("QIKVRT_C90_IP_BOOTSTRAP_SELFTEST=PASS");
    return 0;
}
#endif
