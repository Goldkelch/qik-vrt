-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use work.qikvrt_metatransistor_pkg.all;

entity qikvrt_neutron_star_mesh is
  generic (
    SECTOR_COUNT  : positive := 8;
    SHELL_COUNT   : positive := 8;
    CARRIER_WIDTH : positive range 8 to 256 := 8
  );
  port (
    clk_i                  : in  std_logic;
    reset_i                : in  std_logic;
    enable_i               : in  std_logic_vector((SECTOR_COUNT * SHELL_COUNT) - 1 downto 0);
    binding_valid_i        : in  std_logic_vector((SECTOR_COUNT * SHELL_COUNT) - 1 downto 0);
    authority_valid_i      : in  std_logic_vector((SECTOR_COUNT * SHELL_COUNT) - 1 downto 0);
    parent_child_differ_i  : in  std_logic_vector((SECTOR_COUNT * SHELL_COUNT) - 1 downto 0);
    drift_detected_i       : in  std_logic_vector((SECTOR_COUNT * SHELL_COUNT) - 1 downto 0);
    requested_state_i      : in  qikvrt_state_vector_t(0 to (SECTOR_COUNT * SHELL_COUNT) - 1);
    carrier_i              : in  std_logic_vector((SECTOR_COUNT * SHELL_COUNT * CARRIER_WIDTH) - 1 downto 0);
    emitted_state_o        : out qikvrt_state_vector_t(0 to (SECTOR_COUNT * SHELL_COUNT) - 1);
    receipt_valid_o        : out std_logic_vector((SECTOR_COUNT * SHELL_COUNT) - 1 downto 0);
    carrier_o              : out std_logic_vector((SECTOR_COUNT * SHELL_COUNT * CARRIER_WIDTH) - 1 downto 0)
  );
end entity;

architecture rtl of qikvrt_neutron_star_mesh is
begin
  shell_g : for shell_index in 0 to SHELL_COUNT - 1 generate
    sector_g : for sector_index in 0 to SECTOR_COUNT - 1 generate
      constant node_index : natural := (shell_index * SECTOR_COUNT) + sector_index;
    begin
      cell_i : entity work.qikvrt_metatransistor
        port map (
          clk_i                 => clk_i,
          reset_i               => reset_i,
          enable_i              => enable_i(node_index),
          binding_valid_i       => binding_valid_i(node_index),
          authority_valid_i     => authority_valid_i(node_index),
          parent_child_differ_i => parent_child_differ_i(node_index),
          drift_detected_i      => drift_detected_i(node_index),
          requested_state_i     => requested_state_i(node_index),
          emitted_state_o       => emitted_state_o(node_index),
          receipt_valid_o       => receipt_valid_o(node_index),
          pass_o                => open,
          final_pass_o          => open,
          effect_ack_done_o     => open
        );
    end generate;
  end generate;

  carrier_o <= carrier_i;
end architecture;
