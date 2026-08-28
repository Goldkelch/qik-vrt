-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
--
-- Self-checking simulation testbench for the deterministic admission gate.
-- This file is intentionally a simulation artifact: its waits and assertions
-- are not part of the synthesizable gate.  It covers every std_logic value
-- that is decisive for the exact 1/0/1 ACCEPT boundary.
library ieee;
use ieee.std_logic_1164.all;

entity qikvrt_deterministic_admission_gate_tb is
end entity;

architecture testbench of qikvrt_deterministic_admission_gate_tb is
  constant DECISION_CONTINUE : std_logic_vector(1 downto 0) := "00";
  constant DECISION_HOLD     : std_logic_vector(1 downto 0) := "01";
  constant DECISION_ACCEPT   : std_logic_vector(1 downto 0) := "10";
  constant DECISION_BLOCK    : std_logic_vector(1 downto 0) := "11";

  type logic_values_t is array (natural range <>) of std_logic;
  constant NOT_EXACT_ONE  : logic_values_t := ('U', 'X', '0', 'Z', 'W', 'L', 'H', '-');
  constant NOT_EXACT_ZERO : logic_values_t := ('U', 'X', '1', 'Z', 'W', 'L', 'H', '-');

  signal frame_complete_i    : std_logic := '0';
  signal canonical_equal_i   : std_logic := '0';
  signal ambiguity_present_i : std_logic := '0';
  signal decision_o          : std_logic_vector(1 downto 0);
begin
  dut: entity work.qikvrt_deterministic_admission_gate
    port map (
      frame_complete_i => frame_complete_i,
      canonical_equal_i => canonical_equal_i,
      ambiguity_present_i => ambiguity_present_i,
      decision_o => decision_o
    );

  stimulus: process
  begin
    -- The only accepting exact-value combination.
    frame_complete_i <= '1';
    ambiguity_present_i <= '0';
    canonical_equal_i <= '1';
    wait for 1 ns;
    assert decision_o = DECISION_ACCEPT
      report "exact complete/non-ambiguous/canonical frame must ACCEPT"
      severity failure;

    -- Incompleteness has priority, even when other inputs are asserted.
    frame_complete_i <= '0';
    ambiguity_present_i <= '1';
    canonical_equal_i <= '1';
    wait for 1 ns;
    assert decision_o = DECISION_CONTINUE
      report "incomplete frame must CONTINUE before ambiguity classification"
      severity failure;

    -- Every non-exact-'1' frame-complete input is non-admitting CONTINUE.
    for index in NOT_EXACT_ONE'range loop
      frame_complete_i <= NOT_EXACT_ONE(index);
      ambiguity_present_i <= '0';
      canonical_equal_i <= '1';
      wait for 1 ns;
      assert decision_o = DECISION_CONTINUE
        report "non-exact-one frame_complete must CONTINUE"
        severity failure;
    end loop;

    -- Every non-exact-'0' ambiguity value stays visible as HOLD.
    for index in NOT_EXACT_ZERO'range loop
      frame_complete_i <= '1';
      ambiguity_present_i <= NOT_EXACT_ZERO(index);
      canonical_equal_i <= '1';
      wait for 1 ns;
      assert decision_o = DECISION_HOLD
        report "non-exact-zero ambiguity must HOLD"
        severity failure;
    end loop;

    -- With a complete non-ambiguous frame, only exact '1' canonical equality
    -- accepts; every other std_logic value blocks.
    for index in NOT_EXACT_ONE'range loop
      frame_complete_i <= '1';
      ambiguity_present_i <= '0';
      canonical_equal_i <= NOT_EXACT_ONE(index);
      wait for 1 ns;
      assert decision_o = DECISION_BLOCK
        report "non-exact-one canonical equality must BLOCK"
        severity failure;
    end loop;

    report "qikvrt_deterministic_admission_gate_tb PASS" severity note;
    wait;
  end process;
end architecture;
