/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/* Runtime path compatibility: only the calling process's own executable alias.
   This does not change Lean, its kernel, process permissions or other PID paths. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

ssize_t readlink(const char *path, char *buf, size_t size)
{
    ssize_t (*real_readlink)(const char *, char *, size_t);
    char own_path[64];
    void *symbol = dlsym(RTLD_NEXT, "readlink");
    memcpy(&real_readlink, &symbol, sizeof(real_readlink));
    if (!real_readlink) {
        errno = ENOSYS;
        return -1;
    }
    snprintf(own_path, sizeof(own_path), "/proc/%ld/exe", (long)getpid());
    return real_readlink(strcmp(path, own_path) == 0 ? "/proc/self/exe" : path,
                         buf, size);
}
