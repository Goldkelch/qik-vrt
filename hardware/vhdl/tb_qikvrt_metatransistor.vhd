-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use std.env.all;
use work.qikvrt_metatransistor_pkg.all;

entity tb_qikvrt_metatransistor is
end entity;

architecture test of tb_qikvrt_metatransistor is
  signal clk                 : std_logic := '0';
  signal reset               : std_logic := '1';
  signal enable              : std_logic := '0';
  signal binding_valid       : std_logic := '1';
  signal authority_valid     : std_logic := '1';
  signal parent_child_differ : std_logic := '1';
  signal drift_detected      : std_logic := '0';
  signal requested_state     : qikvrt_state_t := QIKVRT_OBSERVE;
  signal emitted_state       : qikvrt_state_t;
  signal receipt_valid       : std_logic;
  signal pass_value          : std_logic;
  signal final_pass_value    : std_logic;
  signal effect_done_value   : std_logic;
begin
  clk <= not clk after 5 ns;

  dut : entity work.qikvrt_metatransistor
    port map (
      clk_i                 => clk,
      reset_i               => reset,
      enable_i              => enable,
      binding_valid_i       => binding_valid,
      authority_valid_i     => authority_valid,
      parent_child_differ_i => parent_child_differ,
      drift_detected_i      => drift_detected,
      requested_state_i     => requested_state,
      emitted_state_o       => emitted_state,
      receipt_valid_o       => receipt_valid,
      pass_o                => pass_value,
      final_pass_o          => final_pass_value,
      effect_ack_done_o     => effect_done_value
    );

  stimulus : process
  begin
    wait for 12 ns;
    reset <= '0';
    enable <= '1';
    requested_state <= QIKVRT_CONTINUE;
    wait for 10 ns;
    assert emitted_state = QIKVRT_CONTINUE severity failure;
    assert receipt_valid = '1' severity failure;

    drift_detected <= '1';
    wait for 10 ns;
    assert emitted_state = QIKVRT_HOLD severity failure;

    drift_detected <= '0';
    requested_state <= QIKVRT_RESERVED;
    wait for 10 ns;
    assert emitted_state = QIKVRT_HOLD severity failure;

    assert pass_value = '0' severity failure;
    assert final_pass_value = '0' severity failure;
    assert effect_done_value = '0' severity failure;
    stop;
    wait;
  end process;
end architecture;
