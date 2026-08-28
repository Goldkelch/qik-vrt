-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use work.qikvrt_metatransistor_pkg.all;

entity qikvrt_metatransistor is
  port (
    clk_i                  : in  std_logic;
    reset_i                : in  std_logic;
    enable_i               : in  std_logic;
    binding_valid_i        : in  std_logic;
    authority_valid_i      : in  std_logic;
    parent_child_differ_i  : in  std_logic;
    drift_detected_i       : in  std_logic;
    requested_state_i      : in  qikvrt_state_t;
    emitted_state_o        : out qikvrt_state_t;
    receipt_valid_o        : out std_logic;
    pass_o                 : out std_logic;
    final_pass_o           : out std_logic;
    effect_ack_done_o      : out std_logic
  );
end entity;

architecture rtl of qikvrt_metatransistor is
  signal state_q         : qikvrt_state_t := QIKVRT_OBSERVE;
  signal receipt_valid_q : std_logic := '0';
begin
  process (clk_i)
  begin
    if rising_edge(clk_i) then
      if reset_i = '1' then
        state_q         <= QIKVRT_OBSERVE;
        receipt_valid_q <= '0';
      elsif enable_i = '1' then
        state_q <= normalize_state(
          requested_state_i,
          binding_valid_i,
          authority_valid_i,
          parent_child_differ_i,
          drift_detected_i
        );
        receipt_valid_q <= '1';
      else
        receipt_valid_q <= '0';
      end if;
    end if;
  end process;

  emitted_state_o   <= state_q;
  receipt_valid_o   <= receipt_valid_q;
  pass_o            <= '0';
  final_pass_o      <= '0';
  effect_ack_done_o <= '0';
end architecture;
