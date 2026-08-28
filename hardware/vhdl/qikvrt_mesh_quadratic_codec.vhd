-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
--
-- Synthesizable finite-frame serializer/deserializer for a square QIK-VRT
-- mesh.  The finite generic NODES maps to NODES*NODES lanes.  Lane
-- (row,column) occupies bits ((row*NODES+column)*WORD_BITS)+bit, transmitted
-- least-significant bit first.  There are no delays, waits, clocks generated
-- in logic, or polling interfaces.
library ieee;
use ieee.std_logic_1164.all;

entity qikvrt_mesh_quadratic_codec is
  generic (
    NODES     : positive := 2;
    WORD_BITS : positive := 8
  );
  port (
    clk              : in  std_logic;
    rst_n            : in  std_logic;
    lanes_i          : in  std_logic_vector(NODES * NODES * WORD_BITS - 1 downto 0);
    tx_start_i       : in  std_logic;
    tx_ready_i       : in  std_logic;
    tx_valid_o       : out std_logic;
    tx_bit_o         : out std_logic;
    rx_valid_i       : in  std_logic;
    rx_bit_i         : in  std_logic;
    rx_ready_i       : in  std_logic;
    lanes_o          : out std_logic_vector(NODES * NODES * WORD_BITS - 1 downto 0);
    rx_frame_valid_o : out std_logic
  );
end entity;

architecture rtl of qikvrt_mesh_quadratic_codec is
  constant FRAME_BITS : positive := NODES * NODES * WORD_BITS;
  -- The single serial ready/valid edge transfers one payload bit per accepted
  -- handshake.  Therefore a no-stall raw frame needs FRAME_BITS handshakes;
  -- this is not a receipt, hash, persistence, or network-throughput claim.
  constant SERIAL_PAYLOAD_HANDSHAKES_PER_FRAME : positive := FRAME_BITS;
  signal tx_frame     : std_logic_vector(FRAME_BITS - 1 downto 0) := (others => '0');
  signal rx_frame     : std_logic_vector(FRAME_BITS - 1 downto 0) := (others => '0');
  signal tx_index     : natural range 0 to FRAME_BITS - 1 := 0;
  signal rx_index     : natural range 0 to FRAME_BITS - 1 := 0;
  signal tx_active    : std_logic := '0';
begin
  tx_valid_o <= tx_active;
  tx_bit_o <= tx_frame(tx_index);
  lanes_o <= rx_frame;

  process (clk)
  begin
    if rising_edge(clk) then
      if rst_n = '0' then
        tx_frame <= (others => '0');
        tx_index <= 0;
        tx_active <= '0';
      else
        if tx_start_i = '1' and tx_active = '0' then
          tx_frame <= lanes_i;
          tx_index <= 0;
          tx_active <= '1';
        elsif tx_active = '1' and tx_ready_i = '1' then
          if tx_index = FRAME_BITS - 1 then
            tx_active <= '0';
            tx_index <= 0;
          else
            tx_index <= tx_index + 1;
          end if;
        end if;
      end if;
    end if;
  end process;

  process (clk)
  begin
    if rising_edge(clk) then
      rx_frame_valid_o <= '0';
      if rst_n = '0' then
        rx_frame <= (others => '0');
        rx_index <= 0;
      elsif rx_valid_i = '1' and rx_ready_i = '1' then
        rx_frame(rx_index) <= rx_bit_i;
        if rx_index = FRAME_BITS - 1 then
          rx_index <= 0;
          rx_frame_valid_o <= '1';
        else
          rx_index <= rx_index + 1;
        end if;
      end if;
    end if;
  end process;
end architecture;
