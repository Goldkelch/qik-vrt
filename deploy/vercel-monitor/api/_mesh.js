import { createHash } from 'node:crypto';

export const FANOUT = 8;
export const RETIREMENT_DEPTH = 9;
export const MAX_MATERIALIZED_DEPTH = 3;
export const TERMINAL_SLOTS = Object.freeze([0, 7]);
export const GATE_NAMES = Object.freeze([
  'QIKVRT CI',
  'QIKVRT repository evidence materialization',
  'QIKVRT Collective Proposal Review',
  'QIKVRT code-owner review observer',
  'QIKVRT live status watch',
  'QIKVRT Spark branch work-unit core',
  'QIKVRT zero-bug continuous invariant',
  'QIKVRT explicit HOLD contract'
]);

function canonical(value) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('NON_FINITE_NUMBER');
    return value;
  }
  if (Array.isArray(value)) return value.map(canonical);
  if (typeof value === 'object') {
    const result = {};
    for (const key of Object.keys(value).sort()) {
      if (value[key] !== undefined) result[key] = canonical(value[key]);
    }
    return result;
  }
  throw new Error('UNSUPPORTED_CANONICAL_VALUE');
}

export function stableStringify(value) {
  return JSON.stringify(canonical(value));
}

export function sha256(value) {
  const bytes = typeof value === 'string' ? value : stableStringify(value);
  return createHash('sha256').update(bytes, 'utf8').digest('hex');
}

function clone(value) {
  return JSON.parse(stableStringify(value));
}

function boundedInteger(name, value, minimum, maximum) {
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${name.toUpperCase()}_OUT_OF_RANGE`);
  }
  return value;
}

export function logicalNodeCount(depth, fanout = FANOUT) {
  boundedInteger('depth', depth, 0, 64);
  boundedInteger('fanout', fanout, 1, 1024);
  if (fanout === 1) return depth + 1;
  return (BigInt(fanout) ** BigInt(depth + 1) - 1n) / BigInt(fanout - 1);
}

function nodeIdentity(rootSubjectSha256, path) {
  return `qnode-${sha256({
    schema: 'qikvrt_metatransistor_node_identity_v1',
    root_subject_sha256: rootSubjectSha256,
    path
  }).slice(0, 24)}`;
}

export function subjectIdentity(subject) {
  return `qsubject-${sha256({
    schema: 'qikvrt_monitor_subject_identity_v1',
    repository: subject.repository || 'Goldkelch/qik-vrt',
    kind: subject.kind || 'workflow_run',
    number: subject.number ?? null,
    head_sha: subject.head_sha || null,
    head_branch: subject.head_branch || null
  }).slice(0, 32)}`;
}

export function rootNode(subject, tick = 0) {
  boundedInteger('tick', tick, 0, Number.MAX_SAFE_INTEGER - 1);
  const rootSubject = clone(subject);
  const rootSubjectSha256 = sha256(rootSubject);
  const nodeId = nodeIdentity(rootSubjectSha256, []);
  const body = {
    schema: 'qikvrt_metatransistor_node_v1',
    node_id: nodeId,
    root_node_id: nodeId,
    root_subject: rootSubject,
    root_subject_sha256: rootSubjectSha256,
    parent_node_id: null,
    authority_node_id: nodeId,
    path: [],
    depth: 0,
    slot: null,
    role: 'AUTHORITY',
    monitor: true,
    terminal: true,
    tick,
    fanout: FANOUT,
    payload_sha256: null,
    manifestation_complete: true
  };
  return {...body, state_sha256: sha256(body)};
}

export function manifestChildren(parent, payload, tick = null, terminalSlots = TERMINAL_SLOTS) {
  if (parent?.schema !== 'qikvrt_metatransistor_node_v1') throw new Error('PARENT_SCHEMA_MISMATCH');
  const parentTick = boundedInteger('parent_tick', parent.tick, 0, Number.MAX_SAFE_INTEGER - 1);
  const nextTick = tick === null ? parentTick + 1 : boundedInteger('tick', tick, parentTick + 1, Number.MAX_SAFE_INTEGER);
  const slots = [...new Set(terminalSlots)].sort((a, b) => a - b);
  for (const slot of slots) boundedInteger('terminal_slot', slot, 0, FANOUT - 1);
  const payloadCopy = clone(payload);
  const payloadText = stableStringify(payloadCopy);
  const payloadSha256 = sha256(payloadText);
  const parentPath = [...(parent.path || [])];

  return Array.from({length: FANOUT}, (_, slot) => {
    const path = [...parentPath, slot];
    const childId = nodeIdentity(parent.root_subject_sha256, path);
    const body = {
      schema: 'qikvrt_metatransistor_node_v1',
      node_id: childId,
      root_node_id: parent.root_node_id,
      root_subject: parent.root_subject,
      root_subject_sha256: parent.root_subject_sha256,
      parent_node_id: parent.node_id,
      authority_node_id: parent.node_id,
      path,
      depth: path.length,
      slot,
      role: 'MIRROR_AUTHORITY',
      monitor: true,
      terminal: slots.includes(slot),
      tick: nextTick,
      fanout: FANOUT,
      payload: payloadCopy,
      payload_bytes: Buffer.byteLength(payloadText, 'utf8'),
      payload_sha256: payloadSha256,
      manifestation_complete: true,
      serialized_link: {
        schema: 'qikvrt_serialized_terminal_link_v1',
        format: 'CANONICAL_JSON_UTF8',
        source_node_id: parent.node_id,
        target_node_id: childId,
        tick: nextTick,
        payload_sha256: payloadSha256,
        lossless: true
      },
      child_authority_contract: {
        becomes_authority_for_children: true,
        child_count: FANOUT,
        authority_monitor: true,
        terminal_slots: slots
      }
    };
    return {...body, state_sha256: sha256(body)};
  });
}

export function derealize(parent, children) {
  if (!Array.isArray(children) || children.length !== FANOUT) throw new Error('EXACT_EIGHT_CHILDREN_REQUIRED');
  const sorted = [...children].sort((a, b) => a.slot - b.slot);
  const expectedSlots = Array.from({length: FANOUT}, (_, index) => index);
  if (stableStringify(sorted.map(child => child.slot)) !== stableStringify(expectedSlots)) {
    throw new Error('CHILD_SLOT_SET_INCOMPLETE');
  }
  let payload = null;
  let payloadSha256 = null;
  for (const child of sorted) {
    if (child.parent_node_id !== parent.node_id || child.authority_node_id !== parent.node_id) {
      throw new Error('CHILD_AUTHORITY_MISMATCH');
    }
    const unsigned = {...child};
    delete unsigned.state_sha256;
    if (sha256(unsigned) !== child.state_sha256) throw new Error('CHILD_STATE_DIGEST_MISMATCH');
    if (sha256(stableStringify(child.payload)) !== child.payload_sha256) throw new Error('CHILD_PAYLOAD_DIGEST_MISMATCH');
    if (payloadSha256 === null) {
      payload = child.payload;
      payloadSha256 = child.payload_sha256;
    } else if (child.payload_sha256 !== payloadSha256) {
      throw new Error('CHILD_PAYLOAD_DIVERGENCE');
    }
  }
  const body = {
    schema: 'qikvrt_metatransistor_derealization_receipt_v1',
    parent_node_id: parent.node_id,
    root_node_id: parent.root_node_id,
    source_tick: parent.tick,
    manifested_tick: sorted[0].tick,
    child_slots: expectedSlots,
    child_state_sha256: sorted.map(child => child.state_sha256),
    payload,
    payload_sha256: payloadSha256,
    lossless: true,
    state: 'DEREALIZED'
  };
  return {...body, receipt_sha256: sha256(body)};
}

export function materializeMesh(subject, payload, materializedDepth = 2, tick = 0) {
  boundedInteger('materialized_depth', materializedDepth, 0, MAX_MATERIALIZED_DEPTH);
  const root = rootNode(subject, tick);
  const nodes = [root];
  let frontier = [root];
  const levels = [{depth: 0, count: 1}];
  for (let depth = 1; depth <= materializedDepth; depth += 1) {
    const next = [];
    for (const parent of frontier) next.push(...manifestChildren(parent, payload));
    nodes.push(...next);
    frontier = next;
    levels.push({depth, count: frontier.length});
  }
  const body = {
    schema: 'qikvrt_metatransistor_mesh_projection_v1',
    framework: 'KubiKAva',
    method: 'TESTED_EVENT_MODEL_DRIVEN_DEVELOPMENT',
    subject: clone(subject),
    root_node_id: root.node_id,
    fanout: FANOUT,
    materialized_depth: materializedDepth,
    retirement_depth: RETIREMENT_DEPTH,
    materialized_node_count: nodes.length,
    logical_node_count_at_retirement_depth: logicalNodeCount(RETIREMENT_DEPTH).toString(),
    levels,
    nodes,
    payload_sha256: sha256(stableStringify(payload)),
    tick,
    transport: 'SERIALIZED_UNIVERSAL_TERMINAL',
    polling: false,
    security_profile: 'DATAFLOW_DEMONSTRATOR_SECURITY_DEFERRED',
    physical_hardware_execution: false
  };
  return {...body, projection_sha256: sha256(body)};
}


export function summarizeMesh(mesh, visibleDepth = 1) {
  if (!mesh || mesh.schema !== 'qikvrt_metatransistor_mesh_projection_v1') {
    throw new Error('MESH_SCHEMA_MISMATCH');
  }
  boundedInteger('visible_depth', visibleDepth, 0, mesh.materialized_depth);
  const nodes = mesh.nodes
    .filter(node => node.depth <= visibleDepth)
    .map(node => {
      const summary = {
        schema: node.schema,
        node_id: node.node_id,
        root_node_id: node.root_node_id,
        parent_node_id: node.parent_node_id,
        authority_node_id: node.authority_node_id,
        path: node.path,
        depth: node.depth,
        slot: node.slot,
        role: node.role,
        monitor: node.monitor,
        terminal: node.terminal,
        tick: node.tick,
        fanout: node.fanout,
        payload_sha256: node.payload_sha256,
        manifestation_complete: node.manifestation_complete,
        state_sha256: node.state_sha256
      };
      if (node.serialized_link) summary.serialized_link = node.serialized_link;
      if (node.child_authority_contract) summary.child_authority_contract = node.child_authority_contract;
      return summary;
    });
  const body = {
    schema: 'qikvrt_metatransistor_mesh_summary_v1',
    framework: mesh.framework,
    method: mesh.method,
    subject: mesh.subject,
    root_node_id: mesh.root_node_id,
    fanout: mesh.fanout,
    visible_depth: visibleDepth,
    materialized_depth: mesh.materialized_depth,
    retirement_depth: mesh.retirement_depth,
    materialized_node_count: mesh.materialized_node_count,
    logical_node_count_at_retirement_depth: mesh.logical_node_count_at_retirement_depth,
    levels: mesh.levels,
    nodes,
    payload_sha256: mesh.payload_sha256,
    tick: mesh.tick,
    transport: mesh.transport,
    polling: mesh.polling,
    security_profile: mesh.security_profile,
    physical_hardware_execution: mesh.physical_hardware_execution,
    full_projection_sha256: mesh.projection_sha256
  };
  return {...body, summary_sha256: sha256(body)};
}

function toBigInt(name, value) {
  if (typeof value === 'number' && !Number.isSafeInteger(value)) throw new Error(`${name}_NOT_SAFE_INTEGER`);
  try {
    return BigInt(value);
  } catch {
    throw new Error(`${name}_INTEGER_REQUIRED`);
  }
}

function towardZeroDivision(value, divisor) {
  const sign = value < 0n ? -1n : 1n;
  const magnitude = value < 0n ? -value : value;
  return [sign * (magnitude / divisor), sign * (magnitude % divisor)];
}

function fixedDecimal(raw, fractionalBits) {
  if (fractionalBits === 0) return raw.toString();
  const scale = 1n << BigInt(fractionalBits);
  const sign = raw < 0n ? '-' : '';
  const magnitude = raw < 0n ? -raw : raw;
  const integer = magnitude / scale;
  const remainder = magnitude % scale;
  if (remainder === 0n) return `${sign}${integer}`;
  const decimalNumerator = remainder * (5n ** BigInt(fractionalBits));
  const fraction = decimalNumerator.toString().padStart(fractionalBits, '0').replace(/0+$/, '');
  return `${sign}${integer}.${fraction}`;
}

export function fixedPointAlu(command) {
  const operation = String(command.operation || command.op || '').toUpperCase();
  if (!['ADD', 'SUB', 'MUL', 'MAC'].includes(operation)) throw new Error('ALU_OPERATION_INVALID');
  const bits = boundedInteger('bits', Number(command.bits ?? 32), 2, 64);
  const fractionalBits = boundedInteger('fractional_bits', Number(command.fractional_bits ?? 16), 0, bits - 1);
  const aRaw = toBigInt('A_RAW', command.a_raw ?? 0);
  const bRaw = toBigInt('B_RAW', command.b_raw ?? 0);
  const accumulatorRaw = toBigInt('ACCUMULATOR_RAW', command.accumulator_raw ?? 0);
  const scale = 1n << BigInt(fractionalBits);
  let unbounded;
  let discarded = 0n;
  if (operation === 'ADD') unbounded = aRaw + bRaw;
  else if (operation === 'SUB') unbounded = aRaw - bRaw;
  else {
    const [scaled, remainder] = towardZeroDivision(aRaw * bRaw, scale);
    discarded = remainder;
    unbounded = operation === 'MUL' ? scaled : accumulatorRaw + scaled;
  }
  const minimum = -(1n << BigInt(bits - 1));
  const maximum = (1n << BigInt(bits - 1)) - 1n;
  const overflow = unbounded < minimum || unbounded > maximum;
  const body = {
    schema: 'qikvrt_fixed_point_alu_receipt_v1',
    operation,
    bits,
    fractional_bits: fractionalBits,
    scale: scale.toString(),
    a_raw: aRaw.toString(),
    b_raw: bRaw.toString(),
    accumulator_raw: accumulatorRaw.toString(),
    rounding: 'TOWARD_ZERO',
    discarded_product_remainder_raw: discarded.toString(),
    minimum_raw: minimum.toString(),
    maximum_raw: maximum.toString(),
    unbounded_result_raw: unbounded.toString(),
    overflow,
    state: overflow ? 'HOLD' : 'CONTINUE',
    first_blocker: overflow ? 'FIXED_POINT_OVERFLOW' : null,
    result_raw: overflow ? null : unbounded.toString(),
    result_decimal: overflow ? null : fixedDecimal(unbounded, fractionalBits),
    transport_lossless: true,
    numeric_rounding_explicit: true,
    physical_hardware_execution: false
  };
  return {...body, receipt_sha256: sha256(body)};
}

export function normalizeGateState(value) {
  const state = String(value || 'NOT_OBSERVED').trim().toUpperCase();
  const aliases = new Map([
    ['QUEUED', 'REQUESTED'],
    ['PENDING', 'REQUESTED'],
    ['IN_PROGRESS', 'RUNNING'],
    ['FAILURE', 'HOLD'],
    ['FAILED', 'HOLD'],
    ['BLOCKED', 'HOLD'],
    ['ACTION_REQUIRED', 'HOLD'],
    ['TIMED_OUT', 'HOLD'],
    ['STARTUP_FAILURE', 'HOLD'],
    ['NEUTRAL', 'SKIPPED']
  ]);
  return aliases.get(state) || state;
}

export function gateStateFromWorkflow(action, conclusion) {
  if (action === 'requested') return 'REQUESTED';
  if (action === 'in_progress') return 'RUNNING';
  const normalized = normalizeGateState(conclusion);
  if (normalized === 'SUCCESS') return 'SUCCESS';
  if (normalized === 'SKIPPED') return 'SKIPPED';
  if (normalized === 'CANCELLED') return 'CANCELLED';
  if (normalized === 'HOLD') return 'HOLD';
  return 'UNKNOWN';
}

export function classifyGateSet(workflows, causalDepth = RETIREMENT_DEPTH, carrierExists = true) {
  boundedInteger('causal_depth', causalDepth, 0, 1_000_000);
  const byName = new Map((workflows || []).map(item => [item.name, item]));
  const gates = GATE_NAMES.map(name => ({
    name,
    state: normalizeGateState(byName.get(name)?.state),
    conclusion: byName.get(name)?.conclusion ?? null,
    run_id: byName.get(name)?.run_id ?? null,
    updated_at: byName.get(name)?.updated_at ?? null
  }));
  const observed = gates.filter(gate => gate.state !== 'NOT_OBSERVED');
  const active = gates.filter(gate => ['REQUESTED', 'RUNNING'].includes(gate.state));
  const holds = gates.filter(gate => gate.state === 'HOLD');
  const known = new Set(['NOT_OBSERVED', 'REQUESTED', 'RUNNING', 'SUCCESS', 'HOLD', 'SKIPPED', 'CANCELLED']);
  const unknown = gates.filter(gate => !known.has(gate.state));
  const allObserved = observed.length === FANOUT;
  const allHolds = allObserved && holds.length === FANOUT;
  const holdAdmissible = !carrierExists && allHolds && causalDepth >= RETIREMENT_DEPTH;

  let state;
  let action;
  if (unknown.length) [state, action] = ['REOBSERVE', 'REJECT_UNKNOWN_GATE_STATE'];
  else if (!allObserved) [state, action] = ['REOBSERVE', 'WAIT_FOR_EXACT_EIGHT_GATE_EVENT_SET'];
  else if (active.length) [state, action] = ['CONTINUE', 'FOLLOW_ACTIVE_REPOSITORY_EVENT'];
  else if (allHolds && causalDepth >= RETIREMENT_DEPTH && carrierExists) {
    [state, action] = ['RETIRE_CANDIDATE', 'PREPARE_EXACT_CARRIER_RETIREMENT'];
  } else if (allHolds && causalDepth >= RETIREMENT_DEPTH) {
    [state, action] = ['HOLD', 'NO_REPOSITORY_CARRIER_REMAINS'];
  } else if (holds.length) [state, action] = ['SUCCESSOR', 'ROUTE_FIRST_CAUSAL_GATE_BLOCKER'];
  else [state, action] = ['STABLE', 'AWAIT_NEXT_EVENT'];

  const fingerprintBody = {causal_depth: causalDepth, carrier_exists: carrierExists, gates};
  const body = {
    schema: 'qikvrt_depth9_gate_classification_v1',
    gate_count: FANOUT,
    causal_depth: causalDepth,
    retirement_depth: RETIREMENT_DEPTH,
    carrier_exists: carrierExists,
    all_observed: allObserved,
    all_holds: allHolds,
    hold_admissible: holdAdmissible,
    state,
    action,
    first_blocker: holds[0]?.name || null,
    gates,
    predecessor_evidence_transfer: false,
    gate_fingerprint: sha256(fingerprintBody)
  };
  return {...body, receipt_sha256: sha256(body)};
}

export function bootstrapProjection() {
  const subject = {
    repository: 'Goldkelch/qik-vrt',
    kind: 'demo',
    head_branch: 'metatransistor/fixed-point-alu',
    head_sha: '0000000000000000000000000000000000000000'
  };
  const alu = fixedPointAlu({
    operation: 'MAC',
    a_raw: 384,
    b_raw: 128,
    accumulator_raw: 64,
    bits: 16,
    fractional_bits: 8
  });
  const payload = {kind: 'FIXED_POINT_ALU', description: '1.5 × 0.5 + 0.25', alu};
  const mesh = materializeMesh(subject, payload, 1, 0);
  return {
    schema: 'qikvrt_monitor_projection_v3',
    authority: 'Goldkelch/qik-vrt',
    subject_id: subjectIdentity(subject),
    subject,
    state: 'CONTINUE',
    reason: 'AWAITING_FIRST_REPOSITORY_EVENT',
    projection: {role: 'MONITOR_AND_TERMINAL_DEMO', terminal: true, write: false, effect_commit: false},
    workflows: GATE_NAMES.map(name => ({name, state: 'NOT_OBSERVED', conclusion: null, run_id: null, updated_at: null})),
    classification: classifyGateSet([], RETIREMENT_DEPTH, true),
    mesh,
    terminal: {last_receipt: alu},
    transport: {polling: false, snapshot_only: true, live: '/api/gate-stream', terminal: '/api/terminal-event'},
    observed_at: new Date(0).toISOString()
  };
}

export function executeTerminalInput(subject, input) {
  if (!input || input.schema !== 'qikvrt_terminal_input_v1') throw new Error('TERMINAL_SCHEMA_MISMATCH');
  const materializedDepth = boundedInteger('materialized_depth', Number(input.materialized_depth ?? 2), 1, MAX_MATERIALIZED_DEPTH);
  const kind = String(input.command?.kind || '').toUpperCase();
  let payload;
  let receipt;
  if (kind === 'FIXED_POINT_ALU') {
    receipt = fixedPointAlu(input.command);
    payload = {kind, receipt};
  } else if (kind === 'DATA') {
    const value = String(input.command?.value ?? '');
    if (!value || Buffer.byteLength(value, 'utf8') > 4096) throw new Error('DATA_PAYLOAD_SIZE_INVALID');
    const body = {
      schema: 'qikvrt_terminal_data_receipt_v1',
      value,
      value_sha256: sha256(value),
      value_bytes: Buffer.byteLength(value, 'utf8'),
      state: 'CONTINUE',
      executable: false,
      transport_lossless: true
    };
    receipt = {...body, receipt_sha256: sha256(body)};
    payload = {kind, receipt};
  } else {
    throw new Error('TERMINAL_COMMAND_KIND_INVALID');
  }
  const tick = boundedInteger('tick', Number(input.tick ?? Date.now()), 0, Number.MAX_SAFE_INTEGER - 1);
  const mesh = materializeMesh(subject, payload, materializedDepth, tick);
  const root = mesh.nodes[0];
  const firstLevel = mesh.nodes.filter(node => node.depth === 1);
  const derealization = derealize(root, firstLevel);
  const transitionBody = {
    schema: 'qikvrt_terminal_transition_v1',
    event_type: 'terminal-transition',
    subject,
    subject_id: subjectIdentity(subject),
    command_kind: kind,
    tick,
    receipt,
    mesh,
    first_level_derealization: derealization,
    terminal_pattern: {
      OBSERVE: 'TERMINAL_INPUT',
      CLASSIFY: receipt.state,
      D0: subject.head_sha || subjectIdentity(subject),
      ACTION: 'SERIALIZE_AND_MANIFEST_EIGHT_CHILDREN',
      EFFECT: 'DATAFLOW_ONLY',
      READBACK: 'DEREALIZATION_VERIFIED',
      SUCCESSOR: 'EIGHT_CHILD_AUTHORITIES'
    },
    transport_ack: true,
    effect_ack: false,
    predecessor_evidence_transfer: false
  };
  return {...transitionBody, transition_sha256: sha256(transitionBody)};
}
