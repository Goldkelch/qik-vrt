-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
-- Lattice iCE40UP5K-B-EVN bring-up top: one finite 2x2 mesh frame is
-- serialized and looped back on-chip.  LEDs expose reset, transmit, and a
-- latched deterministic ACCEPT state.  No generated clock, delay, polling,
-- random source, or sampled decision is present.
library ieee;
use ieee.std_logic_1164.all;

entity qikvrt_mesh_prototype_top is
  port (
    clock_12mhz : in std_logic;
    led_blue    : out std_logic;
    led_green   : out std_logic;
    led_red     : out std_logic
  );
end entity;

architecture rtl of qikvrt_mesh_prototype_top is
  signal reset_count : natural range 0 to 15 := 0;
  signal rst_n       : std_logic := '0';
  signal tx_start    : std_logic := '0';
  signal tx_valid    : std_logic;
  signal tx_bit      : std_logic;
  signal frame_valid : std_logic;
  signal lanes_out   : std_logic_vector(31 downto 0);
  signal canonical_equal : std_logic;
  signal decision : std_logic_vector(1 downto 0);
  signal accepted : std_logic := '0';
begin
  canonical_equal <= '1' when lanes_out = x"5AA55AA5" else '0';

  process (clock_12mhz)
  begin
    if rising_edge(clock_12mhz) then
      if reset_count < 15 then
        reset_count <= reset_count + 1;
        rst_n <= '0';
        tx_start <= '0';
        accepted <= '0';
      else
        rst_n <= '1';
        tx_start <= not tx_valid and not frame_valid and not accepted;
        if decision = "10" then
          accepted <= '1';
        elsif decision = "11" then
          accepted <= '0';
        end if;
      end if;
    end if;
  end process;

  codec: entity work.qikvrt_mesh_quadratic_codec
    generic map (NODES => 2, WORD_BITS => 8)
    port map (
      clk => clock_12mhz, rst_n => rst_n,
      lanes_i => x"5AA55AA5", tx_start_i => tx_start, tx_ready_i => '1',
      tx_valid_o => tx_valid, tx_bit_o => tx_bit,
      rx_valid_i => tx_valid, rx_bit_i => tx_bit, rx_ready_i => '1',
      lanes_o => lanes_out, rx_frame_valid_o => frame_valid
    );

  admission: entity work.qikvrt_deterministic_admission_gate
    port map (
      frame_complete_i => frame_valid,
      canonical_equal_i => canonical_equal,
      ambiguity_present_i => '0',
      decision_o => decision
    );

  led_blue  <= not rst_n;
  led_green <= tx_valid;
  led_red   <= accepted;
end architecture;
