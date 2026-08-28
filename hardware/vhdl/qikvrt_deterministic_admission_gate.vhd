-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
--
-- Deterministic, fail-closed admission for a complete canonical mesh frame.
-- Uncertainty is represented by an explicit ambiguity input and never by a
-- random or sampled branch.  Encodings: 00 CONTINUE, 01 HOLD, 10 ACCEPT,
-- 11 BLOCK.
library ieee;
use ieee.std_logic_1164.all;

entity qikvrt_deterministic_admission_gate is
  port (
    frame_complete_i : in  std_logic;
    canonical_equal_i : in  std_logic;
    ambiguity_present_i : in  std_logic;
    decision_o : out std_logic_vector(1 downto 0)
  );
end entity;

architecture rtl of qikvrt_deterministic_admission_gate is
  constant DECISION_CONTINUE : std_logic_vector(1 downto 0) := "00";
  constant DECISION_HOLD     : std_logic_vector(1 downto 0) := "01";
  constant DECISION_ACCEPT   : std_logic_vector(1 downto 0) := "10";
  constant DECISION_BLOCK    : std_logic_vector(1 downto 0) := "11";
begin
  process (frame_complete_i, canonical_equal_i, ambiguity_present_i)
  begin
    if frame_complete_i /= '1' then
      decision_o <= DECISION_CONTINUE;
    elsif ambiguity_present_i = '1' then
      decision_o <= DECISION_HOLD;
    elsif canonical_equal_i = '1' then
      decision_o <= DECISION_ACCEPT;
    else
      decision_o <= DECISION_BLOCK;
    end if;
  end process;
end architecture;
