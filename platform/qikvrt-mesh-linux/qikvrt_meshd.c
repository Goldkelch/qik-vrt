/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

/* Request the POSIX.1-2001 socket declarations while retaining C89 syntax. */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
#endif

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include "qikvrt/effect_ack.h"

#define QIKVRT_HEADER_LIMIT 8192
#define QIKVRT_BODY_LENGTH 20
#define QIKVRT_LISTEN_BACKLOG 16

typedef struct qikvrt_http_request {
    char method[8];
    char path[128];
    char version[16];
    long content_length;
    int has_content_length;
    int has_content_type;
    int content_type_ok;
    int has_host;
    int transfer_encoding_present;
    int expect_present;
} qikvrt_http_request;

typedef struct qikvrt_io_deadline {
    struct timespec end;
} qikvrt_io_deadline;

static int qikvrt_deadline_start(
    qikvrt_io_deadline *deadline,
    long timeout_ms)
{
    struct timespec now;
    long nanoseconds;

    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        return 0;
    }
    deadline->end.tv_sec = now.tv_sec + (time_t)(timeout_ms / 1000L);
    nanoseconds = now.tv_nsec + (timeout_ms % 1000L) * 1000000L;
    if (nanoseconds >= 1000000000L) {
        deadline->end.tv_sec += (time_t)1;
        nanoseconds -= 1000000000L;
    }
    deadline->end.tv_nsec = nanoseconds;
    return 1;
}

/*
 * Apply only the monotonic deadline's remaining duration.  Recomputing before
 * every recv prevents a peer from extending the total budget byte by byte.
 */
static int qikvrt_apply_receive_deadline(
    int descriptor,
    const qikvrt_io_deadline *deadline)
{
    struct timespec now;
    struct timeval timeout;
    time_t seconds;
    long nanoseconds;

    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        return 0;
    }
    seconds = deadline->end.tv_sec - now.tv_sec;
    nanoseconds = deadline->end.tv_nsec - now.tv_nsec;
    if (nanoseconds < 0L) {
        seconds -= (time_t)1;
        nanoseconds += 1000000000L;
    }
    if (seconds < (time_t)0
            || (seconds == (time_t)0 && nanoseconds <= 0L)) {
        return 0;
    }
    timeout.tv_sec = seconds;
    timeout.tv_usec = (suseconds_t)((nanoseconds + 999L) / 1000L);
    if (timeout.tv_usec >= (suseconds_t)1000000) {
        timeout.tv_sec += (time_t)1;
        timeout.tv_usec -= (suseconds_t)1000000;
    }
    if (timeout.tv_sec == (time_t)0 && timeout.tv_usec == (suseconds_t)0) {
        timeout.tv_usec = (suseconds_t)1;
    }
    return setsockopt(
        descriptor,
        SOL_SOCKET,
        SO_RCVTIMEO,
        &timeout,
        (socklen_t)sizeof(timeout)) == 0;
}

static int qikvrt_ascii_lower(int value)
{
    if (value >= 'A' && value <= 'Z') {
        return value + ('a' - 'A');
    }
    return value;
}

static int qikvrt_ascii_equal(const char *left, const char *right)
{
    while (*left != '\0' && *right != '\0') {
        if (qikvrt_ascii_lower((unsigned char)*left)
                != qikvrt_ascii_lower((unsigned char)*right)) {
            return 0;
        }
        left += 1;
        right += 1;
    }
    return *left == '\0' && *right == '\0';
}

static int qikvrt_http_tchar(int value)
{
    return (value >= 'a' && value <= 'z')
        || (value >= 'A' && value <= 'Z')
        || (value >= '0' && value <= '9')
        || value == '!' || value == '#' || value == '$' || value == '%'
        || value == '&' || value == '\'' || value == '*' || value == '+'
        || value == '-' || value == '.' || value == '^' || value == '_'
        || value == '`' || value == '|' || value == '~';
}

static char *qikvrt_trim(char *value)
{
    char *end;

    while (*value == ' ' || *value == '\t') {
        value += 1;
    }
    end = value + strlen(value);
    while (end > value && (end[-1] == ' ' || end[-1] == '\t')) {
        end -= 1;
    }
    *end = '\0';
    return value;
}

static int qikvrt_parse_long(
    const char *text,
    long minimum,
    long maximum,
    long *result)
{
    const unsigned char *cursor;
    char *end;
    long value;

    if (text == 0 || *text == '\0') {
        return 0;
    }
    cursor = (const unsigned char *)text;
    while (*cursor != '\0') {
        if (*cursor < '0' || *cursor > '9') {
            return 0;
        }
        cursor += 1;
    }
    errno = 0;
    end = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        return 0;
    }
    if (value < minimum || value > maximum) {
        return 0;
    }
    *result = value;
    return 1;
}

static int qikvrt_write_all(int descriptor, const char *data, size_t length)
{
    size_t offset;

    offset = 0U;
    while (offset < length) {
        ssize_t written;

        written = send(descriptor, data + offset, length - offset, 0);
        if (written < 0 && errno == EINTR) {
            continue;
        }
        if (written <= 0) {
            return 0;
        }
        offset += (size_t)written;
    }
    return 1;
}

static void qikvrt_send_json(
    int descriptor,
    int status,
    const char *reason,
    const char *extra_headers,
    const char *body)
{
    char header[768];
    int length;

    if (extra_headers == 0) {
        extra_headers = "";
    }
    length = sprintf(
        header,
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %lu\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n"
        "%s"
        "\r\n",
        status,
        reason,
        (unsigned long)strlen(body),
        extra_headers);
    if (length <= 0 || (size_t)length >= sizeof(header)) {
        return;
    }
    if (!qikvrt_write_all(descriptor, header, (size_t)length)) {
        return;
    }
    (void)qikvrt_write_all(descriptor, body, strlen(body));
}

static void qikvrt_send_closed_error(
    int descriptor,
    int status,
    const char *reason,
    const char *code)
{
    char body[384];
    int length;

    length = sprintf(
        body,
        "{\"error\":\"%s\",\"ordinary_release\":false,"
        "\"state\":\"EFFECT_ACK_BLOCK\","
        "\"scope\":\"PARSE_BOUNDARY\","
        "\"external_effect\":\"NOT_OBSERVED\"}\n",
        code);
    if (length <= 0 || (size_t)length >= sizeof(body)) {
        return;
    }
    qikvrt_send_json(descriptor, status, reason, 0, body);
}

static void qikvrt_send_method_not_allowed(int descriptor)
{
    qikvrt_send_json(
        descriptor,
        405,
        "Method Not Allowed",
        "Allow: GET, POST\r\n",
        "{\"error\":\"METHOD_NOT_ALLOWED\",\"ordinary_release\":false,"
        "\"state\":\"EFFECT_ACK_BLOCK\","
        "\"scope\":\"PARSE_BOUNDARY\","
        "\"external_effect\":\"NOT_OBSERVED\"}\n");
}

static long qikvrt_find_header_end(const unsigned char *data, size_t length)
{
    size_t index;

    if (length < 4U) {
        return -1L;
    }
    for (index = 0U; index + 3U < length; index += 1U) {
        if (data[index] == '\r'
                && data[index + 1U] == '\n'
                && data[index + 2U] == '\r'
                && data[index + 3U] == '\n') {
            return (long)index;
        }
    }
    return -1L;
}

static int qikvrt_header_octets_valid(
    const unsigned char *data,
    size_t length)
{
    size_t index;

    for (index = 0U; index < length; index += 1U) {
        unsigned char value;

        value = data[index];
        if (value == '\r') {
            if (index + 1U >= length || data[index + 1U] != '\n') {
                return 0;
            }
        } else if (value == '\n') {
            if (index == 0U || data[index - 1U] != '\r') {
                return 0;
            }
        } else if (value != '\t' && (value < 32U || value > 126U)) {
            return 0;
        }
    }
    return 1;
}

static int qikvrt_field_name_valid(const char *name)
{
    const unsigned char *cursor;

    cursor = (const unsigned char *)name;
    if (*cursor == '\0') {
        return 0;
    }
    while (*cursor != '\0') {
        unsigned char value;

        value = *cursor;
        if (!qikvrt_http_tchar(value)) {
            return 0;
        }
        cursor += 1;
    }
    return 1;
}

static int qikvrt_parse_request_line(
    char *line,
    qikvrt_http_request *request)
{
    char *first_space;
    char *second_space;
    char *method;
    char *path;
    char *version;

    first_space = strchr(line, ' ');
    if (first_space == 0) {
        return 0;
    }
    *first_space = '\0';
    second_space = strchr(first_space + 1, ' ');
    if (second_space == 0 || strchr(second_space + 1, ' ') != 0) {
        return 0;
    }
    *second_space = '\0';
    method = line;
    path = first_space + 1;
    version = second_space + 1;
    if (*method == '\0' || *path == '\0' || *version == '\0') {
        return 0;
    }
    {
        const unsigned char *cursor;

        cursor = (const unsigned char *)method;
        while (*cursor != '\0') {
            if (!qikvrt_http_tchar(*cursor)) {
                return 0;
            }
            cursor += 1;
        }
    }
    if (strlen(method) >= sizeof(request->method)
            || strlen(path) >= sizeof(request->path)
            || strlen(version) >= sizeof(request->version)) {
        return 0;
    }
    (void)strcpy(request->method, method);
    (void)strcpy(request->path, path);
    (void)strcpy(request->version, version);
    if (strcmp(request->version, "HTTP/1.1") != 0
            && strcmp(request->version, "HTTP/1.0") != 0) {
        return 0;
    }
    return 1;
}

static int qikvrt_parse_headers(
    char *header,
    qikvrt_http_request *request)
{
    char *line;

    (void)memset(request, 0, sizeof(*request));
    line = strtok(header, "\r\n");
    if (line == 0 || !qikvrt_parse_request_line(line, request)) {
        return 0;
    }
    while ((line = strtok(0, "\r\n")) != 0) {
        char *colon;
        char *name;
        char *value;

        colon = strchr(line, ':');
        if (colon == 0) {
            return 0;
        }
        *colon = '\0';
        name = line;
        value = qikvrt_trim(colon + 1);
        if (!qikvrt_field_name_valid(name)) {
            return 0;
        }
        if (qikvrt_ascii_equal(name, "Content-Length")) {
            long parsed;

            if (request->has_content_length
                    || !qikvrt_parse_long(value, 0L, 2147483647L, &parsed)) {
                return 0;
            }
            request->has_content_length = 1;
            request->content_length = parsed;
        } else if (qikvrt_ascii_equal(name, "Content-Type")) {
            if (request->has_content_type) {
                return 0;
            }
            request->has_content_type = 1;
            request->content_type_ok = qikvrt_ascii_equal(
                value, "application/octet-stream");
        } else if (qikvrt_ascii_equal(name, "Host")) {
            if (request->has_host || *value == '\0') {
                return 0;
            }
            request->has_host = 1;
        } else if (qikvrt_ascii_equal(name, "Transfer-Encoding")) {
            request->transfer_encoding_present = 1;
        } else if (qikvrt_ascii_equal(name, "Expect")) {
            request->expect_present = 1;
        }
    }
    if (strcmp(request->version, "HTTP/1.1") == 0 && !request->has_host) {
        return 0;
    }
    return 1;
}

static int qikvrt_decode_snapshot(
    const unsigned char body[QIKVRT_BODY_LENGTH],
    qikvrt_effect_ack_input *input)
{
    size_t index;

    for (index = 0U; index < QIKVRT_BODY_LENGTH; index += 1U) {
        if (index == 12U) {
            if (body[index] >= QIKVRT_EFFECT_ACK_DECISION_COUNT) {
                return 0;
            }
        } else if (body[index] > 1U) {
            return 0;
        }
    }
    (void)memset(input, 0, sizeof(*input));
    input->transport_ack = body[0];
    input->input_identifier_available = body[1];
    input->input_digest_valid = body[2];
    input->origin_checked = body[3];
    input->context_checked = body[4];
    input->semantics_reconstructed = body[5];
    input->effect_anticipated = body[6];
    input->risk_classified = body[7];
    input->risk_known = body[8];
    input->responsibility_assigned = body[9];
    input->responsibility_owner_present = body[10];
    input->connection_decided = body[11];
    input->connection_decision = (qikvrt_effect_ack_decision)body[12];
    input->policy_allows_release = body[13];
    input->deadline_exceeded = body[14];
    input->no_open_questions = body[15];
    input->no_next_required_checks = body[16];
    input->required_evidence_present = body[17];
    input->predecessor_invalid = body[18];
    input->integrity_failure = body[19];
    return 1;
}

static int qikvrt_receive_request(
    int descriptor,
    unsigned char *buffer,
    size_t capacity,
    size_t *used,
    size_t *header_length,
    const qikvrt_io_deadline *deadline)
{
    long header_end;

    *used = 0U;
    *header_length = 0U;
    header_end = -1L;
    while (header_end < 0L) {
        ssize_t received;

        if (*used >= (size_t)QIKVRT_HEADER_LIMIT) {
            return 2;
        }
        if (!qikvrt_apply_receive_deadline(descriptor, deadline)) {
            return 3;
        }
        received = recv(descriptor, buffer + *used, capacity - *used, 0);
        if (received < 0 && errno == EINTR) {
            continue;
        }
        if (received < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            return 3;
        }
        if (received <= 0) {
            return 0;
        }
        *used += (size_t)received;
        header_end = qikvrt_find_header_end(buffer, *used);
    }
    *header_length = (size_t)header_end + 4U;
    if (*header_length > (size_t)QIKVRT_HEADER_LIMIT) {
        return 2;
    }
    if (!qikvrt_header_octets_valid(buffer, (size_t)header_end + 2U)) {
        return 0;
    }
    return 1;
}

static int qikvrt_read_exact_body(
    int descriptor,
    unsigned char *body,
    size_t initial,
    size_t required,
    const qikvrt_io_deadline *deadline)
{
    size_t used;

    if (initial > required) {
        return 0;
    }
    used = initial;
    while (used < required) {
        ssize_t received;

        if (!qikvrt_apply_receive_deadline(descriptor, deadline)) {
            return 2;
        }
        received = recv(descriptor, body + used, required - used, 0);
        if (received < 0 && errno == EINTR) {
            continue;
        }
        if (received < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            return 2;
        }
        if (received <= 0) {
            return 0;
        }
        used += (size_t)received;
    }
    return 1;
}

static void qikvrt_handle_connection(int descriptor, long io_timeout_ms)
{
    unsigned char raw[QIKVRT_HEADER_LIMIT + QIKVRT_BODY_LENGTH + 1];
    size_t used;
    size_t header_length;
    size_t initial_body;
    qikvrt_http_request request;
    qikvrt_io_deadline deadline;
    int receive_status;

    if (!qikvrt_deadline_start(&deadline, io_timeout_ms)) {
        qikvrt_send_closed_error(
            descriptor, 500, "Internal Server Error", "MONOTONIC_CLOCK_UNAVAILABLE");
        return;
    }
    receive_status = qikvrt_receive_request(
        descriptor, raw, sizeof(raw), &used, &header_length, &deadline);
    if (receive_status == 2) {
        qikvrt_send_closed_error(
            descriptor, 431, "Request Header Fields Too Large", "HEADER_LIMIT");
        return;
    }
    if (receive_status != 1) {
        if (receive_status == 3) {
            qikvrt_send_closed_error(
                descriptor, 408, "Request Timeout", "IO_DEADLINE_EXCEEDED");
            return;
        }
        qikvrt_send_closed_error(descriptor, 400, "Bad Request", "MALFORMED_HTTP");
        return;
    }
    initial_body = used - header_length;
    raw[header_length - 4U] = '\0';
    if (!qikvrt_parse_headers((char *)raw, &request)) {
        qikvrt_send_closed_error(descriptor, 400, "Bad Request", "MALFORMED_HEADERS");
        return;
    }
    if (request.transfer_encoding_present) {
        qikvrt_send_closed_error(descriptor, 400, "Bad Request", "TRANSFER_ENCODING_FORBIDDEN");
        return;
    }
    if (request.expect_present) {
        qikvrt_send_closed_error(descriptor, 417, "Expectation Failed", "EXPECT_FORBIDDEN");
        return;
    }

    if (strcmp(request.method, "GET") == 0) {
        if ((request.has_content_length && request.content_length != 0L)
                || initial_body != 0U) {
            qikvrt_send_closed_error(descriptor, 400, "Bad Request", "GET_BODY_FORBIDDEN");
            return;
        }
        if (strcmp(request.path, "/healthz") == 0) {
            qikvrt_send_json(
                descriptor,
                200,
                "OK",
                0,
                "{\"service\":\"qikvrt_meshd\",\"status\":\"OBSERVED\","
                "\"mode\":\"BLOCKING_NON_POLLING\","
                "\"external_effects\":\"NONE\"}\n");
            return;
        }
        if (strcmp(request.path, "/.well-known/effect-ack") == 0) {
            qikvrt_send_json(
                descriptor,
                200,
                "OK",
                "Link: </v1/effect-ack/evaluate>; rel=\"effect-ack\"\r\n",
                "{\"schema\":\"qikvrt_effect_ack_binary_snapshot_v1\","
                "\"endpoint\":\"/v1/effect-ack/evaluate\","
                "\"media_type\":\"application/octet-stream\","
                "\"length\":20,\"decision_octet\":12,"
                "\"scope\":\"UNAUTHENTICATED_DECISION_PROJECTION_ONLY\","
                "\"authentication\":\"NOT_IMPLEMENTED\","
                "\"ordinary_release\":false,"
                "\"core_ordinary_release_candidate_only\":true,"
                "\"external_effects\":\"NONE\"}\n");
            return;
        }
        qikvrt_send_closed_error(descriptor, 404, "Not Found", "NOT_FOUND");
        return;
    }

    if (strcmp(request.method, "POST") == 0
            && strcmp(request.path, "/v1/effect-ack/evaluate") == 0) {
        unsigned char body[QIKVRT_BODY_LENGTH];
        qikvrt_effect_ack_input input;
        qikvrt_effect_ack_state state;
        int core_ordinary_release_candidate;
        int body_status;
        char response[384];
        int length;

        if (!request.has_content_length
                || request.content_length != QIKVRT_BODY_LENGTH) {
            qikvrt_send_closed_error(descriptor, 400, "Bad Request", "BODY_LENGTH_MUST_BE_20");
            return;
        }
        if (!request.has_content_type || !request.content_type_ok) {
            qikvrt_send_closed_error(descriptor, 415, "Unsupported Media Type", "BINARY_MEDIA_TYPE_REQUIRED");
            return;
        }
        if (initial_body > QIKVRT_BODY_LENGTH) {
            qikvrt_send_closed_error(descriptor, 400, "Bad Request", "BODY_EXCEEDS_20");
            return;
        }
        if (initial_body > 0U) {
            (void)memcpy(body, raw + header_length, initial_body);
        }
        body_status = qikvrt_read_exact_body(
            descriptor, body, initial_body, QIKVRT_BODY_LENGTH, &deadline);
        if (body_status == 2) {
            qikvrt_send_closed_error(
                descriptor, 408, "Request Timeout", "IO_DEADLINE_EXCEEDED");
            return;
        }
        if (body_status != 1) {
            qikvrt_send_closed_error(descriptor, 400, "Bad Request", "INCOMPLETE_BODY");
            return;
        }
        if (!qikvrt_decode_snapshot(body, &input)) {
            qikvrt_send_closed_error(descriptor, 400, "Bad Request", "INVALID_SNAPSHOT_OCTET");
            return;
        }
        state = qikvrt_effect_ack_evaluate(&input);
        core_ordinary_release_candidate =
            qikvrt_effect_ack_ordinary_release(state);
        length = sprintf(
            response,
            "{\"state\":\"%s\",\"state_code\":%d,"
            "\"ordinary_release\":false,"
            "\"core_ordinary_release_candidate\":%s,"
            "\"scope\":\"UNAUTHENTICATED_DECISION_PROJECTION_ONLY\","
            "\"external_effect\":\"NOT_OBSERVED\"}\n",
            qikvrt_effect_ack_state_name(state),
            (int)state,
            core_ordinary_release_candidate ? "true" : "false");
        if (length <= 0 || (size_t)length >= sizeof(response)) {
            qikvrt_send_closed_error(descriptor, 500, "Internal Server Error", "RESPONSE_BOUND");
            return;
        }
        qikvrt_send_json(descriptor, 200, "OK", 0, response);
        return;
    }

    if (strcmp(request.method, "POST") == 0) {
        qikvrt_send_closed_error(descriptor, 404, "Not Found", "NOT_FOUND");
        return;
    }
    qikvrt_send_method_not_allowed(descriptor);
}

static int qikvrt_self_test(void)
{
    unsigned char complete[QIKVRT_BODY_LENGTH];
    qikvrt_effect_ack_input input;
    qikvrt_effect_ack_state state;

    (void)memset(complete, 1, sizeof(complete));
    complete[12] = QIKVRT_EFFECT_DECISION_RELEASE;
    complete[14] = 0;
    complete[18] = 0;
    complete[19] = 0;
    if (!qikvrt_decode_snapshot(complete, &input)) {
        return 0;
    }
    state = qikvrt_effect_ack_evaluate(&input);
    if (state != QIKVRT_EFFECT_ACK_DONE
            || !qikvrt_effect_ack_ordinary_release(state)) {
        return 0;
    }
    complete[12] = QIKVRT_EFFECT_ACK_DECISION_COUNT;
    if (qikvrt_decode_snapshot(complete, &input)) {
        return 0;
    }
    (void)printf(
        "{\"self_test\":\"PASS\","
        "\"scope\":\"VERIFIED_SNAPSHOT_CORE_ONLY\","
        "\"external_effect\":\"NOT_OBSERVED\"}\n");
    return 1;
}

static int qikvrt_run_server(
    const char *bind_address,
    unsigned short port,
    long max_requests,
    long io_timeout_ms)
{
    int listener;
    int reuse;
    struct sockaddr_in address;
    socklen_t address_length;
    long handled;

    listener = socket(AF_INET, SOCK_STREAM, 0);
    if (listener < 0) {
        (void)fprintf(stderr, "qikvrt_meshd: socket failed\n");
        return 0;
    }
    reuse = 1;
    (void)setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    (void)memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons(port);
    if (inet_pton(AF_INET, bind_address, &address.sin_addr) != 1) {
        (void)fprintf(stderr, "qikvrt_meshd: bind address must be an IPv4 literal\n");
        (void)close(listener);
        return 0;
    }
    if (bind(listener, (struct sockaddr *)&address, sizeof(address)) != 0) {
        (void)fprintf(stderr, "qikvrt_meshd: bind failed\n");
        (void)close(listener);
        return 0;
    }
    if (listen(listener, QIKVRT_LISTEN_BACKLOG) != 0) {
        (void)fprintf(stderr, "qikvrt_meshd: listen failed\n");
        (void)close(listener);
        return 0;
    }
    address_length = (socklen_t)sizeof(address);
    if (getsockname(listener, (struct sockaddr *)&address, &address_length) != 0) {
        (void)fprintf(stderr, "qikvrt_meshd: getsockname failed\n");
        (void)close(listener);
        return 0;
    }
    (void)printf("QIKVRT_MESHD_PORT=%u\n", (unsigned int)ntohs(address.sin_port));
    (void)fflush(stdout);

    handled = 0L;
    while (max_requests == 0L || handled < max_requests) {
        int connection;

        connection = accept(listener, 0, 0);
        if (connection < 0 && errno == EINTR) {
            continue;
        }
        if (connection < 0) {
            (void)fprintf(stderr, "qikvrt_meshd: accept failed\n");
            (void)close(listener);
            return 0;
        }
        qikvrt_handle_connection(connection, io_timeout_ms);
        (void)shutdown(connection, SHUT_RDWR);
        (void)close(connection);
        handled += 1L;
    }
    (void)close(listener);
    return 1;
}

static void qikvrt_usage(const char *program)
{
    (void)fprintf(
        stderr,
        "usage: %s [--self-test] [--bind IPV4] [--port 0..65535] "
        "[--max-requests N] [--io-timeout-ms 1..60000]\n",
        program);
}

int main(int argc, char **argv)
{
    const char *bind_address;
    long port;
    long max_requests;
    long io_timeout_ms;
    int self_test;
    int index;

    bind_address = "127.0.0.1";
    port = 8080L;
    max_requests = 0L;
    io_timeout_ms = 5000L;
    self_test = 0;
    for (index = 1; index < argc; index += 1) {
        if (strcmp(argv[index], "--self-test") == 0) {
            self_test = 1;
        } else if (strcmp(argv[index], "--bind") == 0
                && index + 1 < argc) {
            index += 1;
            bind_address = argv[index];
        } else if (strcmp(argv[index], "--port") == 0
                && index + 1 < argc) {
            index += 1;
            if (!qikvrt_parse_long(argv[index], 0L, 65535L, &port)) {
                qikvrt_usage(argv[0]);
                return 2;
            }
        } else if (strcmp(argv[index], "--max-requests") == 0
                && index + 1 < argc) {
            index += 1;
            if (!qikvrt_parse_long(
                    argv[index], 0L, 2147483647L, &max_requests)) {
                qikvrt_usage(argv[0]);
                return 2;
            }
        } else if (strcmp(argv[index], "--io-timeout-ms") == 0
                && index + 1 < argc) {
            index += 1;
            if (!qikvrt_parse_long(
                    argv[index], 1L, 60000L, &io_timeout_ms)) {
                qikvrt_usage(argv[0]);
                return 2;
            }
        } else {
            qikvrt_usage(argv[0]);
            return 2;
        }
    }
    if (self_test) {
        return qikvrt_self_test() ? 0 : 1;
    }
    (void)signal(SIGPIPE, SIG_IGN);
    return qikvrt_run_server(
        bind_address,
        (unsigned short)port,
        max_requests,
        io_timeout_ms) ? 0 : 1;
}
