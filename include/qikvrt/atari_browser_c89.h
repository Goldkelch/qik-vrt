/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#ifndef QIKVRT_ATARI_BROWSER_C89_H
#define QIKVRT_ATARI_BROWSER_C89_H

#include <stddef.h>

#define QIKVRT_ATARI_BROWSER_HOST_CAPACITY 64
#define QIKVRT_ATARI_BROWSER_PATH_CAPACITY 256
#define QIKVRT_ATARI_BROWSER_TEXT_CAPACITY 4096
#define QIKVRT_ATARI_BROWSER_TITLE_CAPACITY 128
#define QIKVRT_ATARI_BROWSER_LINK_CAPACITY 16
#define QIKVRT_ATARI_BROWSER_LINK_TEXT_CAPACITY 128
#define QIKVRT_ATARI_BROWSER_REQUEST_CAPACITY 512

typedef enum qikvrt_atari_browser_status {
    QIKVRT_ATARI_BROWSER_OK = 0,
    QIKVRT_ATARI_BROWSER_BAD_ARGUMENT = 1,
    QIKVRT_ATARI_BROWSER_UNSUPPORTED_SCHEME = 2,
    QIKVRT_ATARI_BROWSER_INVALID_URL = 3,
    QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL = 4,
    QIKVRT_ATARI_BROWSER_INVALID_HTTP = 5,
    QIKVRT_ATARI_BROWSER_INVALID_HTML = 6
} qikvrt_atari_browser_status;

typedef struct qikvrt_atari_browser_url {
    char host[QIKVRT_ATARI_BROWSER_HOST_CAPACITY];
    unsigned int port;
    char path[QIKVRT_ATARI_BROWSER_PATH_CAPACITY];
    int loopback;
} qikvrt_atari_browser_url;

typedef struct qikvrt_atari_browser_http_response {
    int status_code;
    const char *body;
    size_t body_length;
} qikvrt_atari_browser_http_response;

typedef struct qikvrt_atari_browser_link {
    char href[QIKVRT_ATARI_BROWSER_PATH_CAPACITY];
    char text[QIKVRT_ATARI_BROWSER_LINK_TEXT_CAPACITY];
} qikvrt_atari_browser_link;

typedef struct qikvrt_atari_browser_document {
    char title[QIKVRT_ATARI_BROWSER_TITLE_CAPACITY];
    char text[QIKVRT_ATARI_BROWSER_TEXT_CAPACITY];
    size_t text_length;
    qikvrt_atari_browser_link links[QIKVRT_ATARI_BROWSER_LINK_CAPACITY];
    size_t link_count;
    int truncated;
} qikvrt_atari_browser_document;

qikvrt_atari_browser_status qikvrt_atari_browser_parse_url(
    const char *input,
    qikvrt_atari_browser_url *out);

qikvrt_atari_browser_status qikvrt_atari_browser_build_http_get(
    const qikvrt_atari_browser_url *url,
    char *out,
    size_t out_capacity);

qikvrt_atari_browser_status qikvrt_atari_browser_parse_http_response(
    const char *input,
    size_t input_length,
    qikvrt_atari_browser_http_response *out);

qikvrt_atari_browser_status qikvrt_atari_browser_render_html(
    const char *html,
    size_t html_length,
    qikvrt_atari_browser_document *out);

int qikvrt_atari_browser_url_is_loopback(
    const qikvrt_atari_browser_url *url);

const char *qikvrt_atari_browser_status_name(
    qikvrt_atari_browser_status status);

#endif
