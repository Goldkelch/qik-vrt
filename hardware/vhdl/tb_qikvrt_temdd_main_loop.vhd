-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
library ieee;
use ieee.std_logic_1164.all;
use std.env.all;

entity tb_qikvrt_temdd_main_loop is
end entity;

architecture test of tb_qikvrt_temdd_main_loop is
  signal stages : std_logic_vector(7 downto 0) := (others => '0');
  signal successor_bound : std_logic := '0';
  signal done_value : std_logic;
  signal advance_value : std_logic;
begin
  dut : entity work.qikvrt_temdd_main_loop
    port map (
      compile_i => stages(7),
      bind_i => stages(6),
      resolve_i => stages(5),
      execute_i => stages(4),
      test_i => stages(3),
      observe_i => stages(2),
      readback_i => stages(1),
      accept_i => stages(0),
      successor_bound_i => successor_bound,
      effect_ack_done_o => done_value,
      advance_o => advance_value
    );

  stimulus : process
    variable v : std_logic_vector(7 downto 0);
  begin
    for n in 0 to 255 loop
      for i in 0 to 7 loop
        if ((n / (2 ** i)) mod 2) = 1 then
          v(i) := '1';
        else
          v(i) := '0';
        end if;
      end loop;
      stages <= v;
      successor_bound <= '0';
      wait for 1 ns;
      if n = 255 then
        assert done_value = '1' severity failure;
      else
        assert done_value = '0' severity failure;
      end if;
      assert advance_value = '0' severity failure;
    end loop;

    stages <= (others => '1');
    successor_bound <= '1';
    wait for 1 ns;
    assert done_value = '1' severity failure;
    assert advance_value = '1' severity failure;
    report "TEMDD_MAIN_LOOP_VHDL_EXECUTED vectors=257" severity note;
    stop;
    wait;
  end process;
end architecture;
