-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
--
-- Synthesizable finite-frame serializer/deserializer for a square QIK-VRT
-- mesh.  The finite generic NODES maps to NODES*NODES lanes.  Lane
-- (row,column) occupies bits ((row*NODES+column)*WORD_BITS)+bit, transmitted
-- least-significant bit first.
--
-- A wire frame carries a fixed sync field, an exact configured session, a
-- monotonically expected sequence field, the canonical payload and a
-- CRC-16/CCITT integrity tag.  The receiver does not release a payload as
-- valid unless every received field and the configured session are binary, the
-- sync/session/sequence are exact, and the received tag equals the locally
-- recomputed tag.  A short frame remains incomplete; the modeled faults that
-- produce one of those mismatches become an integrity failure rather than an
-- accepting frame.  CRC-16 is an error-detection tag, not a claim of
-- cryptographic authenticity, universal channel-corruption detection, or
-- physical fault-free transport.  There are no delays, waits, clocks generated
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
    -- The session value is provisioned by the enclosing endpoint/control plane.
    -- It must be binary and stable for one received frame, and fresh when
    -- cross-reset replay separation is required.
    session_i        : in  std_logic_vector(31 downto 0);
    tx_start_i       : in  std_logic;
    tx_ready_i       : in  std_logic;
    tx_valid_o       : out std_logic;
    tx_bit_o         : out std_logic;
    rx_valid_i       : in  std_logic;
    rx_bit_i         : in  std_logic;
    rx_ready_i       : in  std_logic;
    lanes_o          : out std_logic_vector(NODES * NODES * WORD_BITS - 1 downto 0);
    rx_frame_complete_o : out std_logic;
    rx_integrity_valid_o : out std_logic;
    rx_integrity_failure_o : out std_logic;
    -- Compatibility pulse: exact alias of rx_integrity_valid_o.  It is never
    -- asserted for a merely width-complete but unverified wire frame.
    rx_frame_valid_o : out std_logic
  );
end entity;

architecture rtl of qikvrt_mesh_quadratic_codec is
  constant FRAME_BITS : positive := NODES * NODES * WORD_BITS;
  constant FRAME_SYNC_BITS : positive := 8;
  constant FRAME_SESSION_BITS : positive := 32;
  constant FRAME_SEQUENCE_BITS : positive := 16;
  constant FRAME_DIGEST_BITS : positive := 16;
  constant FRAME_WIRE_BITS : positive :=
    FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + FRAME_BITS +
    FRAME_DIGEST_BITS;
  constant FRAME_SYNC : std_logic_vector(FRAME_SYNC_BITS - 1 downto 0) := x"A5";
  -- The single serial ready/valid edge transfers one payload bit per accepted
  -- handshake.  Therefore a no-stall raw frame needs FRAME_BITS handshakes;
  -- this is not a receipt, hash, persistence, or network-throughput claim.
  constant SERIAL_PAYLOAD_HANDSHAKES_PER_FRAME : positive := FRAME_BITS;
  -- The protected wire frame has fixed framing overhead.  It is deliberately
  -- accounted separately from the payload-only resource rule above.
  constant SERIAL_WIRE_HANDSHAKES_PER_FRAME : positive := FRAME_WIRE_BITS;
  subtype frame_sequence_t is std_logic_vector(FRAME_SEQUENCE_BITS - 1 downto 0);
  subtype frame_session_t is std_logic_vector(FRAME_SESSION_BITS - 1 downto 0);
  subtype frame_digest_t is std_logic_vector(FRAME_DIGEST_BITS - 1 downto 0);
  subtype frame_wire_t is std_logic_vector(FRAME_WIRE_BITS - 1 downto 0);
  signal tx_wire_frame : frame_wire_t := (others => '0');
  signal rx_wire_frame : frame_wire_t := (others => '0');
  signal rx_frame     : std_logic_vector(FRAME_BITS - 1 downto 0) := (others => '0');
  signal tx_index     : natural range 0 to FRAME_WIRE_BITS - 1 := 0;
  signal rx_index     : natural range 0 to FRAME_WIRE_BITS - 1 := 0;
  signal tx_next_sequence : frame_sequence_t := (others => '0');
  signal rx_expected_sequence : frame_sequence_t := (others => '0');
  -- Capture the configured receive-session context on the first bit of each
  -- attempted wire frame.  The final check also requires the live input to
  -- remain equal, so an in-frame control-plane change fails closed.
  signal rx_session_context : frame_session_t := (others => '0');
  signal tx_sequence_exhausted : std_logic := '0';
  signal rx_sequence_exhausted : std_logic := '0';
  signal tx_active    : std_logic := '0';

  function is_binary(value : std_logic_vector) return boolean is
  begin
    for index in value'range loop
      if value(index) /= '0' and value(index) /= '1' then
        return false;
      end if;
    end loop;
    return true;
  end function;

  function increment_sequence(value : frame_sequence_t) return frame_sequence_t is
    variable result : frame_sequence_t := value;
    variable carry : std_logic := '1';
  begin
    -- This explicit binary increment avoids importing arithmetic packages and
    -- turns any non-binary sequence state into an unknown result that cannot
    -- pass is_binary at the receive boundary.
    for index in 0 to FRAME_SEQUENCE_BITS - 1 loop
      if carry = '1' then
        if value(index) = '0' then
          result(index) := '1';
          carry := '0';
        elsif value(index) = '1' then
          result(index) := '0';
        else
          result := (others => 'X');
          return result;
        end if;
      elsif carry = '0' then
        result(index) := value(index);
      else
        result := (others => 'X');
        return result;
      end if;
    end loop;
    return result;
  end function;

  function sequence_exhausted(value : frame_sequence_t) return boolean is
  begin
    -- The finite counter is deliberately non-wrapping.  A non-binary state is
    -- likewise exhausted rather than being normalized into a reusable value.
    for index in value'range loop
      if value(index) = '0' then
        return false;
      elsif value(index) /= '1' then
        return true;
      end if;
    end loop;
    return true;
  end function;

  function crc16_step(
    crc_i : frame_digest_t;
    bit_i : std_logic
  ) return frame_digest_t is
    variable crc : frame_digest_t := crc_i;
    variable feedback : std_logic;
  begin
    if bit_i /= '0' and bit_i /= '1' then
      return (others => 'X');
    end if;
    feedback := crc(crc'high) xor bit_i;
    crc := crc(crc'high - 1 downto 0) & '0';
    if feedback = '1' then
      crc := crc xor x"1021";
    elsif feedback /= '0' then
      return (others => 'X');
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
    -- Every bound field is processed in its LSB-first wire order.
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
  tx_valid_o <= tx_active;
  tx_bit_o <= tx_wire_frame(tx_index);
  lanes_o <= rx_frame;

  process (clk)
  begin
    if rising_edge(clk) then
      if rst_n = '0' then
        tx_wire_frame <= (others => '0');
        tx_index <= 0;
        tx_next_sequence <= (others => '0');
        tx_sequence_exhausted <= '0';
        tx_active <= '0';
      else
        if tx_start_i = '1' and tx_active = '0' and tx_sequence_exhausted = '0' then
          tx_wire_frame <= encode_wire_frame(lanes_i, session_i, tx_next_sequence);
          tx_index <= 0;
          tx_active <= '1';
        elsif tx_active = '1' and tx_ready_i = '1' then
          if tx_index = FRAME_WIRE_BITS - 1 then
            tx_active <= '0';
            tx_index <= 0;
            if sequence_exhausted(tx_next_sequence) then
              tx_sequence_exhausted <= '1';
            else
              tx_next_sequence <= increment_sequence(tx_next_sequence);
            end if;
          else
            tx_index <= tx_index + 1;
          end if;
        end if;
      end if;
    end if;
  end process;

  process (clk)
    variable candidate_wire : frame_wire_t;
    variable candidate_session : frame_session_t;
    variable candidate_sequence : frame_sequence_t;
    variable candidate_payload : std_logic_vector(FRAME_BITS - 1 downto 0);
    variable candidate_digest : frame_digest_t;
  begin
    if rising_edge(clk) then
      rx_frame_complete_o <= '0';
      rx_integrity_valid_o <= '0';
      rx_integrity_failure_o <= '0';
      rx_frame_valid_o <= '0';
      if rst_n = '0' then
        rx_wire_frame <= (others => '0');
        rx_frame <= (others => '0');
        rx_index <= 0;
        rx_expected_sequence <= (others => '0');
        rx_sequence_exhausted <= '0';
      elsif rx_valid_i = '1' and rx_ready_i = '1' then
        if rx_index = 0 then
          rx_session_context <= session_i;
        end if;
        rx_wire_frame(rx_index) <= rx_bit_i;
        if rx_index = FRAME_WIRE_BITS - 1 then
          candidate_wire := rx_wire_frame;
          candidate_wire(rx_index) := rx_bit_i;
          candidate_sequence := candidate_wire(
            FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS - 1 downto
            FRAME_SYNC_BITS + FRAME_SESSION_BITS
          );
          candidate_session := candidate_wire(
            FRAME_SYNC_BITS + FRAME_SESSION_BITS - 1 downto FRAME_SYNC_BITS
          );
          candidate_payload := candidate_wire(
            FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + FRAME_BITS - 1 downto
            FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS
          );
          candidate_digest := candidate_wire(
            FRAME_WIRE_BITS - 1 downto
            FRAME_SYNC_BITS + FRAME_SESSION_BITS + FRAME_SEQUENCE_BITS + FRAME_BITS
          );
          rx_index <= 0;
          rx_frame_complete_o <= '1';
          if is_binary(candidate_wire)
             and is_binary(rx_session_context)
             and is_binary(session_i)
             and candidate_wire(FRAME_SYNC_BITS - 1 downto 0) = FRAME_SYNC
             and candidate_session = rx_session_context
             and rx_session_context = session_i
             and candidate_sequence = rx_expected_sequence
             and rx_sequence_exhausted = '0'
             and candidate_digest = frame_digest(candidate_session, candidate_sequence, candidate_payload)
          then
            rx_frame <= candidate_payload;
            rx_integrity_valid_o <= '1';
            rx_frame_valid_o <= '1';
            if sequence_exhausted(rx_expected_sequence) then
              rx_sequence_exhausted <= '1';
            else
              rx_expected_sequence <= increment_sequence(rx_expected_sequence);
            end if;
          else
            -- Do not update payload or expected sequence for this observed
            -- framing/tag/session mismatch.  No claim is made that CRC-16
            -- detects every possible channel corruption or constructed collision.
            rx_integrity_failure_o <= '1';
          end if;
        else
          rx_index <= rx_index + 1;
        end if;
      end if;
    end if;
  end process;
end architecture;
