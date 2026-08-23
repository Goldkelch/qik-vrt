/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#include "qikvrt/atari_browser_c89.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;

static void expect_true(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures += 1;
    }
}

static void test_url_and_request(void)
{
    qikvrt_atari_browser_url url;
    char request[QIKVRT_ATARI_BROWSER_REQUEST_CAPACITY];
    qikvrt_atari_browser_status status;

    status = qikvrt_atari_browser_parse_url(
        "http://127.0.0.1:8771/a/b?x=1#ignored",
        &url);
    expect_true(status == QIKVRT_ATARI_BROWSER_OK, "parse bounded URL");
    expect_true(strcmp(url.host, "127.0.0.1") == 0, "parse host");
    expect_true(url.port == 8771U, "parse port");
    expect_true(strcmp(url.path, "/a/b?x=1") == 0, "strip fragment");
    expect_true(qikvrt_atari_browser_url_is_loopback(&url), "loopback marker");

    status = qikvrt_atari_browser_build_http_get(&url, request, sizeof(request));
    expect_true(status == QIKVRT_ATARI_BROWSER_OK, "build request");
    expect_true(strstr(request, "GET /a/b?x=1 HTTP/1.0\r\n") == request,
        "request line");
    expect_true(strstr(request, "Host: 127.0.0.1:8771\r\n") != 0,
        "host header");
    expect_true(strstr(request, "Connection: close\r\n") != 0,
        "connection close");

    status = qikvrt_atari_browser_parse_url("https://example.org/", &url);
    expect_true(status == QIKVRT_ATARI_BROWSER_UNSUPPORTED_SCHEME,
        "fail closed without TLS implementation");
}

static void test_http_and_html(void)
{
    static const char response[] =
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: text/html\r\n"
        "Content-Length: 192\r\n"
        "\r\n"
        "<!doctype html><html><head><title>QIK &amp; VRT</title>"
        "<style>hidden style</style><script>hidden script</script></head>"
        "<body><h1>Atari Browser</h1><p>Hello &lt;world&gt;.</p>"
        "<ul><li>One</li><li><a href=\"/two\">Two</a></li></ul>"
        "<pre>A  B\nC</pre></body></html>";
    qikvrt_atari_browser_http_response parsed;
    qikvrt_atari_browser_document document;
    qikvrt_atari_browser_status status;

    status = qikvrt_atari_browser_parse_http_response(
        response,
        sizeof(response) - 1U,
        &parsed);
    expect_true(status == QIKVRT_ATARI_BROWSER_OK, "parse HTTP response");
    expect_true(parsed.status_code == 200, "status code");
    expect_true(parsed.body_length > 0U, "body length");

    status = qikvrt_atari_browser_render_html(parsed.body, parsed.body_length, &document);
    expect_true(status == QIKVRT_ATARI_BROWSER_OK, "render HTML");
    expect_true(strcmp(document.title, "QIK & VRT") == 0, "title text");
    expect_true(strstr(document.text, "Atari Browser") != 0, "heading text");
    expect_true(strstr(document.text, "Hello <world>.") != 0,
        "entity decode");
    expect_true(strstr(document.text, "hidden script") == 0,
        "script suppressed");
    expect_true(strstr(document.text, "hidden style") == 0,
        "style suppressed");
    expect_true(document.link_count == 1U, "link count");
    expect_true(strcmp(document.links[0].href, "/two") == 0,
        "link href");
    expect_true(strcmp(document.links[0].text, "Two") == 0,
        "link label");
    expect_true(strstr(document.text, "A  B\nC") != 0,
        "pre whitespace preserved");
    expect_true(document.truncated == 0, "document not truncated");
}

static void test_fail_closed_inputs(void)
{
    qikvrt_atari_browser_http_response response;
    qikvrt_atari_browser_document document;
    qikvrt_atari_browser_status status;

    status = qikvrt_atari_browser_parse_http_response("not http", 8U, &response);
    expect_true(status == QIKVRT_ATARI_BROWSER_INVALID_HTTP,
        "invalid HTTP blocked");

    status = qikvrt_atari_browser_render_html(
        "<p unterminated",
        15U,
        &document);
    expect_true(status == QIKVRT_ATARI_BROWSER_INVALID_HTML,
        "unterminated tag blocked");
}

int main(void)
{
    test_url_and_request();
    test_http_and_html();
    test_fail_closed_inputs();

    if (failures != 0) {
        fprintf(stderr, "QIKVRT Atari browser C89: %d failure(s)\n", failures);
        return 1;
    }
    puts("QIKVRT Atari browser C89: PASS (bounded clean-room capsule)");
    return 0;
}
