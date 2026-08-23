/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#include "qikvrt/atari_browser_c89.h"

#include <ctype.h>
#include <string.h>

static int eqi(const char *a, const char *b)
{
    if (a == 0 || b == 0) return 0;
    while (*a != '\0' && *b != '\0') {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
        ++a;
        ++b;
    }
    return *a == '\0' && *b == '\0';
}

static int prefixi(const char *value, const char *prefix)
{
    if (value == 0 || prefix == 0) return 0;
    while (*prefix != '\0') {
        if (*value == '\0'
            || tolower((unsigned char)*value) != tolower((unsigned char)*prefix)) {
            return 0;
        }
        ++value;
        ++prefix;
    }
    return 1;
}

static int copy_slice(char *out, size_t cap, const char *begin, const char *end)
{
    size_t n;
    if (out == 0 || begin == 0 || end == 0 || end < begin || cap == 0U) return 0;
    n = (size_t)(end - begin);
    if (n + 1U > cap) return 0;
    if (n != 0U) memcpy(out, begin, n);
    out[n] = '\0';
    return 1;
}

static int putc_bound(char *out, size_t cap, size_t *len, char value)
{
    if (out == 0 || len == 0 || *len + 1U >= cap) return 0;
    out[*len] = value;
    *len += 1U;
    out[*len] = '\0';
    return 1;
}

static int puts_bound(char *out, size_t cap, size_t *len, const char *value)
{
    if (value == 0) return 0;
    while (*value != '\0') {
        if (!putc_bound(out, cap, len, *value)) return 0;
        ++value;
    }
    return 1;
}

static int put_uint(char *out, size_t cap, size_t *len, unsigned int value)
{
    char digits[16];
    size_t n;
    n = 0U;
    do {
        digits[n++] = (char)('0' + value % 10U);
        value /= 10U;
    } while (value != 0U && n < sizeof(digits));
    while (n != 0U) {
        --n;
        if (!putc_bound(out, cap, len, digits[n])) return 0;
    }
    return 1;
}

qikvrt_atari_browser_status qikvrt_atari_browser_parse_url(
    const char *input,
    qikvrt_atari_browser_url *out)
{
    const char *authority;
    const char *authority_end;
    const char *colon;
    const char *host_end;
    const char *path_end;
    const char *cursor;
    unsigned long port;

    if (input == 0 || out == 0) return QIKVRT_ATARI_BROWSER_BAD_ARGUMENT;
    memset(out, 0, sizeof(*out));
    if (!prefixi(input, "http://")) return QIKVRT_ATARI_BROWSER_UNSUPPORTED_SCHEME;

    authority = input + 7;
    authority_end = authority;
    while (*authority_end != '\0' && *authority_end != '/'
        && *authority_end != '?' && *authority_end != '#') {
        unsigned char ch;
        ch = (unsigned char)*authority_end;
        if (ch <= 0x20U || ch == 0x7fU || ch == '\\' || ch == '@') {
            return QIKVRT_ATARI_BROWSER_INVALID_URL;
        }
        ++authority_end;
    }
    if (authority == authority_end) return QIKVRT_ATARI_BROWSER_INVALID_URL;

    colon = 0;
    cursor = authority;
    while (cursor < authority_end) {
        if (*cursor == ':') colon = cursor;
        ++cursor;
    }
    host_end = colon != 0 ? colon : authority_end;
    if (!copy_slice(out->host, sizeof(out->host), authority, host_end)) {
        return QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL;
    }
    if (out->host[0] == '\0') return QIKVRT_ATARI_BROWSER_INVALID_URL;

    out->port = 80U;
    if (colon != 0) {
        cursor = colon + 1;
        if (cursor == authority_end) return QIKVRT_ATARI_BROWSER_INVALID_URL;
        port = 0UL;
        while (cursor < authority_end) {
            if (!isdigit((unsigned char)*cursor)) return QIKVRT_ATARI_BROWSER_INVALID_URL;
            port = port * 10UL + (unsigned long)(*cursor - '0');
            if (port > 65535UL) return QIKVRT_ATARI_BROWSER_INVALID_URL;
            ++cursor;
        }
        if (port == 0UL) return QIKVRT_ATARI_BROWSER_INVALID_URL;
        out->port = (unsigned int)port;
    }

    path_end = authority_end;
    while (*path_end != '\0' && *path_end != '#') {
        if ((unsigned char)*path_end <= 0x1fU || *path_end == ' ') {
            return QIKVRT_ATARI_BROWSER_INVALID_URL;
        }
        ++path_end;
    }
    if (authority_end == path_end) {
        strcpy(out->path, "/");
    } else if (*authority_end == '?') {
        size_t n;
        n = (size_t)(path_end - authority_end);
        if (n + 2U > sizeof(out->path)) return QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL;
        out->path[0] = '/';
        memcpy(out->path + 1, authority_end, n);
        out->path[n + 1U] = '\0';
    } else if (!copy_slice(out->path, sizeof(out->path), authority_end, path_end)) {
        return QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL;
    }

    out->loopback = eqi(out->host, "localhost") || strcmp(out->host, "127.0.0.1") == 0;
    return QIKVRT_ATARI_BROWSER_OK;
}

qikvrt_atari_browser_status qikvrt_atari_browser_build_http_get(
    const qikvrt_atari_browser_url *url,
    char *out,
    size_t cap)
{
    size_t len;
    if (url == 0 || out == 0 || cap == 0U) return QIKVRT_ATARI_BROWSER_BAD_ARGUMENT;
    if (url->host[0] == '\0' || url->path[0] != '/' || url->port == 0U) {
        return QIKVRT_ATARI_BROWSER_INVALID_URL;
    }
    len = 0U;
    out[0] = '\0';
    if (!puts_bound(out, cap, &len, "GET ")
        || !puts_bound(out, cap, &len, url->path)
        || !puts_bound(out, cap, &len, " HTTP/1.0\r\nHost: ")
        || !puts_bound(out, cap, &len, url->host)) {
        return QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL;
    }
    if (url->port != 80U
        && (!putc_bound(out, cap, &len, ':') || !put_uint(out, cap, &len, url->port))) {
        return QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL;
    }
    if (!puts_bound(out, cap, &len,
            "\r\nConnection: close\r\nUser-Agent: QIKVRT-Atari-C89/1\r\n"
            "Accept: text/html,text/plain\r\n\r\n")) {
        return QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL;
    }
    return QIKVRT_ATARI_BROWSER_OK;
}

qikvrt_atari_browser_status qikvrt_atari_browser_parse_http_response(
    const char *input,
    size_t input_length,
    qikvrt_atari_browser_http_response *out)
{
    const char *end;
    const char *cursor;
    const char *body;
    if (input == 0 || out == 0) return QIKVRT_ATARI_BROWSER_BAD_ARGUMENT;
    memset(out, 0, sizeof(*out));
    if (input_length < 12U || !prefixi(input, "HTTP/1.")) {
        return QIKVRT_ATARI_BROWSER_INVALID_HTTP;
    }
    cursor = input + 9;
    if (!isdigit((unsigned char)cursor[0])
        || !isdigit((unsigned char)cursor[1])
        || !isdigit((unsigned char)cursor[2])) {
        return QIKVRT_ATARI_BROWSER_INVALID_HTTP;
    }
    out->status_code = (cursor[0] - '0') * 100
        + (cursor[1] - '0') * 10 + (cursor[2] - '0');
    end = input + input_length;
    body = 0;
    cursor = input;
    while (cursor + 3 < end) {
        if (cursor[0] == '\r' && cursor[1] == '\n'
            && cursor[2] == '\r' && cursor[3] == '\n') {
            body = cursor + 4;
            break;
        }
        ++cursor;
    }
    if (body == 0) {
        cursor = input;
        while (cursor + 1 < end) {
            if (cursor[0] == '\n' && cursor[1] == '\n') {
                body = cursor + 2;
                break;
            }
            ++cursor;
        }
    }
    if (body == 0) return QIKVRT_ATARI_BROWSER_INVALID_HTTP;
    out->body = body;
    out->body_length = (size_t)(end - body);
    return QIKVRT_ATARI_BROWSER_OK;
}

static int tag_name(const char *begin, const char *end, char *out, size_t cap, int *closing)
{
    size_t n;
    while (begin < end && isspace((unsigned char)*begin)) ++begin;
    *closing = 0;
    if (begin < end && *begin == '/') {
        *closing = 1;
        ++begin;
    }
    while (begin < end && isspace((unsigned char)*begin)) ++begin;
    n = 0U;
    while (begin < end && (isalnum((unsigned char)*begin) || *begin == '-' || *begin == ':')) {
        if (n + 1U >= cap) return 0;
        out[n++] = (char)tolower((unsigned char)*begin++);
    }
    out[n] = '\0';
    return n != 0U;
}

static int tag_attr(
    const char *begin,
    const char *end,
    const char *name,
    char *out,
    size_t cap)
{
    size_t nlen;
    const char *cursor;
    nlen = strlen(name);
    cursor = begin;
    out[0] = '\0';
    while (cursor < end) {
        const char *after;
        const char *value;
        const char *value_end;
        char quote;
        while (cursor < end && isspace((unsigned char)*cursor)) ++cursor;
        if ((size_t)(end - cursor) < nlen || !prefixi(cursor, name)) {
            ++cursor;
            continue;
        }
        after = cursor + nlen;
        if (after < end && !isspace((unsigned char)*after) && *after != '=') {
            ++cursor;
            continue;
        }
        while (after < end && isspace((unsigned char)*after)) ++after;
        if (after >= end || *after != '=') return 0;
        ++after;
        while (after < end && isspace((unsigned char)*after)) ++after;
        if (after >= end) return 0;
        quote = 0;
        if (*after == '"' || *after == '\'') quote = *after++;
        value = after;
        value_end = value;
        while (value_end < end) {
            if ((quote != 0 && *value_end == quote)
                || (quote == 0 && isspace((unsigned char)*value_end))) break;
            ++value_end;
        }
        return copy_slice(out, cap, value, value_end);
    }
    return 0;
}

static int block_tag(const char *name)
{
    static const char *const names[] = {
        "address", "article", "aside", "blockquote", "br", "dd", "div",
        "dl", "dt", "footer", "h1", "h2", "h3", "h4", "h5", "h6",
        "header", "hr", "li", "main", "nav", "ol", "p", "pre",
        "section", "table", "tr", "ul"
    };
    size_t i;
    for (i = 0U; i < sizeof(names) / sizeof(names[0]); ++i) {
        if (eqi(name, names[i])) return 1;
    }
    return 0;
}

static int entity(const char *begin, const char *end, char *value, size_t *consumed)
{
    const char *semi;
    const char *cursor;
    unsigned long number;
    int base;
    semi = begin + 1;
    while (semi < end && semi - begin <= 12 && *semi != ';') ++semi;
    if (semi >= end || *semi != ';') return 0;
    if ((size_t)(semi - begin) == 4U && strncmp(begin, "&amp", 4U) == 0) *value = '&';
    else if ((size_t)(semi - begin) == 3U && strncmp(begin, "&lt", 3U) == 0) *value = '<';
    else if ((size_t)(semi - begin) == 3U && strncmp(begin, "&gt", 3U) == 0) *value = '>';
    else if ((size_t)(semi - begin) == 5U && strncmp(begin, "&quot", 5U) == 0) *value = '"';
    else if ((size_t)(semi - begin) == 5U && strncmp(begin, "&apos", 5U) == 0) *value = '\'';
    else if (begin + 2 < semi && begin[1] == '#') {
        cursor = begin + 2;
        base = 10;
        if (cursor < semi && (*cursor == 'x' || *cursor == 'X')) {
            base = 16;
            ++cursor;
        }
        number = 0UL;
        if (cursor >= semi) return 0;
        while (cursor < semi) {
            unsigned int digit;
            if (isdigit((unsigned char)*cursor)) digit = (unsigned int)(*cursor - '0');
            else if (base == 16 && *cursor >= 'a' && *cursor <= 'f') digit = (unsigned int)(*cursor - 'a' + 10);
            else if (base == 16 && *cursor >= 'A' && *cursor <= 'F') digit = (unsigned int)(*cursor - 'A' + 10);
            else return 0;
            if (digit >= (unsigned int)base) return 0;
            number = number * (unsigned long)base + (unsigned long)digit;
            if (number == 0UL || number > 255UL) return 0;
            ++cursor;
        }
        *value = (char)number;
    } else return 0;
    *consumed = (size_t)(semi - begin + 1);
    return 1;
}

static void newline(qikvrt_atari_browser_document *out)
{
    if (out->text_length != 0U && out->text[out->text_length - 1U] != '\n'
        && !putc_bound(out->text, sizeof(out->text), &out->text_length, '\n')) {
        out->truncated = 1;
    }
}

static void text_char(qikvrt_atari_browser_document *out, char value, int preserve)
{
    if (!preserve && isspace((unsigned char)value)) {
        if (out->text_length == 0U || out->text[out->text_length - 1U] == ' '
            || out->text[out->text_length - 1U] == '\n') return;
        value = ' ';
    }
    if (!putc_bound(out->text, sizeof(out->text), &out->text_length, value)) {
        out->truncated = 1;
    }
}

static void link_char(qikvrt_atari_browser_document *out, size_t index, char value)
{
    size_t len;
    if (index >= out->link_count) return;
    len = strlen(out->links[index].text);
    if (isspace((unsigned char)value)) {
        if (len == 0U || out->links[index].text[len - 1U] == ' ') return;
        value = ' ';
    }
    (void)putc_bound(out->links[index].text, sizeof(out->links[index].text), &len, value);
}

qikvrt_atari_browser_status qikvrt_atari_browser_render_html(
    const char *html,
    size_t html_length,
    qikvrt_atari_browser_document *out)
{
    const char *cursor;
    const char *end;
    size_t title_len;
    size_t active_link;
    int in_head;
    int in_title;
    int in_pre;
    int skip_script;
    int skip_style;

    if (html == 0 || out == 0) return QIKVRT_ATARI_BROWSER_BAD_ARGUMENT;
    memset(out, 0, sizeof(*out));
    cursor = html;
    end = html + html_length;
    title_len = 0U;
    active_link = QIKVRT_ATARI_BROWSER_LINK_CAPACITY;
    in_head = in_title = in_pre = skip_script = skip_style = 0;

    while (cursor < end) {
        if (*cursor == '<') {
            const char *tag_end;
            char name[32];
            int closing;
            if (cursor + 3 < end && strncmp(cursor, "<!--", 4U) == 0) {
                const char *comment_end;
                comment_end = cursor + 4;
                while (comment_end + 2 < end
                    && !(comment_end[0] == '-' && comment_end[1] == '-'
                        && comment_end[2] == '>')) ++comment_end;
                if (comment_end + 2 >= end) return QIKVRT_ATARI_BROWSER_INVALID_HTML;
                cursor = comment_end + 3;
                continue;
            }
            tag_end = cursor + 1;
            while (tag_end < end && *tag_end != '>') ++tag_end;
            if (tag_end >= end) return QIKVRT_ATARI_BROWSER_INVALID_HTML;
            if (!tag_name(cursor + 1, tag_end, name, sizeof(name), &closing)) {
                cursor = tag_end + 1;
                continue;
            }
            if (eqi(name, "script")) skip_script = closing ? 0 : 1;
            else if (eqi(name, "style")) skip_style = closing ? 0 : 1;
            else if (!skip_script && !skip_style) {
                if (eqi(name, "head")) in_head = closing ? 0 : 1;
                if (eqi(name, "title")) in_title = closing ? 0 : 1;
                if (eqi(name, "pre")) in_pre = closing ? 0 : 1;
                if (eqi(name, "a")) {
                    if (closing) active_link = QIKVRT_ATARI_BROWSER_LINK_CAPACITY;
                    else if (out->link_count < QIKVRT_ATARI_BROWSER_LINK_CAPACITY
                        && tag_attr(cursor + 1, tag_end, "href",
                            out->links[out->link_count].href,
                            sizeof(out->links[out->link_count].href))) {
                        active_link = out->link_count++;
                    }
                }
                if (eqi(name, "li") && !closing) {
                    newline(out);
                    text_char(out, '*', 0);
                    text_char(out, ' ', 0);
                } else if (block_tag(name)) newline(out);
            }
            cursor = tag_end + 1;
            continue;
        }
        if (!skip_script && !skip_style) {
            char value;
            size_t used;
            value = *cursor;
            used = 1U;
            if (*cursor == '&') (void)entity(cursor, end, &value, &used);
            if (!in_head) text_char(out, value, in_pre);
            if (in_title && !putc_bound(out->title, sizeof(out->title), &title_len, value)) {
                out->truncated = 1;
            }
            if (active_link < out->link_count) link_char(out, active_link, value);
            cursor += used;
        } else ++cursor;
    }
    while (out->text_length != 0U
        && (out->text[out->text_length - 1U] == ' '
            || out->text[out->text_length - 1U] == '\n')) {
        out->text[--out->text_length] = '\0';
    }
    return QIKVRT_ATARI_BROWSER_OK;
}

int qikvrt_atari_browser_url_is_loopback(const qikvrt_atari_browser_url *url)
{
    return url != 0 && url->loopback != 0;
}

const char *qikvrt_atari_browser_status_name(qikvrt_atari_browser_status status)
{
    switch (status) {
    case QIKVRT_ATARI_BROWSER_OK: return "OK";
    case QIKVRT_ATARI_BROWSER_BAD_ARGUMENT: return "BAD_ARGUMENT";
    case QIKVRT_ATARI_BROWSER_UNSUPPORTED_SCHEME: return "UNSUPPORTED_SCHEME";
    case QIKVRT_ATARI_BROWSER_INVALID_URL: return "INVALID_URL";
    case QIKVRT_ATARI_BROWSER_BUFFER_TOO_SMALL: return "BUFFER_TOO_SMALL";
    case QIKVRT_ATARI_BROWSER_INVALID_HTTP: return "INVALID_HTTP";
    case QIKVRT_ATARI_BROWSER_INVALID_HTML: return "INVALID_HTML";
    }
    return "UNKNOWN_STATUS";
}
