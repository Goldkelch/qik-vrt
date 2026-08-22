/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
#include <stdio.h>
#include <stdlib.h>

typedef struct qikvrt_d3_machine {
    int d3;
    int active_ring;
    int result_collected;
    int persisted;
    int resources_released;
    int global_halt;
    int owner_interrupt;
} qikvrt_d3_machine;

static int activate(qikvrt_d3_machine *m, int ring)
{
    if (m == NULL || m->d3 != 0 || m->active_ring != 0 || ring < 1) {
        return 10;
    }
    m->d3 = 1;
    m->active_ring = ring;
    m->result_collected = 0;
    m->persisted = 0;
    m->resources_released = 0;
    return 0;
}

static int collect_result(qikvrt_d3_machine *m)
{
    if (m == NULL || m->d3 != 1 || m->active_ring < 1) {
        return 11;
    }
    m->result_collected = 1;
    return 0;
}

static int persist(qikvrt_d3_machine *m)
{
    if (m == NULL || m->d3 != 1 || !m->result_collected) {
        return 12;
    }
    m->persisted = 1;
    return 0;
}

static int release_resources(qikvrt_d3_machine *m)
{
    if (m == NULL || m->d3 != 1 || !m->persisted) {
        return 13;
    }
    m->resources_released = 1;
    return 0;
}

static int quiesce(qikvrt_d3_machine *m)
{
    if (m == NULL || m->d3 != 1 || !m->result_collected ||
        !m->persisted || !m->resources_released) {
        return 14;
    }
    m->d3 = 0;
    m->active_ring = 0;
    return 0;
}

static unsigned long ring_width_bits(int ring)
{
    if (ring == 1) {
        return 8UL;
    }
    if (ring == 2) {
        return 256UL;
    }
    if (ring == 3) {
        return 16777216UL;
    }
    return 0UL;
}

int main(void)
{
    qikvrt_d3_machine machine;
    int ring;
    int status;

    machine.d3 = 0;
    machine.active_ring = 0;
    machine.result_collected = 0;
    machine.persisted = 0;
    machine.resources_released = 1;
    machine.global_halt = 0;
    machine.owner_interrupt = 0;

    for (ring = 1; ring <= 3; ++ring) {
        if (ring_width_bits(ring) == 0UL) {
            return 20;
        }
        status = activate(&machine, ring);
        if (status != 0) return status;
        printf("ACTIVATE %d 0 1 %lu\n", ring, ring_width_bits(ring));
        status = collect_result(&machine);
        if (status != 0) return status;
        printf("COLLECT_RESULT %d 1 1 %lu\n", ring, ring_width_bits(ring));
        status = persist(&machine);
        if (status != 0) return status;
        printf("PERSIST %d 1 1 %lu\n", ring, ring_width_bits(ring));
        status = release_resources(&machine);
        if (status != 0) return status;
        printf("RELEASE_RESOURCES %d 1 1 %lu\n", ring, ring_width_bits(ring));
        status = quiesce(&machine);
        if (status != 0) return status;
        printf("QUIESCE %d 1 0 %lu\n", ring, ring_width_bits(ring));
    }

    printf("FINAL D3=%d GLOBAL_HALT=%d OWNER_INTERRUPT=%d BYTE_STATES=256\n",
           machine.d3, machine.global_halt, machine.owner_interrupt);
    return 0;
}
