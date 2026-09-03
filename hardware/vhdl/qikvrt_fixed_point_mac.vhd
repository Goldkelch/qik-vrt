-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity qikvrt_fixed_point_mac is
  generic (
    OPERAND_WIDTH : positive := 8;
    ACC_WIDTH     : positive := 32
  );
  port (
    clk_i       : in  std_logic;
    reset_i     : in  std_logic;
    clear_i     : in  std_logic;
    valid_i     : in  std_logic;
    left_i      : in  signed(OPERAND_WIDTH - 1 downto 0);
    right_i     : in  signed(OPERAND_WIDTH - 1 downto 0);
    accumulator_o : out signed(ACC_WIDTH - 1 downto 0);
    accepted_o  : out std_logic;
    overflow_o  : out std_logic
  );
end entity;

architecture rtl of qikvrt_fixed_point_mac is
  signal accumulator_q : signed(ACC_WIDTH - 1 downto 0) := (others => '0');
  signal accepted_q    : std_logic := '0';
  signal overflow_q    : std_logic := '0';
begin
  assert ACC_WIDTH >= 2 * OPERAND_WIDTH
    report "ACC_WIDTH must hold one full signed product"
    severity failure;

  process (clk_i)
    variable product_v   : signed(2 * OPERAND_WIDTH - 1 downto 0);
    variable candidate_v : signed(ACC_WIDTH downto 0);
  begin
    if rising_edge(clk_i) then
      accepted_q <= '0';
      if reset_i = '1' then
        accumulator_q <= (others => '0');
        overflow_q    <= '0';
      elsif clear_i = '1' then
        accumulator_q <= (others => '0');
        overflow_q    <= '0';
      elsif valid_i = '1' and overflow_q = '0' then
        product_v := left_i * right_i;
        candidate_v := resize(accumulator_q, ACC_WIDTH + 1) + resize(product_v, ACC_WIDTH + 1);
        if candidate_v(ACC_WIDTH) /= candidate_v(ACC_WIDTH - 1) then
          overflow_q <= '1';
        else
          accumulator_q <= candidate_v(ACC_WIDTH - 1 downto 0);
          accepted_q    <= '1';
        end if;
      end if;
    end if;
  end process;

  accumulator_o <= accumulator_q;
  accepted_o    <= accepted_q;
  overflow_o    <= overflow_q;
end architecture;
