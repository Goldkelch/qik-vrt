-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;
use work.qikvrt_metatransistor_pkg.all;

entity tb_tile is end;
architecture simulation of tb_tile is
  signal clk:std_logic:='0';
  signal reset:std_logic:='1';
  signal input_valid,ready,output_valid:std_logic:='0';
  signal output_ready:std_logic:='1';
  signal a,b,tag,value,result_tag:std_logic_vector(31 downto 0):=(others=>'0');
  signal lut:std_logic_vector(3 downto 0):=(others=>'0');
  signal requested,result_state:qikvrt_state_t:=QIKVRT_OBSERVE;
  signal binding,authority,distinction,drift,value_valid:std_logic:='0';
  function tri(n:integer) return std_logic is
  begin case n is when 0=>return '0';when 1=>return '1';when others=>return 'X';end case;end;
begin
  clk<=not clk after 5 ns;
  dut:entity work.metatransistor_tile port map(
    clk,reset,input_valid,output_ready,ready,output_valid,a,b,tag,lut,requested,
    binding,authority,distinction,drift,value,result_tag,result_state,value_valid);
  process
    file vectors:text open read_mode is "vectors.txt";
    file observed:text open write_mode is "observed.txt";
    variable line_in,line_out:line;
    variable li,ai,bi,ri,bind_i,auth_i,dist_i,drift_i,es,ev:integer;
    variable expected_value,held_value:std_logic_vector(31 downto 0);
    variable held_state:qikvrt_state_t;
    variable index:natural:=0;
  begin
    wait until rising_edge(clk);wait for 1 ns;
    assert output_valid='0' severity failure;
    reset<='0';
    while not endfile(vectors) loop
      readline(vectors,line_in);
      read(line_in,li);read(line_in,ai);read(line_in,bi);read(line_in,ri);
      read(line_in,bind_i);read(line_in,auth_i);read(line_in,dist_i);read(line_in,drift_i);
      read(line_in,es);hread(line_in,expected_value);read(line_in,ev);
      wait until falling_edge(clk);
      lut<=std_logic_vector(to_unsigned(li,4));a<=std_logic_vector(to_unsigned(ai,32));b<=std_logic_vector(to_unsigned(bi,32));
      requested<=std_logic_vector(to_unsigned(ri,2));binding<=tri(bind_i);authority<=tri(auth_i);
      distinction<=tri(dist_i);drift<=tri(drift_i);tag<=std_logic_vector(to_unsigned(index,32));input_valid<='1';output_ready<='1';
      wait until rising_edge(clk);wait for 1 ns;
      assert output_valid='1' and to_integer(unsigned(result_tag))=index report "lost or reordered token" severity failure;
      assert to_integer(unsigned(result_state))=es and value=expected_value and value_valid=tri(ev) report "carrier mismatch" severity failure;
      write(line_out,to_integer(unsigned(result_state)));write(line_out,string'(" "));hwrite(line_out,value);
      write(line_out,string'(" "));write(line_out,ev);writeline(observed,line_out);
      if index mod 17=0 then
        held_value:=value;held_state:=result_state;output_ready<='0';tag<=(others=>'1');
        wait until rising_edge(clk);wait for 1 ns;
        assert ready='0' and output_valid='1' and value=held_value and result_state=held_state
          and to_integer(unsigned(result_tag))=index report "backpressure corruption" severity failure;
        output_ready<='1';
      end if;
      index:=index+1;
    end loop;
    reset<='1';wait until rising_edge(clk);wait for 1 ns;
    assert output_valid='0' and value_valid='0' severity failure;
    report "tile vectors and backpressure PASS count="&integer'image(index);
    stop;wait;
  end process;
end;
