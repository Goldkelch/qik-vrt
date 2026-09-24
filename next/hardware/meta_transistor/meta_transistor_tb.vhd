library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity qikvrt_meta_transistor_tb is end;
architecture test of qikvrt_meta_transistor_tb is
  signal a,b,value : std_logic_vector(31 downto 0) := (others=>'0');
  signal lut : std_logic_vector(3 downto 0) := "0110"; -- XOR
  signal requested,state : std_logic_vector(1 downto 0) := "10";
  signal binding,authority,distinction : std_logic := '0';
  signal drift,value_valid : std_logic := '0';
begin
  dut: entity work.qikvrt_meta_transistor port map(
    a,b,lut,requested,binding,authority,distinction,drift,value,state,value_valid);
  process
  begin
    a <= x"AAAAAAAA"; b <= x"55555555"; wait for 1 ns;
    assert state="01" and value_valid='0' report "fail-closed binding" severity failure;
    binding<='1'; authority<='1'; distinction<='1'; wait for 1 ns;
    assert state="10" and value_valid='1' and value=x"FFFFFFFF" report "continue/XOR" severity failure;
    drift<='1'; wait for 1 ns;
    assert state="01" and value_valid='0' report "drift must HOLD" severity failure;
    report "META_TRANSISTOR_RTL_SIM_PASS" severity note;
    wait;
  end process;
end architecture;
