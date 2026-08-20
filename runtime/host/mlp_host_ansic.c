/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * QIK-VRT MLP Ubuntu host bridge, strict ANSI C89.
 *
 * One-shot bridge: validate the exact Atari REQUESTED frame, delegate only a
 * bounded Firefox launch to the existing QIK-VRT proxy, then persist a local
 * execution receipt.  It never upgrades browser launch to OBSERVED or
 * ACKNOWLEDGED.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FRAME 512

static const char expected_frame[] =
    "QIKMLP1\r\n"
    "PROGRAM MLP\r\n"
    "ACTION OPEN_FIREFOX\r\n"
    "STATE REQUESTED\r\n"
    "AUTHORITY MISSING\r\n"
    "EFFECT REQUESTED\r\n"
    "END\r\n";

static const char delegate_command[] =
    "python3 -B tools/qikvrt_firefox_proxy_delegate.py "
    "--url https://github.com/Goldkelch/qik-vrt/blob/main/AI "
    "--expected-owner Goldkelch "
    "--repository Goldkelch/qik-vrt";

static int read_exact(const char *path, char *buffer, size_t capacity)
{
    FILE *fp;
    size_t n;
    int extra;
    fp = fopen(path, "rb");
    if (fp == NULL)
        return 1;
    n = fread(buffer, 1U, capacity - 1U, fp);
    extra = fgetc(fp);
    fclose(fp);
    if (extra != EOF)
        return 1;
    buffer[n] = '\0';
    if (strcmp(buffer, expected_frame) != 0)
        return 1;
    return 0;
}

static int write_receipt(const char *path)
{
    FILE *fp;
    static const char receipt[] =
        "QIKMLPHOST1\n"
        "ACTION OPEN_FIREFOX\n"
        "REQUEST_STATE REQUESTED\n"
        "HOST_STATE BROWSER_LAUNCH_EXECUTED\n"
        "OBSERVED false\n"
        "ACKNOWLEDGED false\n"
        "NEXT REOBSERVE\n"
        "END\n";
    fp = fopen(path, "wb");
    if (fp == NULL)
        return 1;
    if (fwrite(receipt, 1U, sizeof(receipt) - 1U, fp) != sizeof(receipt) - 1U) {
        fclose(fp);
        return 1;
    }
    if (fclose(fp) != 0)
        return 1;
    return 0;
}

int main(int argc, char **argv)
{
    char frame[MAX_FRAME];
    int rc;
    if (argc != 3) {
        fprintf(stderr, "usage: %s MLP.OPEN MLP.HOST\n", argv[0]);
        return 64;
    }
    if (read_exact(argv[1], frame, sizeof(frame)) != 0) {
        fprintf(stderr, "HOLD: invalid or absent MLP request\n");
        return 2;
    }

    rc = system(delegate_command);
    if (rc != 0) {
        fprintf(stderr, "HOLD: Firefox proxy delegation failed\n");
        return 3;
    }
    if (write_receipt(argv[2]) != 0) {
        fprintf(stderr, "HOLD: host receipt persistence failed\n");
        return 4;
    }

    printf("MLP_HOST_STATE=BROWSER_LAUNCH_EXECUTED\n");
    printf("OBSERVED=false\n");
    printf("ACKNOWLEDGED=false\n");
    printf("NEXT=REOBSERVE\n");
    return 0;
}
