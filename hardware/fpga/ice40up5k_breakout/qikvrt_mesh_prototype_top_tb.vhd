-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
--
-- Self-checking simulation testbench for the reset-bound one-shot iCE40
-- prototype top.  It verifies one protected loopback reaches the visible
-- deterministic ACCEPT state and that the green serialization indicator has
-- exactly one rising burst over the bounded observation window.
library ieee;
use ieee.std_logic_1164.all;

entity qikvrt_mesh_prototype_top_tb is
end entity;

architecture testbench of qikvrt_mesh_prototype_top_tb is
  signal clock_12mhz : std_logic := '0';
  signal led_blue : std_logic;
  signal led_green : std_logic;
  signal led_red : std_logic;
  signal green_launches : natural := 0;
begin
  clock_12mhz <= not clock_12mhz after 5 ns;

  dut: entity work.qikvrt_mesh_prototype_top
    port map (
      clock_12mhz => clock_12mhz,
      led_blue => led_blue,
      led_green => led_green,
      led_red => led_red
    );

  green_monitor: process (clock_12mhz)
    variable prior_green : std_logic := '0';
  begin
    if rising_edge(clock_12mhz) then
      if led_green = '1' and prior_green /= '1' then
        green_launches <= green_launches + 1;
      end if;
      prior_green := led_green;
    end if;
  end process;

  stimulus: process
  begin
    -- 16 reset cycles, one launch cycle and one 104-bit protected wire frame
    -- fit comfortably in this finite test window.
    for index in 1 to 160 loop
      wait until rising_edge(clock_12mhz);
    end loop;
    wait for 1 ns;
    assert led_blue = '0'
      report "prototype must leave reset"
      severity failure;
    assert led_red = '1'
      report "exact protected loopback must reach deterministic ACCEPT"
      severity failure;
    assert green_launches = 1
      report "reset-bound one-shot must never start a second frame"
      severity failure;
    report "qikvrt_mesh_prototype_top_tb PASS" severity note;
    wait;
  end process;
end architecture;
