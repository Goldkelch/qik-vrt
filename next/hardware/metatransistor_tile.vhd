-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.qikvrt_metatransistor_pkg.all;

-- A composable one-entry ready/valid tile with 32 parallel programmable
-- Boolean lanes. Tags and results remain stable under backpressure.
entity metatransistor_tile is
  port (
    clk_i, reset_i, in_valid_i, out_ready_i : in std_logic;
    in_ready_o, out_valid_o : out std_logic;
    a_i, b_i, tag_i : in std_logic_vector(31 downto 0);
    lut_i : in std_logic_vector(3 downto 0);
    requested_i : in qikvrt_state_t;
    binding_i, authority_i, distinction_i, drift_i : in std_logic;
    value_o, tag_o : out std_logic_vector(31 downto 0);
    state_o : out qikvrt_state_t;
    value_valid_o : out std_logic
  );
end entity;

architecture rtl of metatransistor_tile is
  signal valid_q : std_logic := '0';
  signal ready : std_logic;
  signal state_q : qikvrt_state_t := QIKVRT_OBSERVE;
  signal value_q, tag_q : std_logic_vector(31 downto 0) := (others=>'0');
  function known(v:std_logic_vector) return boolean is
  begin
    for n in v'range loop
      if v(n)/='0' and v(n)/='1' then return false; end if;
    end loop;
    return true;
  end function;
begin
  ready <= '1' when reset_i='0' and (valid_q='0' or out_ready_i='1') else '0';
  in_ready_o <= ready;
  out_valid_o <= valid_q;
  state_o <= state_q;
  value_o <= value_q;
  tag_o <= tag_q;
  value_valid_o <= '1' when valid_q='1' and state_q=QIKVRT_CONTINUE else '0';
  process(clk_i)
    variable normalized:qikvrt_state_t;
    variable v:std_logic_vector(31 downto 0);
    variable pair:std_logic_vector(1 downto 0);
  begin
    if rising_edge(clk_i) then
      if reset_i/='0' then
        valid_q<='0';state_q<=QIKVRT_OBSERVE;
        value_q<=(others=>'0');tag_q<=(others=>'0');
      elsif ready='1' then
        valid_q<='0';
        if in_valid_i='1' then
          normalized:=normalize_state(requested_i,binding_i,authority_i,distinction_i,drift_i);
          -- Preserve the source package bytes while closing its unknown-drift case.
          if drift_i/='0' or not known(a_i) or not known(b_i)
            or not known(lut_i) or not known(tag_i) then normalized:=QIKVRT_HOLD; end if;
          v:=(others=>'0');
          if normalized=QIKVRT_CONTINUE then
            for n in 0 to 31 loop
              pair:=a_i(n)&b_i(n);
              case pair is
                when "00"=>v(n):=lut_i(0);
                when "01"=>v(n):=lut_i(1);
                when "10"=>v(n):=lut_i(2);
                when "11"=>v(n):=lut_i(3);
                when others=>v(n):='0';
              end case;
            end loop;
          end if;
          state_q<=normalized;value_q<=v;tag_q<=tag_i;valid_q<='1';
        end if;
      end if;
    end if;
  end process;
end architecture;
