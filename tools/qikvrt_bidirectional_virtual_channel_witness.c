/*
 * SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann.
 *
 * qikvrt_bidirectional_virtual_channel_witness.c
 *
 * Dependency-free ISO C90 witness for a bidirectional channel between
 * virtual time addresses.  All actual computation remains strictly ordered
 * by an increasing host clock.  The program deliberately makes no claim of
 * physical backward signalling.
 */

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DEFAULT_CHUNK_SIZE 17U
#define HOST_EVENT_CAPACITY 16U
#define DIGEST_MODULUS 65521UL
#define VIRTUAL_PAST 15L
#define VIRTUAL_PRESENT 30L

typedef enum HostEventKindTag {
    HOST_SOURCE_EVENT = 0,
    HOST_REQUEST_CREATE = 1,
    HOST_REQUEST_TRANSPORT_ACK = 2,
    HOST_REPLAY = 3,
    HOST_RESPONSE_CREATE = 4,
    HOST_RESPONSE_TRANSPORT_ACK = 5,
    HOST_EFFECT_ACK_COMMIT = 6
} HostEventKind;

typedef struct PayloadTag {
    unsigned char *bytes;
    size_t length;
    unsigned long digest;
} Payload;

typedef struct TransportStatsTag {
    size_t chunk_count;
    size_t delivered_bytes;
    int exact;
} TransportStats;

typedef struct HostEventTag {
    unsigned long sequence;
    HostEventKind kind;
    long from_virtual;
    long to_virtual;
} HostEvent;

typedef struct HostLogTag {
    HostEvent events[HOST_EVENT_CAPACITY];
    size_t count;
    unsigned long clock;
} HostLog;

typedef struct ChannelRunTag {
    HostLog host;
    Payload request;
    Payload request_at_past;
    Payload response_a;
    Payload response_b;
    Payload response_at_present;
    TransportStats request_transport;
    TransportStats response_transport;
    unsigned long source_digest_before;
    unsigned long source_digest_after;
    int source_immutable;
    int replay_deterministic;
    int response_is_bound_to_request;
    int host_order_strict;
    int virtual_cycle_closed;
} ChannelRun;

typedef struct CheckReportTag {
    int violations;
} CheckReport;

static unsigned long digest_bytes(const unsigned char *bytes, size_t length)
{
    unsigned long hash;
    size_t remaining;
    size_t index;

    hash = 17UL;
    for (index = 0U; index < length; index++) {
        hash = (hash * 257UL + (unsigned long)bytes[index] + 1UL)
            % DIGEST_MODULUS;
    }
    remaining = length;
    do {
        hash = (hash * 257UL + (unsigned long)(remaining % 256U) + 1UL)
            % DIGEST_MODULUS;
        remaining /= 256U;
    } while (remaining != 0U);
    return hash;
}

static void payload_zero(Payload *payload)
{
    payload->bytes = (unsigned char *)0;
    payload->length = 0U;
    payload->digest = digest_bytes((const unsigned char *)"", 0U);
}

static void payload_release(Payload *payload)
{
    if (payload->bytes != (unsigned char *)0) {
        free(payload->bytes);
    }
    payload_zero(payload);
}

static int payload_allocate(Payload *payload, size_t length)
{
    size_t allocation_size;

    payload_zero(payload);
    allocation_size = length == 0U ? 1U : length;
    payload->bytes = (unsigned char *)malloc(allocation_size);
    if (payload->bytes == (unsigned char *)0) {
        return 0;
    }
    payload->length = length;
    return 1;
}

static int payload_generate(Payload *payload, size_t length,
                            unsigned long seed)
{
    size_t index;

    if (!payload_allocate(payload, length)) {
        return 0;
    }
    for (index = 0U; index < length; index++) {
        payload->bytes[index] = (unsigned char)
            ((seed + (unsigned long)(index * 131U) +
              (unsigned long)(index / 7U)) % 256UL);
    }
    payload->digest = digest_bytes(payload->bytes, payload->length);
    return 1;
}

static int payload_equal(const Payload *left, const Payload *right)
{
    if (left->length != right->length || left->digest != right->digest) {
        return 0;
    }
    if (left->length == 0U) {
        return 1;
    }
    return memcmp(left->bytes, right->bytes, left->length) == 0;
}

static int exact_chunk_transport(const Payload *source, Payload *destination,
                                 size_t chunk_size, int omit_second_chunk,
                                 TransportStats *stats)
{
    size_t offset;
    size_t remaining;
    size_t amount;
    size_t chunk_index;

    stats->chunk_count = 0U;
    stats->delivered_bytes = 0U;
    stats->exact = 0;
    if (chunk_size == 0U || !payload_allocate(destination, source->length)) {
        return 0;
    }
    if (source->length > 0U) {
        (void)memset(destination->bytes, 0, source->length);
    }
    offset = 0U;
    chunk_index = 0U;
    while (offset < source->length) {
        remaining = source->length - offset;
        amount = remaining < chunk_size ? remaining : chunk_size;
        if (!(omit_second_chunk && chunk_index == 1U)) {
            (void)memcpy(destination->bytes + offset,
                         source->bytes + offset, amount);
            stats->delivered_bytes += amount;
        }
        offset += amount;
        chunk_index++;
        stats->chunk_count++;
    }
    destination->digest = digest_bytes(destination->bytes,
                                       destination->length);
    stats->exact = stats->delivered_bytes == source->length
        && payload_equal(source, destination);
    return stats->exact;
}

static int derive_response(const Payload *request, Payload *response)
{
    size_t index;

    if (request->length == (size_t)-1) {
        return 0;
    }
    if (!payload_allocate(response, request->length + 1U)) {
        return 0;
    }
    response->bytes[0] = (unsigned char)0xA5U;
    for (index = 0U; index < request->length; index++) {
        response->bytes[index + 1U] =
            request->bytes[request->length - index - 1U];
    }
    response->digest = digest_bytes(response->bytes, response->length);
    return 1;
}

static int response_matches_request(const Payload *request,
                                    const Payload *response)
{
    size_t index;

    if (response->length != request->length + 1U
            || response->bytes[0] != (unsigned char)0xA5U) {
        return 0;
    }
    for (index = 0U; index < request->length; index++) {
        if (response->bytes[index + 1U]
                != request->bytes[request->length - index - 1U]) {
            return 0;
        }
    }
    return response->digest ==
        digest_bytes(response->bytes, response->length);
}

static int host_append(HostLog *host, HostEventKind kind,
                       long from_virtual, long to_virtual)
{
    HostEvent *event;

    if (host->count >= (size_t)HOST_EVENT_CAPACITY) {
        return 0;
    }
    host->clock++;
    event = &host->events[host->count];
    event->sequence = host->clock;
    event->kind = kind;
    event->from_virtual = from_virtual;
    event->to_virtual = to_virtual;
    host->count++;
    return 1;
}

static int host_is_strict(const HostLog *host)
{
    size_t index;

    for (index = 0U; index < host->count; index++) {
        if (host->events[index].sequence != (unsigned long)index + 1UL) {
            return 0;
        }
    }
    return host->clock == (unsigned long)host->count;
}

static const char *host_kind_name(HostEventKind kind)
{
    switch (kind) {
    case HOST_SOURCE_EVENT:
        return "SOURCE_EVENT";
    case HOST_REQUEST_CREATE:
        return "REQUEST_CREATE";
    case HOST_REQUEST_TRANSPORT_ACK:
        return "REQUEST_TRANSPORT_ACK";
    case HOST_REPLAY:
        return "DETERMINISTIC_REPLAY";
    case HOST_RESPONSE_CREATE:
        return "RESPONSE_CREATE";
    case HOST_RESPONSE_TRANSPORT_ACK:
        return "RESPONSE_TRANSPORT_ACK";
    case HOST_EFFECT_ACK_COMMIT:
        return "DEMO_EFFECT_ACK_COMMIT";
    default:
        return "UNKNOWN";
    }
}

static void channel_release(ChannelRun *run)
{
    payload_release(&run->request);
    payload_release(&run->request_at_past);
    payload_release(&run->response_a);
    payload_release(&run->response_b);
    payload_release(&run->response_at_present);
}

static int construct_channel(ChannelRun *run, size_t request_length,
                             unsigned long seed)
{
    static const unsigned char source_snapshot[] =
        "immutable-source-events:v10,v20,v30";

    (void)memset(run, 0, sizeof(*run));
    payload_zero(&run->request);
    payload_zero(&run->request_at_past);
    payload_zero(&run->response_a);
    payload_zero(&run->response_b);
    payload_zero(&run->response_at_present);
    if (!host_append(&run->host, HOST_SOURCE_EVENT, 10L, 10L)
            || !host_append(&run->host, HOST_SOURCE_EVENT, 20L, 20L)
            || !host_append(&run->host, HOST_SOURCE_EVENT, 30L, 30L)) {
        return 0;
    }
    run->source_digest_before = digest_bytes(source_snapshot,
        sizeof(source_snapshot) - 1U);
    if (!payload_generate(&run->request, request_length, seed)
            || !host_append(&run->host, HOST_REQUEST_CREATE,
                            VIRTUAL_PRESENT, VIRTUAL_PAST)
            || !exact_chunk_transport(&run->request, &run->request_at_past,
                                      (size_t)DEFAULT_CHUNK_SIZE, 0,
                                      &run->request_transport)
            || !host_append(&run->host, HOST_REQUEST_TRANSPORT_ACK,
                            VIRTUAL_PRESENT, VIRTUAL_PAST)
            || !host_append(&run->host, HOST_REPLAY,
                            VIRTUAL_PAST, VIRTUAL_PAST)
            || !derive_response(&run->request_at_past, &run->response_a)
            || !derive_response(&run->request_at_past, &run->response_b)
            || !host_append(&run->host, HOST_RESPONSE_CREATE,
                            VIRTUAL_PAST, VIRTUAL_PRESENT)
            || !exact_chunk_transport(&run->response_a,
                                      &run->response_at_present,
                                      (size_t)DEFAULT_CHUNK_SIZE, 0,
                                      &run->response_transport)
            || !host_append(&run->host, HOST_RESPONSE_TRANSPORT_ACK,
                            VIRTUAL_PAST, VIRTUAL_PRESENT)
            || !host_append(&run->host, HOST_EFFECT_ACK_COMMIT,
                            VIRTUAL_PAST, VIRTUAL_PRESENT)) {
        channel_release(run);
        return 0;
    }
    run->source_digest_after = digest_bytes(source_snapshot,
        sizeof(source_snapshot) - 1U);
    run->source_immutable =
        run->source_digest_before == run->source_digest_after;
    run->replay_deterministic =
        payload_equal(&run->response_a, &run->response_b);
    run->response_is_bound_to_request =
        response_matches_request(&run->request_at_past,
                                 &run->response_at_present);
    run->host_order_strict = host_is_strict(&run->host);
    run->virtual_cycle_closed =
        run->host.events[3U].from_virtual == VIRTUAL_PRESENT
        && run->host.events[3U].to_virtual == VIRTUAL_PAST
        && run->host.events[6U].from_virtual == VIRTUAL_PAST
        && run->host.events[6U].to_virtual == VIRTUAL_PRESENT;
    return 1;
}

static void check_condition(CheckReport *report, int condition,
                            const char *description)
{
    if (condition) {
        (void)printf("  [ok] %s\n", description);
    } else {
        (void)printf("  [VIOLATION] %s\n", description);
        report->violations++;
    }
}

static int verify_missing_chunk_rejected(void)
{
    Payload source;
    Payload received;
    TransportStats stats;
    int accepted;

    payload_zero(&source);
    payload_zero(&received);
    if (!payload_generate(&source, 64U, 77UL)) {
        return 0;
    }
    accepted = exact_chunk_transport(&source, &received,
                                     (size_t)DEFAULT_CHUNK_SIZE, 1, &stats);
    payload_release(&source);
    payload_release(&received);
    return !accepted && !stats.exact && stats.delivered_bytes < 64U;
}

static int verify_length_sweep(size_t *cases_checked)
{
    static const size_t lengths[] = {
        0U, 1U, 16U, 17U, 18U, 31U, 255U, 256U, 257U, 4096U
    };
    size_t index;
    ChannelRun run;
    int valid;

    *cases_checked = 0U;
    valid = 1;
    for (index = 0U; index < sizeof(lengths) / sizeof(lengths[0]); index++) {
        if (!construct_channel(&run, lengths[index],
                               (unsigned long)(101U + index))
                || !run.request_transport.exact
                || !run.response_transport.exact
                || !run.source_immutable
                || !run.replay_deterministic
                || !run.response_is_bound_to_request
                || !run.host_order_strict
                || !run.virtual_cycle_closed) {
            valid = 0;
            channel_release(&run);
            break;
        }
        (*cases_checked)++;
        channel_release(&run);
    }
    return valid && *cases_checked == sizeof(lengths) / sizeof(lengths[0]);
}

static void print_host_trace(const HostLog *host)
{
    size_t index;
    const HostEvent *event;

    (void)printf("HOST ORDER (all actual work is forward):\n");
    for (index = 0U; index < host->count; index++) {
        event = &host->events[index];
        (void)printf("  h=%lu  %-24s virtual=%ld -> %ld\n",
                     event->sequence, host_kind_name(event->kind),
                     event->from_virtual, event->to_virtual);
    }
}

int main(void)
{
    ChannelRun run;
    CheckReport report;
    size_t sweep_cases;
    int sweep_valid;
    int loss_rejected;

    report.violations = 0;
    (void)printf("QIK-VRT ISO C90 bidirectional virtual-channel witness\n\n");
    if (!construct_channel(&run, 257U, 42UL)) {
        (void)fprintf(stderr, "channel construction failed\n");
        return EXIT_FAILURE;
    }
    sweep_valid = verify_length_sweep(&sweep_cases);
    loss_rejected = verify_missing_chunk_rejected();
    print_host_trace(&run.host);
    (void)printf("\nVIRTUAL CHANNEL:\n");
    (void)printf("  request: v=%ld -> v=%ld, bytes=%lu, chunks=%lu\n",
                 VIRTUAL_PRESENT, VIRTUAL_PAST,
                 (unsigned long)run.request.length,
                 (unsigned long)run.request_transport.chunk_count);
    (void)printf("  response: v=%ld -> v=%ld, bytes=%lu, chunks=%lu\n",
                 VIRTUAL_PAST, VIRTUAL_PRESENT,
                 (unsigned long)run.response_at_present.length,
                 (unsigned long)run.response_transport.chunk_count);
    (void)printf("\nRUNTIME INVARIANTS:\n");
    check_condition(&report, run.host_order_strict,
                    "host sequence is strict and contiguous");
    check_condition(&report, run.virtual_cycle_closed,
                    "virtual request and response close both directions");
    check_condition(&report, run.request_transport.exact,
                    "request is reassembled byte-exactly at the past address");
    check_condition(&report, run.response_transport.exact,
                    "response is reassembled byte-exactly at the present address");
    check_condition(&report, run.replay_deterministic,
                    "two independent replays produce the same response");
    check_condition(&report, run.response_is_bound_to_request,
                    "returned response is a total deterministic transform of request");
    check_condition(&report, run.source_immutable,
                    "the source snapshot remains unchanged");
    check_condition(&report, sweep_valid && sweep_cases == 10U,
                    "boundary-length sweep passes in both directions");
    check_condition(&report, loss_rejected,
                    "a deliberately missing chunk is rejected");
    (void)printf("\nEVIDENCE:\n");
    (void)printf("  source digest before/after: %lu / %lu\n",
                 run.source_digest_before, run.source_digest_after);
    (void)printf("  request digest sent/received: %lu / %lu\n",
                 run.request.digest, run.request_at_past.digest);
    (void)printf("  response digest replay-A/replay-B/received: %lu / %lu / %lu\n",
                 run.response_a.digest, run.response_b.digest,
                 run.response_at_present.digest);
    (void)printf("  tested payload lengths: 0,1,16,17,18,31,255,256,257,4096\n");
    channel_release(&run);
    if (report.violations != 0) {
        (void)printf("\nLOCAL_WITNESS_RESULT: %d violation(s)\n",
                     report.violations);
        return EXIT_FAILURE;
    }
    (void)printf("\nLOCAL_WITNESS_RESULT: conditions satisfied\n");
    (void)printf("BIDIRECTIONAL_VIRTUAL_CHANNEL: demonstrated\n");
    (void)printf("FINITE_PAYLOAD_SEGMENTATION: demonstrated for bounded cases\n");
    (void)printf("PHYSICAL_BACKWARD_SIGNALLING: not present in this model\n");
    (void)printf("DEMO_LOCAL_EFFECT_ACK=COMMITTED\n");
    (void)printf("GLOBAL_EFFECT_ACK_DONE=UNCLAIMED\n");
    return EXIT_SUCCESS;
}
