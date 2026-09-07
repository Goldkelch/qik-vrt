/*
 * QIK-VRT IP bootstrap probe.
 *
 * Strict ISO C90 source plus POSIX/BSD socket interfaces.  The same source is
 * compiled natively for runtime smoke tests and as an -m68000 ELF object.
 * The M68000 object proves code generation for the CPU target; it is not a
 * claim that Debian glibc or this container itself runs on a physical MC68000.
 */
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#define QIKVRT_BUF 8192
#define QIKVRT_REQ 2048

static int write_all(int fd, const char *buf, size_t len)
{
    size_t done;
    ssize_t rc;

    done = 0U;
    while (done < len) {
        rc = write(fd, buf + done, len - done);
        if (rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (rc == 0) {
            return -1;
        }
        done += (size_t)rc;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *host;
    const char *path;
    long port_long;
    int port;
    struct hostent *hostent_value;
    struct sockaddr_in address;
    int fd;
    char request[QIKVRT_REQ];
    char buffer[QIKVRT_BUF + 1];
    int request_len;
    ssize_t count;
    size_t used;
    int saw_200;

    if (argc != 4) {
        fprintf(stderr, "usage: %s HOST PORT PATH\n", argv[0]);
        return 64;
    }

    host = argv[1];
    path = argv[3];
    port_long = strtol(argv[2], (char **)0, 10);
    if (port_long < 1L || port_long > 65535L) {
        fprintf(stderr, "invalid TCP port\n");
        return 64;
    }
    port = (int)port_long;
    if (strlen(host) > 512U || strlen(path) > 1024U || path[0] != '/') {
        fprintf(stderr, "host/path outside bounded bootstrap contract\n");
        return 64;
    }

    hostent_value = gethostbyname(host);
    if (hostent_value == (struct hostent *)0 ||
        hostent_value->h_addrtype != AF_INET ||
        hostent_value->h_length != (int)sizeof(address.sin_addr)) {
        fprintf(stderr, "IPv4 resolution failed for %s\n", host);
        return 69;
    }

    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons((unsigned short)port);
    memcpy(&address.sin_addr, hostent_value->h_addr_list[0], sizeof(address.sin_addr));

    fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("socket");
        return 71;
    }
    if (connect(fd, (struct sockaddr *)&address, sizeof(address)) != 0) {
        perror("connect");
        close(fd);
        return 69;
    }

    request_len = sprintf(
        request,
        "GET %s HTTP/1.0\r\nHost: %s\r\nUser-Agent: qikvrt-ip-bootstrap/1\r\nConnection: close\r\n\r\n",
        path,
        host
    );
    if (request_len < 0 || (size_t)request_len >= sizeof(request)) {
        close(fd);
        return 70;
    }
    if (write_all(fd, request, (size_t)request_len) != 0) {
        perror("write");
        close(fd);
        return 74;
    }

    used = 0U;
    saw_200 = 0;
    while (used < QIKVRT_BUF) {
        count = read(fd, buffer + used, QIKVRT_BUF - used);
        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            perror("read");
            close(fd);
            return 74;
        }
        if (count == 0) {
            break;
        }
        used += (size_t)count;
        if (used >= 12U) {
            buffer[used] = '\0';
            if (strstr(buffer, "HTTP/1.0 200") != (char *)0 ||
                strstr(buffer, "HTTP/1.1 200") != (char *)0) {
                saw_200 = 1;
            }
        }
    }
    close(fd);

    buffer[used] = '\0';
    if (!saw_200) {
        fprintf(stderr, "bootstrap endpoint did not return HTTP 200\n");
        return 69;
    }

    printf("QIKVRT_IP_BOOTSTRAP_OK host=%s port=%d path=%s bytes=%lu\n",
           host, port, path, (unsigned long)used);
    return 0;
}
