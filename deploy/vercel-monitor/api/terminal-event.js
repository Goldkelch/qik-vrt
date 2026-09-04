import {
  bootstrapProjection,
  executeTerminalInput,
  subjectIdentity,
  summarizeMesh,
} from './_mesh.js';
import {
  getRedis,
  STREAM_KEY,
  LATEST_PROJECTION_KEY,
  LATEST_MESH_KEY,
  LATEST_TERMINAL_KEY,
  NODE_MESHES_KEY,
  meshKey,
  terminalKey,
} from './_redis.js';

function fail(message, statusCode = 422) {
  const error = new Error(message);
  error.statusCode = statusCode;
  throw error;
}

function parseBody(req) {
  const contentLength = Number(req.headers['content-length'] || 0);
  if (contentLength > 8192) fail('TERMINAL_INPUT_TOO_LARGE', 413);
  const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  if (!body || body.schema !== 'qikvrt_terminal_input_v1') fail('TERMINAL_SCHEMA_MISMATCH');
  const depth = Number(body.materialized_depth ?? 2);
  if (!Number.isInteger(depth) || depth < 1 || depth > 2) {
    fail('TERMINAL_MATERIALIZED_DEPTH_MUST_BE_ONE_OR_TWO');
  }
  return { ...body, materialized_depth: depth };
}

async function resolveSubject(redis, requestedSubjectId) {
  const latestRaw = await redis.get(LATEST_PROJECTION_KEY);
  if (latestRaw) {
    const projection = JSON.parse(latestRaw);
    const subject = {
      repository: projection.node?.repository || 'Goldkelch/qik-vrt',
      ...projection.subject,
      head_sha: projection.head_sha,
    };
    const subjectId = projection.subject_id || subjectIdentity(subject);
    if (requestedSubjectId && requestedSubjectId !== subjectId) {
      fail('TERMINAL_EXACT_SUBJECT_DRIFT', 409);
    }
    return { nodeId: projection.node?.id || 'authority', subjectId, subject };
  }
  const bootstrap = bootstrapProjection();
  if (requestedSubjectId && requestedSubjectId !== bootstrap.subject_id) {
    fail('TERMINAL_SUBJECT_NOT_OBSERVED', 409);
  }
  return {
    nodeId: 'authority',
    subjectId: bootstrap.subject_id,
    subject: bootstrap.subject,
  };
}

function publicTransition(transition, mesh) {
  return {
    schema: transition.schema,
    event_type: transition.event_type,
    subject: transition.subject,
    subject_id: transition.subject_id,
    command_kind: transition.command_kind,
    tick: transition.tick,
    receipt: transition.receipt,
    mesh,
    first_level_derealization: transition.first_level_derealization,
    terminal_pattern: transition.terminal_pattern,
    transport_ack: transition.transport_ack,
    effect_ack: transition.effect_ack,
    predecessor_evidence_transfer: transition.predecessor_evidence_transfer,
    transition_sha256: transition.transition_sha256,
  };
}

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-QIKVRT-Role', 'BOUNDED_TERMINAL_DATAFLOW');
  res.setHeader('X-QIKVRT-Security-Profile', 'DEFERRED_NO_CODE_EXECUTION');
  if (req.method !== 'POST') {
    return res.status(405).json({
      schema: 'qikvrt_terminal_transport_receipt_v2',
      accepted: false,
      state: 'REOBSERVE',
      disposition: 'CONTINUE',
      reason: 'TERMINAL_POST_ONLY',
      transport_ack: false,
      effect_ack: false,
    });
  }

  try {
    const input = parseBody(req);
    const redis = await getRedis();
    const { nodeId, subjectId, subject } = await resolveSubject(redis, input.subject_id);
    const transition = executeTerminalInput(subject, input);
    if (transition.subject_id !== subjectId) fail('TERMINAL_SUBJECT_ID_MISMATCH', 409);
    const mesh = summarizeMesh(transition.mesh, 1);
    const terminal = publicTransition(transition, mesh);

    await redis.multi()
      .set(meshKey(nodeId, subjectId), JSON.stringify(transition.mesh))
      .set(terminalKey(nodeId, subjectId), JSON.stringify(terminal))
      .set(LATEST_MESH_KEY, JSON.stringify(mesh))
      .set(LATEST_TERMINAL_KEY, JSON.stringify(terminal))
      .hSet(NODE_MESHES_KEY, nodeId, JSON.stringify(mesh))
      .exec();

    const envelope = {
      schema: 'qikvrt_horizon_terminal_stream_event_v2',
      terminal,
      mesh,
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
      schema: 'qikvrt_terminal_transport_receipt_v2',
      accepted: true,
      node_id: nodeId,
      subject_id: subjectId,
      stream_id: streamId,
      transition_sha256: transition.transition_sha256,
      receipt: transition.receipt,
      mesh,
      first_level_derealization: transition.first_level_derealization,
      terminal_pattern: transition.terminal_pattern,
      transport_ack: true,
      effect_ack: false,
      repository_write: false,
      executable_input: false,
      physical_hardware_execution: false,
    });
  } catch (error) {
    return res.status(Number(error?.statusCode || 503)).json({
      schema: 'qikvrt_terminal_transport_receipt_v2',
      accepted: false,
      state: 'REOBSERVE',
      disposition: 'CONTINUE',
      reason: error?.message || 'TERMINAL_TRANSPORT_FAILURE',
      transport_ack: false,
      effect_ack: false,
      repository_write: false,
      executable_input: false,
    });
  }
}
