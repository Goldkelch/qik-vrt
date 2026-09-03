-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_qikvrt_fixed_point_mac is
end entity;

architecture test of tb_qikvrt_fixed_point_mac is
  signal clk         : std_logic := '0';
  signal reset       : std_logic := '1';
  signal clear       : std_logic := '0';
  signal valid       : std_logic := '0';
  signal left_value  : signed(7 downto 0) := (others => '0');
  signal right_value : signed(7 downto 0) := (others => '0');
  signal accumulator : signed(15 downto 0);
  signal accepted    : std_logic;
  signal overflow    : std_logic;
begin
  clk <= not clk after 5 ns;

  dut : entity work.qikvrt_fixed_point_mac
    generic map (OPERAND_WIDTH => 8, ACC_WIDTH => 16)
    port map (
      clk_i => clk, reset_i => reset, clear_i => clear, valid_i => valid,
      left_i => left_value, right_i => right_value,
      accumulator_o => accumulator, accepted_o => accepted, overflow_o => overflow
    );

  stimulus : process
  begin
    wait for 12 ns;
    reset <= '0';
    valid <= '1';
    left_value <= to_signed(3, 8);
    right_value <= to_signed(4, 8);
    wait for 10 ns;
    assert accumulator = to_signed(12, 16) severity failure;
    assert accepted = '1' and overflow = '0' severity failure;

    left_value <= to_signed(-2, 8);
    right_value <= to_signed(5, 8);
    wait for 10 ns;
    assert accumulator = to_signed(2, 16) severity failure;

    valid <= '0';
    clear <= '1';
    wait for 10 ns;
    clear <= '0';
    valid <= '1';
    left_value <= to_signed(127, 8);
    right_value <= to_signed(127, 8);
    wait for 20 ns;
    assert accumulator = to_signed(32258, 16) severity failure;
    wait for 10 ns;
    assert accumulator = to_signed(32258, 16) severity failure;
    assert overflow = '1' and accepted = '0' severity failure;
    stop;
    wait;
  end process;
end architecture;
