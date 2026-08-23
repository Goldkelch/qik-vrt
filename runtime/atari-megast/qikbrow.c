/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#include "qikvrt/atari_browser_c89.h"

#include <stdio.h>

#define QIKBROW_INPUT_CAPACITY 16384U

static char qikbrow_input[QIKBROW_INPUT_CAPACITY];
static qikvrt_atari_browser_document qikbrow_document;

int main(int argc, char **argv)
{
    FILE *stream;
    size_t length;
    qikvrt_atari_browser_status status;

    if (argc != 2) {
        fputs("usage: QIKBROW HTMLFILE\n", stderr);
        return 2;
    }
    stream = fopen(argv[1], "rb");
    if (stream == 0) {
        fputs("QIKBROW: input unavailable\n", stderr);
        return 3;
    }
    length = fread(qikbrow_input, 1U, QIKBROW_INPUT_CAPACITY, stream);
    if (ferror(stream) != 0) {
        fclose(stream);
        fputs("QIKBROW: read failure\n", stderr);
        return 5;
    }
    if (!feof(stream)) {
        fclose(stream);
        fputs("QIKBROW: input exceeds 16 KiB bound\n", stderr);
        return 6;
    }
    fclose(stream);

    status = qikvrt_atari_browser_render_html(
        qikbrow_input,
        length,
        &qikbrow_document);
    if (status != QIKVRT_ATARI_BROWSER_OK) {
        fprintf(stderr, "QIKBROW: %s\n", qikvrt_atari_browser_status_name(status));
        return 7;
    }
    if (qikbrow_document.title[0] != '\0') {
        fputs(qikbrow_document.title, stdout);
        fputs("\n\n", stdout);
    }
    fputs(qikbrow_document.text, stdout);
    fputc('\n', stdout);
    if (qikbrow_document.truncated) {
        fputs("[QIKBROW output truncated]\n", stderr);
    }
    return 0;
}
