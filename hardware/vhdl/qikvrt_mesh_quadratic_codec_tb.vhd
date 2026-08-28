-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
--
-- Self-checking simulation testbench for the protected quadratic codec wire
-- frame.  It is intentionally a simulation artifact: waits and assertions are
-- not part of the synthesizable codec.  It proves the bounded RTL contract
-- that an exact session-bound frame validates and that the modeled short,
-- insertion/reorder, session/replay and digest-failure paths never emit a
-- valid frame.  It does not claim CRC-16 detects arbitrary channel faults.
library ieee;
use ieee.std_logic_1164.all;

entity qikvrt_mesh_quadratic_codec_tb is
end entity;

architecture testbench of qikvrt_mesh_quadratic_codec_tb is
  constant FRAME_BITS : positive := 32;
  constant FRAME_SYNC_BITS : positive := 8;
  constant FRAME_SESSION_BITS : positive := 32;
  constant FRAME_SEQUENCE_BITS : positive := 16;
  constant FRAME_DIGEST_BITS : positive := 16;
  constant FRAME_WIRE_BITS : positive :=
    FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + FRAME_BITS +
    FRAME_DIGEST_BITS;
  constant FRAME_SYNC : std_logic_vector(FRAME_SYNC_BITS - 1 downto 0) := x"A5";
  subtype frame_sequence_t is std_logic_vector(FRAME_SEQUENCE_BITS - 1 downto 0);
  subtype frame_session_t is std_logic_vector(FRAME_SESSION_BITS - 1 downto 0);
  subtype frame_digest_t is std_logic_vector(FRAME_DIGEST_BITS - 1 downto 0);
  subtype frame_wire_t is std_logic_vector(FRAME_WIRE_BITS - 1 downto 0);

  signal clk : std_logic := '0';
  signal rst_n : std_logic := '0';
  signal lanes_i : std_logic_vector(FRAME_BITS - 1 downto 0) := (others => '0');
  signal session_i : std_logic_vector(FRAME_SESSION_BITS - 1 downto 0) := x"11223344";
  signal tx_start_i : std_logic := '0';
  signal tx_ready_i : std_logic := '1';
  signal tx_valid_o : std_logic;
  signal tx_bit_o : std_logic;
  signal rx_valid_i : std_logic := '0';
  signal rx_bit_i : std_logic := '0';
  signal rx_ready_i : std_logic := '1';
  signal lanes_o : std_logic_vector(FRAME_BITS - 1 downto 0);
  signal rx_frame_complete_o : std_logic;
  signal rx_integrity_valid_o : std_logic;
  signal rx_integrity_failure_o : std_logic;
  signal rx_frame_valid_o : std_logic;
  signal canonical_equal_i : std_logic;
  signal admission_decision_o : std_logic_vector(1 downto 0);

  function crc16_step(
    crc_i : frame_digest_t;
    bit_i : std_logic
  ) return frame_digest_t is
    variable crc : frame_digest_t := crc_i;
    variable feedback : std_logic;
  begin
    feedback := crc(crc'high) xor bit_i;
    crc := crc(crc'high - 1 downto 0) & '0';
    if feedback = '1' then
      crc := crc xor x"1021";
    end if;
    return crc;
  end function;

  function frame_digest(
    session : frame_session_t;
    sequence : frame_sequence_t;
    payload : std_logic_vector(FRAME_BITS - 1 downto 0)
  ) return frame_digest_t is
    variable crc : frame_digest_t := x"FFFF";
  begin
    for index in 0 to FRAME_SESSION_BITS - 1 loop
      crc := crc16_step(crc, session(index));
    end loop;
    for index in 0 to FRAME_SEQUENCE_BITS - 1 loop
      crc := crc16_step(crc, sequence(index));
    end loop;
    for index in 0 to FRAME_BITS - 1 loop
      crc := crc16_step(crc, payload(index));
    end loop;
    return crc;
  end function;

  function encode_wire_frame(
    payload : std_logic_vector(FRAME_BITS - 1 downto 0);
    session : frame_session_t;
    sequence : frame_sequence_t
  ) return frame_wire_t is
    variable result : frame_wire_t := (others => '0');
  begin
    result(FRAME_SYNC_BITS - 1 downto 0) := FRAME_SYNC;
    result(FRAME_SYNC_BITS + FRAME_SESSION_BITS - 1 downto FRAME_SYNC_BITS) := session;
    result(FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS - 1 downto
           FRAME_SYNC_BITS + FRAME_SESSION_BITS) := sequence;
    result(FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + FRAME_BITS - 1 downto
           FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS) := payload;
    result(FRAME_WIRE_BITS - 1 downto
           FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + FRAME_BITS) :=
      frame_digest(session, sequence, payload);
    return result;
  end function;
begin
  clk <= not clk after 5 ns;

  dut: entity work.qikvrt_mesh_quadratic_codec
    generic map (NODES => 2, WORD_BITS => 8)
    port map (
      clk => clk,
      rst_n => rst_n,
      lanes_i => lanes_i,
      session_i => session_i,
      tx_start_i => tx_start_i,
      tx_ready_i => tx_ready_i,
      tx_valid_o => tx_valid_o,
      tx_bit_o => tx_bit_o,
      rx_valid_i => rx_valid_i,
      rx_bit_i => rx_bit_i,
      rx_ready_i => rx_ready_i,
      lanes_o => lanes_o,
      rx_frame_complete_o => rx_frame_complete_o,
      rx_integrity_valid_o => rx_integrity_valid_o,
      rx_integrity_failure_o => rx_integrity_failure_o,
      rx_frame_valid_o => rx_frame_valid_o
    );

  canonical_equal_i <= '1' when lanes_o = x"5AA55AA5" else '0';

  admission: entity work.qikvrt_deterministic_admission_gate
    port map (
      frame_complete_i => rx_frame_complete_o,
      canonical_equal_i => canonical_equal_i,
      ambiguity_present_i => not rx_integrity_valid_o,
      decision_o => admission_decision_o
    );

  stimulus: process
    constant PAYLOAD : std_logic_vector(FRAME_BITS - 1 downto 0) := x"5AA55AA5";
    constant SESSION_ZERO : frame_session_t := x"11223344";
    constant SESSION_OTHER : frame_session_t := x"55667788";
    constant SEQUENCE_ZERO : frame_sequence_t := (others => '0');
    variable good_frame : frame_wire_t;
    variable bad_frame : frame_wire_t;

    procedure reset_dut is
    begin
      rst_n <= '0';
      rx_valid_i <= '0';
      wait until rising_edge(clk);
      wait until rising_edge(clk);
      rst_n <= '1';
      wait until rising_edge(clk);
      wait for 1 ns;
    end procedure;

    procedure send_frame(constant frame : frame_wire_t) is
    begin
      -- frame_wire_t is declared downto, but the serial protocol is LSB-first.
      for index in 0 to frame'high loop
        rx_bit_i <= frame(index);
        rx_valid_i <= '1';
        wait until rising_edge(clk);
        wait for 1 ns;
      end loop;
      rx_valid_i <= '0';
    end procedure;

    procedure send_short_frame(constant frame : frame_wire_t) is
    begin
      for index in 0 to frame'high - 1 loop
        rx_bit_i <= frame(index);
        rx_valid_i <= '1';
        wait until rising_edge(clk);
        wait for 1 ns;
      end loop;
      rx_valid_i <= '0';
      wait until rising_edge(clk);
      wait for 1 ns;
    end procedure;

    procedure send_frame_with_session_change(
      constant frame : frame_wire_t;
      constant changed_session : frame_session_t
    ) is
    begin
      for index in 0 to frame'high loop
        if index = 1 then
          session_i <= changed_session;
        end if;
        rx_bit_i <= frame(index);
        rx_valid_i <= '1';
        wait until rising_edge(clk);
        wait for 1 ns;
      end loop;
      rx_valid_i <= '0';
    end procedure;
  begin
    good_frame := encode_wire_frame(PAYLOAD, SESSION_ZERO, SEQUENCE_ZERO);

    reset_dut;
    send_frame(good_frame);
    assert rx_frame_complete_o = '1'
      report "exact protected frame must complete"
      severity failure;
    assert rx_integrity_valid_o = '1' and rx_frame_valid_o = '1'
      report "exact protected frame must validate"
      severity failure;
    assert rx_integrity_failure_o = '0' and lanes_o = PAYLOAD
      report "exact protected frame must deserialize canonically"
      severity failure;
    assert admission_decision_o = "10"
      report "only an exact protected canonical frame may ACCEPT"
      severity failure;

    reset_dut;
    bad_frame := good_frame;
    bad_frame(bad_frame'high) := not bad_frame(bad_frame'high);
    send_frame(bad_frame);
    assert rx_frame_complete_o = '1'
      report "digest-mismatched frame remains width-complete"
      severity failure;
    assert rx_integrity_valid_o = '0' and rx_frame_valid_o = '0'
      report "digest mismatch must not validate"
      severity failure;
    assert rx_integrity_failure_o = '1'
      report "digest mismatch must be visible"
      severity failure;
    assert admission_decision_o /= "10"
      report "modeled digest mismatch must never ACCEPT"
      severity failure;

    reset_dut;
    send_frame(good_frame);
    assert rx_integrity_valid_o = '1'
      report "first sequence zero frame must validate"
      severity failure;
    wait until rising_edge(clk);
    wait for 1 ns;
    send_frame(good_frame);
    assert rx_integrity_valid_o = '0' and rx_frame_valid_o = '0'
      report "sequence/replay mismatch must not validate"
      severity failure;
    assert rx_integrity_failure_o = '1'
      report "sequence/replay mismatch must be visible"
      severity failure;
    assert admission_decision_o /= "10"
      report "modeled sequence/replay mismatch must never ACCEPT"
      severity failure;

    reset_dut;
    session_i <= SESSION_OTHER;
    wait for 1 ns;
    send_frame(good_frame);
    assert rx_integrity_valid_o = '0' and rx_frame_valid_o = '0'
      report "session mismatch must not validate"
      severity failure;
    assert rx_integrity_failure_o = '1' and admission_decision_o /= "10"
      report "modeled session mismatch must remain visible and never ACCEPT"
      severity failure;
    session_i <= SESSION_ZERO;

    reset_dut;
    send_frame_with_session_change(good_frame, SESSION_OTHER);
    assert rx_integrity_valid_o = '0' and rx_frame_valid_o = '0'
      report "in-frame session context change must not validate"
      severity failure;
    assert rx_integrity_failure_o = '1' and admission_decision_o /= "10"
      report "modeled in-frame session context change must remain visible and never ACCEPT"
      severity failure;
    session_i <= SESSION_ZERO;

    reset_dut;
    bad_frame := good_frame;
    -- Two distinct payload bits exchanged in place model a bit reorder.  The
    -- payload width is unchanged, so only the integrity check can reject it.
    bad_frame(FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS) :=
      good_frame(FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + 1);
    bad_frame(FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + 1) :=
      good_frame(FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS);
    send_frame(bad_frame);
    assert rx_integrity_valid_o = '0' and rx_frame_valid_o = '0'
      report "framing fault must not validate"
      severity failure;
    assert rx_integrity_failure_o = '1'
      report "reordered frame must be visible as an integrity failure"
      severity failure;
    assert admission_decision_o /= "10"
      report "modeled reordered frame must never ACCEPT"
      severity failure;

    reset_dut;
    bad_frame := good_frame;
    -- Insert one value at the payload boundary and shift the remaining wire
    -- bits toward the tag.  The final original bit is displaced; the resulting
    -- wire width is still complete, so validation must depend on the tag.
    for index in FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + 1 to bad_frame'high loop
      bad_frame(index) := good_frame(index - 1);
    end loop;
    bad_frame(FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS) := '0';
    send_frame(bad_frame);
    assert rx_integrity_valid_o = '0' and rx_frame_valid_o = '0'
      report "inserted wire bit must not validate"
      severity failure;
    assert rx_integrity_failure_o = '1' and admission_decision_o /= "10"
      report "modeled inserted wire bit must remain visible and never ACCEPT"
      severity failure;

    reset_dut;
    send_short_frame(good_frame);
    assert rx_frame_complete_o = '0' and rx_frame_valid_o = '0'
      report "short/lost wire frame must remain incomplete and not validate"
      severity failure;
    assert admission_decision_o /= "10"
      report "modeled short/lost wire frame must never ACCEPT"
      severity failure;

    report "qikvrt_mesh_quadratic_codec_tb PASS" severity note;
    wait;
  end process;
end architecture;
