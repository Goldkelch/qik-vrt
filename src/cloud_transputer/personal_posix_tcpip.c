/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/*
 * QIK-VRT Personal POSIX / M68000 TCP-IP bootstrap profile.
 *
 * Strict ISO C90 source. The POSIX personality and IPv4/TCP/UDP packet engine
 * below do not call host socket APIs. They are therefore executable as one
 * bounded M68000 program under qemu-m68k and remain separable from the OCI
 * host adapter that carries public Internet traffic for Firefox and services.
 *
 * This is an implementation profile, not a claim of complete POSIX.1
 * conformance, a bare-metal NIC driver, or physical MC68000 execution.
 */
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include "qikvrt/effect_ack.h"

#define QV_MAX_FILES 4
#define QV_FILE_CAPACITY 512
#define QV_IPV4_HEADER 20
#define QV_TCP_HEADER 20
#define QV_UDP_HEADER 8
#define QV_PACKET_CAPACITY 1024

#define QV_TCP_SYN 0x02
#define QV_TCP_PSH 0x08
#define QV_TCP_ACK 0x10

#define QV_TCP_CLOSED 0
#define QV_TCP_LISTEN 1
#define QV_TCP_SYN_SENT 2
#define QV_TCP_SYN_RECEIVED 3
#define QV_TCP_ESTABLISHED 4

typedef unsigned char qv_u8;
typedef unsigned short qv_u16;
typedef unsigned long qv_u32;

typedef struct qv_file {
    int used;
    char name[64];
    qv_u8 data[QV_FILE_CAPACITY];
    unsigned long size;
    unsigned long pos;
} qv_file;

typedef struct qv_tcp_endpoint {
    int state;
    qv_u32 snd_nxt;
    qv_u32 rcv_nxt;
} qv_tcp_endpoint;

static qv_file qv_files[QV_MAX_FILES];

static qv_u32 qv_u32_mask(qv_u32 value)
{
    return value & 0xffffffffUL;
}

static void qv_put16(qv_u8 *p, qv_u16 value)
{
    p[0] = (qv_u8)((value >> 8) & 0xffU);
    p[1] = (qv_u8)(value & 0xffU);
}

static qv_u16 qv_get16(const qv_u8 *p)
{
    return (qv_u16)(((qv_u16)p[0] << 8) | (qv_u16)p[1]);
}

static void qv_put32(qv_u8 *p, qv_u32 value)
{
    value = qv_u32_mask(value);
    p[0] = (qv_u8)((value >> 24) & 0xffUL);
    p[1] = (qv_u8)((value >> 16) & 0xffUL);
    p[2] = (qv_u8)((value >> 8) & 0xffUL);
    p[3] = (qv_u8)(value & 0xffUL);
}

static qv_u32 qv_get32(const qv_u8 *p)
{
    qv_u32 value;
    value = ((qv_u32)p[0] << 24)
          | ((qv_u32)p[1] << 16)
          | ((qv_u32)p[2] << 8)
          | (qv_u32)p[3];
    return qv_u32_mask(value);
}

static qv_u16 qv_checksum(const qv_u8 *data, unsigned long length, qv_u32 initial)
{
    qv_u32 sum;
    unsigned long i;

    sum = initial;
    i = 0UL;
    while (i + 1UL < length) {
        sum += (qv_u32)(((qv_u16)data[i] << 8) | (qv_u16)data[i + 1UL]);
        while ((sum >> 16) != 0UL) {
            sum = (sum & 0xffffUL) + (sum >> 16);
        }
        i += 2UL;
    }
    if (i < length) {
        sum += (qv_u32)((qv_u16)data[i] << 8);
    }
    while ((sum >> 16) != 0UL) {
        sum = (sum & 0xffffUL) + (sum >> 16);
    }
    return (qv_u16)(~sum & 0xffffUL);
}

static qv_u32 qv_pseudo_sum(qv_u32 src, qv_u32 dst, qv_u8 protocol, qv_u16 length)
{
    qv_u32 sum;
    sum = ((src >> 16) & 0xffffUL) + (src & 0xffffUL);
    sum += ((dst >> 16) & 0xffffUL) + (dst & 0xffffUL);
    sum += (qv_u32)protocol;
    sum += (qv_u32)length;
    while ((sum >> 16) != 0UL) {
        sum = (sum & 0xffffUL) + (sum >> 16);
    }
    return sum;
}

static int qv_open(const char *path)
{
    int i;
    if (path == (const char *)0 || path[0] != '/') {
        return -1;
    }
    for (i = 0; i < QV_MAX_FILES; ++i) {
        if (qv_files[i].used && strcmp(qv_files[i].name, path) == 0) {
            qv_files[i].pos = 0UL;
            return i + 3;
        }
    }
    for (i = 0; i < QV_MAX_FILES; ++i) {
        if (!qv_files[i].used) {
            size_t n;
            n = strlen(path);
            if (n >= sizeof(qv_files[i].name)) {
                return -1;
            }
            memset(&qv_files[i], 0, sizeof(qv_files[i]));
            qv_files[i].used = 1;
            memcpy(qv_files[i].name, path, n + 1U);
            return i + 3;
        }
    }
    return -1;
}

static qv_file *qv_fd(int fd)
{
    int index;
    index = fd - 3;
    if (index < 0 || index >= QV_MAX_FILES || !qv_files[index].used) {
        return (qv_file *)0;
    }
    return &qv_files[index];
}

static long qv_write(int fd, const void *buffer, unsigned long length)
{
    qv_file *file_value;
    unsigned long available;
    file_value = qv_fd(fd);
    if (file_value == (qv_file *)0 || buffer == (const void *)0) {
        return -1L;
    }
    if (file_value->pos > QV_FILE_CAPACITY) {
        return -1L;
    }
    available = (unsigned long)QV_FILE_CAPACITY - file_value->pos;
    if (length > available) {
        return -1L;
    }
    memcpy(file_value->data + file_value->pos, buffer, (size_t)length);
    file_value->pos += length;
    if (file_value->pos > file_value->size) {
        file_value->size = file_value->pos;
    }
    return (long)length;
}

static long qv_read(int fd, void *buffer, unsigned long length)
{
    qv_file *file_value;
    unsigned long available;
    file_value = qv_fd(fd);
    if (file_value == (qv_file *)0 || buffer == (void *)0) {
        return -1L;
    }
    if (file_value->pos > file_value->size) {
        return -1L;
    }
    available = file_value->size - file_value->pos;
    if (length > available) {
        length = available;
    }
    memcpy(buffer, file_value->data + file_value->pos, (size_t)length);
    file_value->pos += length;
    return (long)length;
}

static long qv_lseek(int fd, long offset)
{
    qv_file *file_value;
    file_value = qv_fd(fd);
    if (file_value == (qv_file *)0 || offset < 0L || (unsigned long)offset > file_value->size) {
        return -1L;
    }
    file_value->pos = (unsigned long)offset;
    return offset;
}

static int qv_close(int fd)
{
    qv_file *file_value;
    file_value = qv_fd(fd);
    if (file_value == (qv_file *)0) {
        return -1;
    }
    file_value->pos = 0UL;
    return 0;
}

static int qv_posix_selftest(void)
{
    static const char payload[] = "qikvrt-personal-posix-state-v1";
    char readback[64];
    int fd;
    long rc;

    memset(qv_files, 0, sizeof(qv_files));
    memset(readback, 0, sizeof(readback));
    fd = qv_open("/state/node");
    if (fd < 3) {
        return 0;
    }
    rc = qv_write(fd, payload, (unsigned long)(sizeof(payload) - 1U));
    if (rc != (long)(sizeof(payload) - 1U)) {
        return 0;
    }
    if (qv_lseek(fd, 0L) != 0L) {
        return 0;
    }
    rc = qv_read(fd, readback, (unsigned long)(sizeof(payload) - 1U));
    if (rc != (long)(sizeof(payload) - 1U)) {
        return 0;
    }
    if (memcmp(readback, payload, sizeof(payload) - 1U) != 0) {
        return 0;
    }
    return qv_close(fd) == 0;
}

static unsigned long qv_ipv4_packet(
    qv_u8 *packet,
    unsigned long capacity,
    qv_u8 protocol,
    qv_u32 src,
    qv_u32 dst,
    const qv_u8 *payload,
    unsigned long payload_len)
{
    unsigned long total;
    qv_u16 sum;
    total = (unsigned long)QV_IPV4_HEADER + payload_len;
    if (packet == (qv_u8 *)0 || payload == (const qv_u8 *)0 || total > capacity || total > 65535UL) {
        return 0UL;
    }
    memset(packet, 0, (size_t)total);
    packet[0] = 0x45U;
    packet[1] = 0U;
    qv_put16(packet + 2, (qv_u16)total);
    qv_put16(packet + 4, 0x5156U);
    qv_put16(packet + 6, 0x4000U);
    packet[8] = 64U;
    packet[9] = protocol;
    qv_put32(packet + 12, src);
    qv_put32(packet + 16, dst);
    sum = qv_checksum(packet, QV_IPV4_HEADER, 0UL);
    qv_put16(packet + 10, sum);
    memcpy(packet + QV_IPV4_HEADER, payload, (size_t)payload_len);
    return total;
}

static int qv_ipv4_valid(const qv_u8 *packet, unsigned long length, qv_u8 expected_protocol)
{
    if (packet == (const qv_u8 *)0 || length < QV_IPV4_HEADER) {
        return 0;
    }
    if (packet[0] != 0x45U || packet[9] != expected_protocol) {
        return 0;
    }
    if ((unsigned long)qv_get16(packet + 2) != length) {
        return 0;
    }
    return qv_checksum(packet, QV_IPV4_HEADER, 0UL) == 0U;
}

static unsigned long qv_tcp_segment(
    qv_u8 *segment,
    unsigned long capacity,
    qv_u32 src_ip,
    qv_u32 dst_ip,
    qv_u16 src_port,
    qv_u16 dst_port,
    qv_u32 seq,
    qv_u32 ack,
    qv_u8 flags,
    const qv_u8 *payload,
    unsigned long payload_len)
{
    unsigned long total;
    qv_u16 sum;
    total = (unsigned long)QV_TCP_HEADER + payload_len;
    if (segment == (qv_u8 *)0 || total > capacity || total > 65535UL) {
        return 0UL;
    }
    if (payload_len != 0UL && payload == (const qv_u8 *)0) {
        return 0UL;
    }
    memset(segment, 0, (size_t)total);
    qv_put16(segment, src_port);
    qv_put16(segment + 2, dst_port);
    qv_put32(segment + 4, seq);
    qv_put32(segment + 8, ack);
    segment[12] = 0x50U;
    segment[13] = flags;
    qv_put16(segment + 14, 4096U);
    if (payload_len != 0UL) {
        memcpy(segment + QV_TCP_HEADER, payload, (size_t)payload_len);
    }
    sum = qv_checksum(segment, total, qv_pseudo_sum(src_ip, dst_ip, 6U, (qv_u16)total));
    qv_put16(segment + 16, sum);
    return total;
}

static int qv_tcp_valid(const qv_u8 *packet, unsigned long packet_len)
{
    qv_u32 src;
    qv_u32 dst;
    const qv_u8 *segment;
    unsigned long segment_len;
    qv_u16 result;

    if (!qv_ipv4_valid(packet, packet_len, 6U)) {
        return 0;
    }
    segment = packet + QV_IPV4_HEADER;
    segment_len = packet_len - (unsigned long)QV_IPV4_HEADER;
    if (segment_len < QV_TCP_HEADER || (segment[12] >> 4) != 5U) {
        return 0;
    }
    src = qv_get32(packet + 12);
    dst = qv_get32(packet + 16);
    result = qv_checksum(segment, segment_len, qv_pseudo_sum(src, dst, 6U, (qv_u16)segment_len));
    return result == 0U;
}

static unsigned long qv_make_tcp_packet(
    qv_u8 *packet,
    unsigned long capacity,
    qv_u32 src,
    qv_u32 dst,
    qv_u16 src_port,
    qv_u16 dst_port,
    qv_u32 seq,
    qv_u32 ack,
    qv_u8 flags,
    const qv_u8 *payload,
    unsigned long payload_len)
{
    qv_u8 segment[QV_PACKET_CAPACITY];
    unsigned long segment_len;

    segment_len = qv_tcp_segment(segment, sizeof(segment), src, dst, src_port, dst_port,
                                 seq, ack, flags, payload, payload_len);
    if (segment_len == 0UL) {
        return 0UL;
    }
    return qv_ipv4_packet(packet, capacity, 6U, src, dst, segment, segment_len);
}

static unsigned long qv_udp_segment(
    qv_u8 *segment,
    unsigned long capacity,
    qv_u32 src_ip,
    qv_u32 dst_ip,
    qv_u16 src_port,
    qv_u16 dst_port,
    const qv_u8 *payload,
    unsigned long payload_len)
{
    unsigned long total;
    qv_u16 sum;
    total = (unsigned long)QV_UDP_HEADER + payload_len;
    if (segment == (qv_u8 *)0 || payload == (const qv_u8 *)0 || total > capacity || total > 65535UL) {
        return 0UL;
    }
    memset(segment, 0, (size_t)total);
    qv_put16(segment, src_port);
    qv_put16(segment + 2, dst_port);
    qv_put16(segment + 4, (qv_u16)total);
    memcpy(segment + QV_UDP_HEADER, payload, (size_t)payload_len);
    sum = qv_checksum(segment, total, qv_pseudo_sum(src_ip, dst_ip, 17U, (qv_u16)total));
    if (sum == 0U) {
        sum = 0xffffU;
    }
    qv_put16(segment + 6, sum);
    return total;
}

static int qv_udp_valid(const qv_u8 *packet, unsigned long packet_len)
{
    const qv_u8 *segment;
    unsigned long segment_len;
    qv_u32 src;
    qv_u32 dst;
    if (!qv_ipv4_valid(packet, packet_len, 17U)) {
        return 0;
    }
    segment = packet + QV_IPV4_HEADER;
    segment_len = packet_len - (unsigned long)QV_IPV4_HEADER;
    if (segment_len < QV_UDP_HEADER || (unsigned long)qv_get16(segment + 4) != segment_len) {
        return 0;
    }
    src = qv_get32(packet + 12);
    dst = qv_get32(packet + 16);
    return qv_checksum(segment, segment_len, qv_pseudo_sum(src, dst, 17U, (qv_u16)segment_len)) == 0U;
}

static int qv_tcp_bootstrap_selftest(void)
{
    const qv_u32 client_ip = 0x0a000001UL;
    const qv_u32 server_ip = 0x0a000002UL;
    const qv_u16 client_port = 40000U;
    const qv_u16 server_port = 80U;
    static const qv_u8 request[] =
        "GET /.well-known/qikvrt-cloud-transputer HTTP/1.0\r\n"
        "Host: qikvrt.mesh.local\r\n\r\n";
    qv_tcp_endpoint client;
    qv_tcp_endpoint server;
    qv_u8 packet[QV_PACKET_CAPACITY];
    unsigned long length;
    const qv_u8 *tcp;
    const qv_u8 *body;
    unsigned long body_len;

    client.state = QV_TCP_CLOSED;
    client.snd_nxt = 0x01020304UL;
    client.rcv_nxt = 0UL;
    server.state = QV_TCP_LISTEN;
    server.snd_nxt = 0x11223344UL;
    server.rcv_nxt = 0UL;

    length = qv_make_tcp_packet(packet, sizeof(packet), client_ip, server_ip,
                                client_port, server_port, client.snd_nxt, 0UL,
                                QV_TCP_SYN, (const qv_u8 *)0, 0UL);
    if (length == 0UL || !qv_tcp_valid(packet, length)) {
        return 0;
    }
    tcp = packet + QV_IPV4_HEADER;
    if (tcp[13] != QV_TCP_SYN || qv_get32(tcp + 4) != client.snd_nxt) {
        return 0;
    }
    client.state = QV_TCP_SYN_SENT;
    client.snd_nxt = qv_u32_mask(client.snd_nxt + 1UL);
    server.rcv_nxt = qv_u32_mask(qv_get32(tcp + 4) + 1UL);
    server.state = QV_TCP_SYN_RECEIVED;

    length = qv_make_tcp_packet(packet, sizeof(packet), server_ip, client_ip,
                                server_port, client_port, server.snd_nxt, server.rcv_nxt,
                                (qv_u8)(QV_TCP_SYN | QV_TCP_ACK), (const qv_u8 *)0, 0UL);
    if (length == 0UL || !qv_tcp_valid(packet, length)) {
        return 0;
    }
    tcp = packet + QV_IPV4_HEADER;
    if (tcp[13] != (qv_u8)(QV_TCP_SYN | QV_TCP_ACK) || qv_get32(tcp + 8) != client.snd_nxt) {
        return 0;
    }
    client.rcv_nxt = qv_u32_mask(qv_get32(tcp + 4) + 1UL);
    server.snd_nxt = qv_u32_mask(server.snd_nxt + 1UL);
    client.state = QV_TCP_ESTABLISHED;

    length = qv_make_tcp_packet(packet, sizeof(packet), client_ip, server_ip,
                                client_port, server_port, client.snd_nxt, client.rcv_nxt,
                                QV_TCP_ACK, (const qv_u8 *)0, 0UL);
    if (length == 0UL || !qv_tcp_valid(packet, length)) {
        return 0;
    }
    tcp = packet + QV_IPV4_HEADER;
    if (tcp[13] != QV_TCP_ACK || qv_get32(tcp + 8) != server.snd_nxt) {
        return 0;
    }
    server.state = QV_TCP_ESTABLISHED;
    if (client.state != QV_TCP_ESTABLISHED || server.state != QV_TCP_ESTABLISHED) {
        return 0;
    }

    length = qv_make_tcp_packet(packet, sizeof(packet), client_ip, server_ip,
                                client_port, server_port, client.snd_nxt, client.rcv_nxt,
                                (qv_u8)(QV_TCP_PSH | QV_TCP_ACK), request,
                                (unsigned long)(sizeof(request) - 1U));
    if (length == 0UL || !qv_tcp_valid(packet, length)) {
        return 0;
    }
    tcp = packet + QV_IPV4_HEADER;
    if (tcp[13] != (qv_u8)(QV_TCP_PSH | QV_TCP_ACK)) {
        return 0;
    }
    body = tcp + QV_TCP_HEADER;
    body_len = length - (unsigned long)QV_IPV4_HEADER - (unsigned long)QV_TCP_HEADER;
    if (body_len != (unsigned long)(sizeof(request) - 1U)) {
        return 0;
    }
    return memcmp(body, request, sizeof(request) - 1U) == 0;
}

static int qv_udp_selftest(void)
{
    const qv_u32 src = 0x0a000001UL;
    const qv_u32 dst = 0x0a000002UL;
    static const qv_u8 payload[] = "QIKVRT-DNS-BOOTSTRAP";
    qv_u8 segment[256];
    qv_u8 packet[QV_PACKET_CAPACITY];
    unsigned long segment_len;
    unsigned long packet_len;

    segment_len = qv_udp_segment(segment, sizeof(segment), src, dst, 53530U, 5353U,
                                 payload, (unsigned long)(sizeof(payload) - 1U));
    if (segment_len == 0UL) {
        return 0;
    }
    packet_len = qv_ipv4_packet(packet, sizeof(packet), 17U, src, dst, segment, segment_len);
    return packet_len != 0UL && qv_udp_valid(packet, packet_len);
}

static void qv_fill_done(qikvrt_effect_ack_input *input)
{
    memset(input, 0, sizeof(*input));
    input->transport_ack = 1;
    input->input_identifier_available = 1;
    input->input_digest_valid = 1;
    input->origin_checked = 1;
    input->context_checked = 1;
    input->semantics_reconstructed = 1;
    input->effect_anticipated = 1;
    input->risk_classified = 1;
    input->risk_known = 1;
    input->responsibility_assigned = 1;
    input->responsibility_owner_present = 1;
    input->connection_decided = 1;
    input->connection_decision = QIKVRT_EFFECT_DECISION_RELEASE;
    input->policy_allows_release = 1;
    input->deadline_exceeded = 0;
    input->no_open_questions = 1;
    input->no_next_required_checks = 1;
    input->required_evidence_present = 1;
    input->predecessor_invalid = 0;
    input->integrity_failure = 0;
}

int main(void)
{
    qikvrt_effect_ack_input input;
    qikvrt_effect_ack_state done_state;
    qikvrt_effect_ack_state negative_state;
    int posix_ok;
    int tcp_ok;
    int udp_ok;

    if (CHAR_BIT != 8 || sizeof(qv_u16) < 2U || sizeof(qv_u32) < 4U) {
        puts("BLOCK=UNSUPPORTED_C90_INTEGER_MODEL");
        return 2;
    }

    posix_ok = qv_posix_selftest();
    tcp_ok = qv_tcp_bootstrap_selftest();
    udp_ok = qv_udp_selftest();

    qv_fill_done(&input);
    done_state = qikvrt_effect_ack_evaluate(&input);
    input.required_evidence_present = 0;
    negative_state = qikvrt_effect_ack_evaluate(&input);

#ifdef __m68k__
    puts("ARCH=M68000_FAMILY");
#else
    puts("ARCH=NON_M68000_BUILD");
#endif
    puts("PERSONAL_POSIX_PROFILE=QIKVRT_PERSONAL_POSIX_C90_V1");
    printf("PERSONAL_POSIX_SELFTEST=%s\n", posix_ok ? "PASS" : "FAIL");
    printf("STANDALONE_M68000_TCPIP_PACKET_ENGINE=%s\n", (tcp_ok && udp_ok) ? "PASS" : "FAIL");
    printf("TCP_HANDSHAKE_SELFTEST=%s\n", tcp_ok ? "PASS" : "FAIL");
    printf("TCP_HTTP_BOOTSTRAP_SELFTEST=%s\n", tcp_ok ? "PASS" : "FAIL");
    printf("UDP_SELFTEST=%s\n", udp_ok ? "PASS" : "FAIL");
    printf("EFFECT_ACK_STATE=%s\n", qikvrt_effect_ack_state_name(done_state));
    printf("EFFECT_ACK_NEGATIVE_STATE=%s\n", qikvrt_effect_ack_state_name(negative_state));
    puts("EXTERNAL_PACKET_IO=LINUX_OCI_HOST_ADAPTER_REQUIRED");
    puts("BARE_METAL_NIC_DRIVER=NOT_CLAIMED");
    puts("FULL_POSIX_1_CONFORMANCE=NOT_CLAIMED");

    if (!posix_ok || !tcp_ok || !udp_ok) {
        return 20;
    }
    if (done_state != QIKVRT_EFFECT_ACK_DONE) {
        return 21;
    }
    if (negative_state == QIKVRT_EFFECT_ACK_DONE) {
        return 22;
    }
    return 0;
}
