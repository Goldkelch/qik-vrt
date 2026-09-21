/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#ifndef QIKVRT_TYPES_H
#define QIKVRT_TYPES_H
#include <limits.h>
#if CHAR_BIT != 8
#error "QVRT v1 octet carrier requires CHAR_BIT == 8"
#endif
#if UINT_MAX == 0xffffffffUL && !defined(QIKVRT_FORCE_LONG32)
typedef unsigned int qikvrt_u32;
#elif ULONG_MAX == 0xffffffffUL
typedef unsigned long qikvrt_u32;
#else
#error "An exact unsigned 32-bit int or long is required"
#endif
/* No stdint, long long, allocation, OS, compiler extension or endianness ABI. */
qikvrt_u32 qikvrt_get32(const unsigned char *p);
void qikvrt_put32(unsigned char *p, qikvrt_u32 v);
#endif
