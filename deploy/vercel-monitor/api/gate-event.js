import { createHash } from 'node:crypto';
import { createRemoteJWKSet, jwtVerify } from 'jose';
import {
  getRedis,
  STREAM_KEY,
  LATEST_PROJECTION_KEY,
  NODE_PROJECTIONS_KEY,
  gatesKey,
  projectionKey,
  dedupeKey,
} from './_redis.js';

const GATES = Object.freeze([
  'QIKVRT CI',
  'QIKVRT repository evidence materialization',
  'QIKVRT Collective Proposal Review',
  'QIKVRT code-owner review observer',
  'QIKVRT live status watch',
  'QIKVRT Spark branch work-unit core',
  'QIKVRT zero-bug continuous invariant',
  'QIKVRT explicit HOLD contract',
]);
const GATE_SET = new Set(GATES);
const ALLOWED_REPOSITORIES = new Map([
  ['Goldkelch/qik-vrt', { id: 'authority', role: 'AUTHORITY', capability: 'MASTER_MONITOR_AND_FULL_TERMINAL' }],
  ['ingolf-lohmann/qik-vrt', { id: 'mirror', role: 'MIRROR', capability: 'MONITOR_AND_FULL_TERMINAL' }],
]);
const STATES = new Set(['NOT_OBSERVED', 'CONTINUE', 'READY', 'HOLD', 'SKIPPED']);
const SHA40 = /^[0-9a-f]{40}$/;
const SHA256 = /^[0-9a-f]{64}$/;
const MAX_DEPTH = 9;
const JWKS = createRemoteJWKSet(new URL('https://token.actions.githubusercontent.com/.well-known/jwks'));
const AUDIENCE = 'https://horizon-by-qik-vrt.vercel.app';

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}

function fingerprint(value) {
  return createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
}

function fail(message, statusCode = 422) {
  const error = new Error(message);
  error.statusCode = statusCode;
  throw error;
}

async function authenticate(req) {
  const header = req.headers.authorization || '';
  if (!header.startsWith('Bearer ')) fail('OIDC_REQUIRED', 401);
  const token = header.slice(7);
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: 'https://token.actions.githubusercontent.com',
    audience: AUDIENCE,
  });
  const repository = String(payload.repository || '');
  if (!ALLOWED_REPOSITORIES.has(repository)) fail('REPOSITORY_NOT_REGISTERED', 403);
  if (payload.event_name !== 'workflow_run') fail('EVENT_MISMATCH', 403);
  return { payload, repository, registered: ALLOWED_REPOSITORIES.get(repository) };
}

function parseBody(req) {
  if (typeof req.body === 'string') return JSON.parse(req.body);
  return req.body;
}

function subjectId(subject) {
  if (subject?.kind === 'pull_request' && Number.isInteger(subject.number)) {
    return `pr-${subject.number}`;
  }
  const branch = String(subject?.head_branch || 'unbound');
  return `ref-${branch}`;
}

function normalizeGate(body) {
  return {
    name: body.gate,
    state: body.state,
    status: body.status ?? null,
    conclusion: body.conclusion ?? null,
    run_id: body.run_id,
    updated_at: body.updated_at ?? null,
    event_id: body.event_id,
    cause_authority: body.cause_authority || 'GITHUB_WORKFLOW_SURFACE',
    causal_fingerprint: body.causal_fingerprint || '',
  };
}

function vectorFrom(rawGates) {
  return GATES.map(name => {
    const parsed = rawGates[name] ? JSON.parse(rawGates[name]) : {};
    return {
      name,
      state: parsed.state || 'NOT_OBSERVED',
      status: parsed.status ?? null,
      conclusion: parsed.conclusion ?? null,
      run_id: parsed.run_id ?? null,
      updated_at: parsed.updated_at ?? null,
      event_id: parsed.event_id ?? null,
      cause_authority: parsed.cause_authority || '',
      causal_fingerprint: parsed.causal_fingerprint || '',
    };
  });
}

function carrierFrom(body) {
  const supplied = body.carrier && typeof body.carrier === 'object' ? body.carrier : {};
  return {
    pull_request_open: Boolean(supplied.pull_request_open ?? (body.subject?.kind === 'pull_request')),
    issue_open: Boolean(supplied.issue_open),
    branch_exists: Boolean(supplied.branch_exists ?? body.subject?.head_branch),
    exact_head_current: Boolean(supplied.exact_head_current),
    protected: Boolean(supplied.protected ?? true),
    default_branch: Boolean(supplied.default_branch ?? true),
  };
}

function project({ body, vector, previous }) {
  const complete = vector.every(gate => gate.state !== 'NOT_OBSERVED');
  const allHold = complete && vector.every(gate => gate.state === 'HOLD');
  const vectorFingerprint = fingerprint({ head_sha: body.head_sha, gates: vector });
  const activeWriter = Boolean(body.active_writer);
  const successorObserved = Boolean(body.successor_observed);
  const holdCount = vector.filter(gate => gate.state === 'HOLD').length;
  const computationDepth = activeWriter || successorObserved || holdCount === 0
    ? 0
    : Math.min(MAX_DEPTH, holdCount + 1);
  const authoritativeVector = complete && vector.every(gate =>
    gate.cause_authority === 'REPOSITORY_RECEIPT' && SHA256.test(gate.causal_fingerprint)
  );
  const carrier = carrierFrom(body);
  const carrierPresent = carrier.pull_request_open || carrier.issue_open || carrier.branch_exists;
  const cutCandidate = complete && allHold && computationDepth >= MAX_DEPTH;
  const cutEligible = cutCandidate && authoritativeVector && carrierPresent &&
    carrier.exact_head_current && !carrier.protected && !carrier.default_branch;
  let disposition = 'REOBSERVE_INCOMPLETE_VECTOR';
  if (complete) disposition = 'CONTINUE';
  if (allHold) disposition = 'CONTINUE_DEPTH_OBSERVATION';
  if (cutCandidate) disposition = 'CUT_CANDIDATE_REQUIRES_EXACT_RECEIPT';
  if (cutEligible) disposition = 'CUT_ELIGIBLE';

  return {
    schema: 'qikvrt_metatransistor_projection_v1',
    framework: 'KubiKAva',
    development_model: 'TESTED_EVENT_MODEL_DRIVEN_DEVELOPMENT',
    node: body.node,
    subject: body.subject,
    head_sha: body.head_sha,
    gate_count: GATES.length,
    gates: vector,
    complete,
    all_hold: allHold,
    computation_depth: computationDepth,
    max_compute_depth: MAX_DEPTH,
    vector_fingerprint: vectorFingerprint,
    authoritative_vector: authoritativeVector,
    active_writer: activeWriter,
    successor_observed: successorObserved,
    carrier,
    cut_candidate: cutCandidate,
    cut_eligible: cutEligible,
    disposition,
    prune_plan: {
      executable: cutEligible,
      automatic: false,
      reason: 'ALL_GATES_HOLD_AT_COMPUTE_DEPTH_9',
      ordered_actions: [
        'READBACK_EXACT_SUBJECT_AND_CARRIER',
        'PERSIST_CUT_RECEIPT',
        'CLOSE_PULL_REQUEST_NOT_PLANNED_IF_OPEN',
        'CLOSE_EXCLUSIVE_ISSUE_CARRIER_IF_OPEN',
        'DELETE_UNPROTECTED_NONDEFAULT_BRANCH_IF_HEAD_UNCHANGED',
        'READBACK_ALL_CARRIER_ABSENCE',
      ],
    },
    terminal: body.terminal,
    observed_at: new Date().toISOString(),
    claims: {
      pass: false,
      final_pass: false,
      effect_ack_done: false,
      deployment: false,
      publication: false,
      empirical_confirmation: false,
    },
  };
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'EVENT_INGRESS_POST_ONLY' });
  try {
    const auth = await authenticate(req);
    const body = parseBody(req);
    if (!body || body.schema !== 'qikvrt_horizon_gate_event_v2') fail('SCHEMA_MISMATCH');
    if (!GATE_SET.has(body.gate)) fail('UNKNOWN_GATE');
    if (!SHA40.test(body.head_sha || '')) fail('EXACT_HEAD_REQUIRED');
    if (!Number.isInteger(body.run_id) || body.run_id < 1) fail('RUN_ID_REQUIRED');
    if (!body.event_id || !STATES.has(body.state)) fail('INCOMPLETE_EVENT');
    if (!body.node || body.node.repository !== auth.repository) fail('NODE_REPOSITORY_MISMATCH');
    if (body.node.id !== auth.registered.id || body.node.role !== auth.registered.role) {
      fail('NODE_ROLE_MISMATCH');
    }
    if (body.node.capability !== auth.registered.capability) fail('NODE_CAPABILITY_MISMATCH');
    if (body.subject?.head_sha !== body.head_sha) fail('SUBJECT_HEAD_MISMATCH');

    const redis = await getRedis();
    const first = await redis.set(dedupeKey(body.event_id), '1', { NX: true, EX: 604800 });
    if (!first) {
      return res.status(200).json({
        schema: 'qikvrt_horizon_ingress_receipt_v2',
        accepted: true,
        deduplicated: true,
        event_id: body.event_id,
        transport_ack: true,
        effect_ack: false,
      });
    }

    const sid = subjectId(body.subject);
    const pkey = projectionKey(body.node.id, sid);
    const previousRaw = await redis.get(pkey);
    const previous = previousRaw ? JSON.parse(previousRaw) : null;
    const gkey = gatesKey(body.node.id, sid, body.head_sha);
    await redis.hSet(gkey, body.gate, JSON.stringify(normalizeGate(body)));
    const rawGates = await redis.hGetAll(gkey);
    const projection = project({ body, vector: vectorFrom(rawGates), previous });
    const serialized = JSON.stringify(projection);

    await redis.multi()
      .set(pkey, serialized)
      .set(LATEST_PROJECTION_KEY, serialized)
      .hSet(NODE_PROJECTIONS_KEY, body.node.id, serialized)
      .exec();

    const envelope = {
      schema: 'qikvrt_horizon_stream_event_v2',
      event: body,
      projection,
      transport_ack: true,
      effect_ack: false,
    };
    const streamId = await redis.xAdd(
      STREAM_KEY,
      '*',
      { payload: JSON.stringify(envelope) },
      { TRIM: { strategy: 'MAXLEN', strategyModifier: '~', threshold: 4096 } },
    );
    return res.status(202).json({
      schema: 'qikvrt_horizon_ingress_receipt_v2',
      accepted: true,
      deduplicated: false,
      event_id: body.event_id,
      stream_id: streamId,
      disposition: projection.disposition,
      computation_depth: projection.computation_depth,
      cut_candidate: projection.cut_candidate,
      cut_eligible: projection.cut_eligible,
      transport_ack: true,
      effect_ack: false,
    });
  } catch (error) {
    const status = Number(error?.statusCode || 503);
    return res.status(status).json({
      schema: 'qikvrt_horizon_ingress_receipt_v2',
      accepted: false,
      state: 'REOBSERVE',
      disposition: 'CONTINUE',
      reason: error?.message || 'INGRESS_REJECTED',
      transport_ack: false,
      effect_ack: false,
    });
  }
}
