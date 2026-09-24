-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
-- Canonical TEMDD bounded terminal predicate.
--
-- This entity does not claim repository/global EFFECT_ACK_DONE. It computes the
-- local conjunction for one exact bound subject. The outer runtime rebinds an
-- accepted successor before the next cycle.
library ieee;
use ieee.std_logic_1164.all;

entity qikvrt_temdd_main_loop is
  port (
    compile_i         : in  std_logic;
    bind_i            : in  std_logic;
    resolve_i         : in  std_logic;
    execute_i         : in  std_logic;
    test_i            : in  std_logic;
    observe_i         : in  std_logic;
    readback_i        : in  std_logic;
    accept_i          : in  std_logic;
    successor_bound_i : in  std_logic;
    effect_ack_done_o : out std_logic;
    advance_o         : out std_logic
  );
end entity;

architecture rtl of qikvrt_temdd_main_loop is
  signal done_s : std_logic;
begin
  done_s <= compile_i and bind_i and resolve_i and execute_i and
            test_i and observe_i and readback_i and accept_i;
  effect_ack_done_o <= done_s;
  advance_o <= done_s and successor_bound_i;
end architecture;
