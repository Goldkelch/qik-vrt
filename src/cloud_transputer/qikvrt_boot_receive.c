/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. ISO C90 plus bounded POSIX UDP transport. */
#define _POSIX_C_SOURCE 200809L
#include "qikvrt_wire_v1.h"
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define HEADER 32U
#define CHUNK 128U
#define MAX_IMAGE (4U * 1024U * 1024U)

static unsigned int get32(const unsigned char *p)
{
    return ((unsigned int)p[0] << 24U) | ((unsigned int)p[1] << 16U)
        | ((unsigned int)p[2] << 8U) | (unsigned int)p[3];
}

static void put32(unsigned char *p, unsigned int n)
{
    p[0] = (unsigned char)(n >> 24U); p[1] = (unsigned char)(n >> 16U);
    p[2] = (unsigned char)(n >> 8U); p[3] = (unsigned char)n;
}

static unsigned int checksum(const unsigned char *p, unsigned int length)
{
    unsigned char data[28U + CHUNK];
    memcpy(data, p, 28U);
    if (length != 0U) { memcpy(data + 28U, p + HEADER, length); }
    return qikvrt_fnv1a32(data, 28U + length);
}

static int exchange(int fd, unsigned int type, unsigned int nonce,
                    unsigned int offset, unsigned int total,
                    unsigned char *reply, time_t deadline)
{
    unsigned char request[HEADER];
    unsigned int attempt, dropped, length;
    ssize_t count;
    memset(request, 0, sizeof(request)); memcpy(request, "QBT1", 4U);
    request[4] = (unsigned char)type;
    put32(request + 8U, nonce); put32(request + 12U, 1U);
    put32(request + 16U, offset); put32(request + 20U, total);
    put32(request + 28U, checksum(request, 0U));
    for (attempt = 0U; attempt < 3U && time(0) < deadline; ++attempt) {
        if (send(fd, request, sizeof(request), 0) != (ssize_t)sizeof(request)) { return -1; }
        for (dropped = 0U; dropped < 8U && time(0) < deadline; ++dropped) {
            count = recv(fd, reply, HEADER + CHUNK + 1U, 0);
            if (count < 0) { if (errno == EINTR) { continue; } break; }
            if (count < (ssize_t)HEADER || count > (ssize_t)(HEADER + CHUNK)) { continue; }
            length = get32(reply + 24U);
            if (memcmp(reply, "QBT1", 4U) != 0 || length > CHUNK
                || (unsigned int)count != HEADER + length || reply[5] || reply[6] || reply[7]
                || get32(reply + 8U) != nonce || get32(reply + 12U) != 1U
                || get32(reply + 16U) != offset
                || get32(reply + 28U) != checksum(reply, length)) { continue; }
            if ((type == 1U && reply[4] == 2U) || (type == 3U && reply[4] == 4U)
                || (type == 5U && reply[4] == 5U)) { return (int)length; }
        }
    }
    return -1;
}

int main(int argc, char **argv)
{
    struct sockaddr_in address;
    struct timeval timeout;
    unsigned char reply[HEADER + CHUNK + 1U], expected[32], actual[32];
    unsigned char *image;
    unsigned int nonce, total, offset, n, value;
    unsigned long port, session;
    char *end;
    int fd, output, rc, length;
    ssize_t written;
    time_t deadline;
    if (argc != 6) {
        fprintf(stderr, "usage: %s SERVER_IPV4 PORT OUTPUT EXPECTED_SHA256 NONCE\n", argv[0]);
        return 64;
    }
    port = strtoul(argv[2], &end, 10);
    if (!*argv[2] || strspn(argv[2], "0123456789") != strlen(argv[2]) || *end || port == 0UL || port > 65535UL) { return 64; }
    session = strtoul(argv[5], &end, 10);
    if (!*argv[5] || strspn(argv[5], "0123456789") != strlen(argv[5]) || *end || session == 0UL || session > 4294967295UL) { return 64; }
    nonce = (unsigned int)session;
    if (strlen(argv[4]) != 64U) { return 64; }
    for (n = 0U; n < 32U; ++n) {
        if (strspn(argv[4], "0123456789abcdef") != 64U
            || sscanf(argv[4] + n * 2U, "%2x", &value) != 1) { return 64; }
        expected[n] = (unsigned char)value;
    }
    memset(&address, 0, sizeof(address)); address.sin_family = AF_INET;
    address.sin_port = htons((unsigned short)port);
    if (inet_pton(AF_INET, argv[1], &address.sin_addr) != 1) { return 64; }
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) { return 71; }
    timeout.tv_sec = 2; timeout.tv_usec = 0;
    if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) != 0
        || connect(fd, (struct sockaddr *)&address, sizeof(address)) != 0) { close(fd); return 69; }
    deadline = time(0) + 120;
    alarm(121U); /* Outer wall-clock bound even if the civil clock moves back. */
    length = exchange(fd, 1U, nonce, 0U, 0U, reply, deadline);
    if (length != 32) { close(fd); return 65; }
    total = get32(reply + 20U);
    if (total == 0U || total > MAX_IMAGE || memcmp(reply + HEADER, expected, 32U)) {
        close(fd); return 65;
    }
    image = (unsigned char *)malloc(total);
    if (image == 0) { close(fd); return 71; }
    rc = 65;
    for (offset = 0U; offset < total;) {
        length = exchange(fd, 3U, nonce, offset, total, reply, deadline);
        n = total - offset < CHUNK ? total - offset : CHUNK;
        if (length != (int)n || get32(reply + 20U) != total) { goto finish; }
        memcpy(image + offset, reply + HEADER, n); offset += n;
    }
    qikvrt_sha256(image, total, actual);
    if (memcmp(actual, expected, 32U)) { goto finish; }
    /* Exclusive creation: never overwrite existing files or follow a symlink. */
    output = open(argv[3], O_CREAT | O_EXCL | O_WRONLY, S_IRUSR | S_IWUSR);
    if (output < 0) { rc = 73; goto finish; }
    offset = 0U;
    while (offset < total) {
        written = write(output, image + offset, total - offset);
        if (written < 0 && errno == EINTR) { continue; }
        if (written <= 0) { close(output); unlink(argv[3]); rc = 74; goto finish; }
        offset += (unsigned int)written;
    }
    rc = fsync(output); if (close(output) != 0) { rc = -1; }
    if (rc != 0) { unlink(argv[3]); rc = 74; goto finish; }
    /* Re-read persisted bytes before emitting content acknowledgement. */
    output = open(argv[3], O_RDONLY); offset = 0U;
    if (output < 0) { rc = 74; goto finish; }
    while (offset < total) {
        written = read(output, image + offset, total - offset);
        if (written < 0 && errno == EINTR) { continue; }
        if (written <= 0) { close(output); rc = 74; goto finish; }
        offset += (unsigned int)written;
    }
    close(output); qikvrt_sha256(image, total, actual);
    if (memcmp(actual, expected, 32U)) { rc = 65; goto finish; }
    length = exchange(fd, 5U, nonce, total, total, reply, deadline);
    if (length != 0 || get32(reply + 20U) != total) { rc = 69; goto finish; }
    printf("QIKVRT_BOOT_CONTENT_VERIFIED file_id=1 bytes=%u sha256=%s execution=SEPARATE\n", total, argv[4]);
    rc = 0;
finish:
    free(image); close(fd); return rc;
}
