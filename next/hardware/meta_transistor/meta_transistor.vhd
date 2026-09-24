-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity qikvrt_meta_transistor is
  port (
    a, b        : in  std_logic_vector(31 downto 0);
    lut         : in  std_logic_vector(3 downto 0);
    requested   : in  std_logic_vector(1 downto 0);
    binding     : in  std_logic;
    authority   : in  std_logic;
    distinction : in  std_logic;
    drift       : in  std_logic;
    value       : out std_logic_vector(31 downto 0);
    state       : out std_logic_vector(1 downto 0);
    value_valid : out std_logic
  );
end entity;

architecture rtl of qikvrt_meta_transistor is
  constant OBSERVE  : std_logic_vector(1 downto 0) := "00";
  constant HOLD     : std_logic_vector(1 downto 0) := "01";
  constant CONTINUE : std_logic_vector(1 downto 0) := "10";
  signal q : std_logic_vector(1 downto 0);
  signal v : std_logic_vector(31 downto 0);
begin
  process(all)
    variable r : std_logic_vector(31 downto 0);
    variable idx : integer range 0 to 3;
  begin
    q <= HOLD;
    v <= (others => '0');
    if binding='1' and authority='1' and distinction='1' and drift='0'
       and unsigned(requested) <= 2 then
      q <= requested;
      if requested = CONTINUE then
        for i in 0 to 31 loop
          if a(i)='0' and b(i)='0' then idx := 0;
          elsif a(i)='0' and b(i)='1' then idx := 1;
          elsif a(i)='1' and b(i)='0' then idx := 2;
          else idx := 3;
          end if;
          r(i) := lut(idx);
        end loop;
        v <= r;
      end if;
    end if;
  end process;
  state <= q;
  value <= v;
  value_valid <= '1' when q=CONTINUE else '0';
end architecture;
