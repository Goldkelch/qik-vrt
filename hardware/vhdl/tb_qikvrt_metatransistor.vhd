-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
library ieee;
use ieee.std_logic_1164.all;
use std.env.all;
use work.qikvrt_metatransistor_pkg.all;

entity tb_qikvrt_metatransistor is
end entity;

architecture test of tb_qikvrt_metatransistor is
  signal clk                 : std_logic := '0';
  signal reset               : std_logic := '1';
  signal enable              : std_logic := '0';
  signal binding_valid       : std_logic := '1';
  signal authority_valid     : std_logic := '1';
  signal parent_child_differ : std_logic := '1';
  signal drift_detected      : std_logic := '0';
  signal requested_state     : qikvrt_state_t := QIKVRT_OBSERVE;
  signal emitted_state       : qikvrt_state_t;
  signal receipt_valid       : std_logic;
  signal pass_value          : std_logic;
  signal final_pass_value    : std_logic;
  signal effect_done_value   : std_logic;
begin
  clk <= not clk after 5 ns;

  dut : entity work.qikvrt_metatransistor
    port map (
      clk_i                 => clk,
      reset_i               => reset,
      enable_i              => enable,
      binding_valid_i       => binding_valid,
      authority_valid_i     => authority_valid,
      parent_child_differ_i => parent_child_differ,
      drift_detected_i      => drift_detected,
      requested_state_i     => requested_state,
      emitted_state_o       => emitted_state,
      receipt_valid_o       => receipt_valid,
      pass_o                => pass_value,
      final_pass_o          => final_pass_value,
      effect_ack_done_o     => effect_done_value
    );

  stimulus : process
    variable requested      : qikvrt_state_t;
    variable expected       : qikvrt_state_t;
    variable checked_cases  : natural := 0;
  begin
    -- Regression for the originally reported fail-open drift input.
    assert normalize_state(QIKVRT_CONTINUE, '1', '1', '1', 'X') = QIKVRT_HOLD
      report "Unknown drift must hold rather than continue" severity failure;

    -- Exhaust the function's finite std_logic input domain: 9**6 cases.
    -- The oracle permits a state only with three strong '1' guards and
    -- strong '0' drift. Weak, unknown, high-impedance and don't-care values
    -- are not evidence of a valid guard or drift freedom.
    for hi in std_logic loop
      for lo in std_logic loop
        requested := hi & lo;
        for b in std_logic loop
          for a in std_logic loop
            for p in std_logic loop
              for d in std_logic loop
                expected := QIKVRT_HOLD;
                if b = '1' and a = '1' and p = '1' and d = '0' then
                  case requested is
                    when QIKVRT_OBSERVE  => expected := QIKVRT_OBSERVE;
                    when QIKVRT_CONTINUE => expected := QIKVRT_CONTINUE;
                    when others          => expected := QIKVRT_HOLD;
                  end case;
                end if;
                assert normalize_state(requested, b, a, p, d) = expected
                  report "normalize_state mismatch at case " &
                         natural'image(checked_cases)
                  severity failure;
                checked_cases := checked_cases + 1;
              end loop;
            end loop;
          end loop;
        end loop;
      end loop;
    end loop;
    assert checked_cases = 531441 severity failure;
    report "QIKVRT_METATRANSISTOR_NORMALIZE_CASES=531441" severity note;

    wait for 12 ns;
    reset <= '0';
    enable <= '1';
    requested_state <= QIKVRT_CONTINUE;
    wait for 10 ns;
    assert emitted_state = QIKVRT_CONTINUE severity failure;
    assert receipt_valid = '1' severity failure;

    drift_detected <= '1';
    wait for 10 ns;
    assert emitted_state = QIKVRT_HOLD severity failure;

    drift_detected <= '0';
    requested_state <= QIKVRT_RESERVED;
    wait for 10 ns;
    assert emitted_state = QIKVRT_HOLD severity failure;

    -- Exercise all drift values through the registered entity as well.
    -- Drive on the falling edge and inspect after the following rising edge.
    for d in std_logic loop
      wait until falling_edge(clk);
      requested_state <= QIKVRT_CONTINUE;
      drift_detected <= d;
      wait until rising_edge(clk);
      wait for 1 ns;
      expected := QIKVRT_HOLD;
      if d = '0' then
        expected := QIKVRT_CONTINUE;
      end if;
      assert emitted_state = expected
        report "Registered drift mismatch for " & std_logic'image(d)
        severity failure;
      assert receipt_valid = '1' severity failure;
      assert pass_value = '0' severity failure;
      assert final_pass_value = '0' severity failure;
      assert effect_done_value = '0' severity failure;
    end loop;
    report "QIKVRT_METATRANSISTOR_REGISTERED_DRIFT_CASES=9" severity note;

    assert pass_value = '0' severity failure;
    assert final_pass_value = '0' severity failure;
    assert effect_done_value = '0' severity failure;
    stop;
    wait;
  end process;
end architecture;
