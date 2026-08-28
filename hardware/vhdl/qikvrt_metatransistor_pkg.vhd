-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;

package qikvrt_metatransistor_pkg is
  subtype qikvrt_state_t is std_logic_vector(1 downto 0);
  type qikvrt_state_vector_t is array (natural range <>) of qikvrt_state_t;

  constant QIKVRT_OBSERVE  : qikvrt_state_t := "00";
  constant QIKVRT_HOLD     : qikvrt_state_t := "01";
  constant QIKVRT_CONTINUE : qikvrt_state_t := "10";
  constant QIKVRT_RESERVED : qikvrt_state_t := "11";

  function normalize_state(
    requested_state      : qikvrt_state_t;
    binding_valid        : std_logic;
    authority_valid      : std_logic;
    parent_child_differ  : std_logic;
    drift_detected       : std_logic
  ) return qikvrt_state_t;
end package;

package body qikvrt_metatransistor_pkg is
  function normalize_state(
    requested_state      : qikvrt_state_t;
    binding_valid        : std_logic;
    authority_valid      : std_logic;
    parent_child_differ  : std_logic;
    drift_detected       : std_logic
  ) return qikvrt_state_t is
  begin
    if binding_valid /= '1' or
       authority_valid /= '1' or
       parent_child_differ /= '1' or
       drift_detected = '1' then
      return QIKVRT_HOLD;
    end if;

    case requested_state is
      when QIKVRT_OBSERVE  => return QIKVRT_OBSERVE;
      when QIKVRT_HOLD     => return QIKVRT_HOLD;
      when QIKVRT_CONTINUE => return QIKVRT_CONTINUE;
      when others           => return QIKVRT_HOLD;
    end case;
  end function;
end package body;
