# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
CC ?= cc
AR ?= ar
OUT ?= build
CFLAGS ?= -O2
STRICT = -std=c90 -pedantic-errors -Wall -Wextra -Werror -Iinclude -I../../include
SOURCES = src/qikvrt_kernel.c src/qikvrt_wire_v1.c src/qikvrt_sha256_v1.c src/qikvrt_exchange.c src/qikvrt_bus.c ../../src/effect_ack_core.c
HEADERS = $(wildcard include/*.h) ../../include/qikvrt/effect_ack.h
.PHONY: all test assembly
OBJECTS = $(addprefix $(OUT)/,qikvrt_kernel.o qikvrt_wire_v1.o qikvrt_sha256_v1.o qikvrt_exchange.o qikvrt_bus.o effect_ack_core.o)
all: $(OUT)/libqikvrt_transputer.a $(OUT)/qikvrt-c90 $(OUT)/test-core
$(OUT):
	mkdir -p $(OUT)
$(OUT)/%.o: src/%.c $(HEADERS) | $(OUT)
	$(CC) $(STRICT) $(CFLAGS) -c $< -o $@
$(OUT)/effect_ack_core.o: ../../src/effect_ack_core.c ../../include/qikvrt/effect_ack.h | $(OUT)
	$(CC) $(STRICT) $(CFLAGS) -c $< -o $@
$(OUT)/libqikvrt_transputer.a: $(OBJECTS)
	$(AR) rcs $@ $(OBJECTS)
$(OUT)/qikvrt-c90: $(SOURCES) $(HEADERS) adapters/stdio.c | $(OUT)
	$(CC) $(STRICT) $(CFLAGS) $(SOURCES) adapters/stdio.c -o $@
$(OUT)/test-core: $(SOURCES) $(HEADERS) tests/test_core.c | $(OUT)
	$(CC) $(STRICT) $(CFLAGS) $(SOURCES) tests/test_core.c -o $@
test: all
	$(OUT)/test-core
assembly: $(OUT)/test-core
	$(CC) $(STRICT) $(CFLAGS) -S src/qikvrt_kernel.c -o $(OUT)/qikvrt_kernel.s
	$(CC) $(STRICT) $(CFLAGS) $(OUT)/qikvrt_kernel.s $(filter-out src/qikvrt_kernel.c,$(SOURCES)) tests/test_core.c -o $(OUT)/test-assembly
	$(OUT)/test-assembly
