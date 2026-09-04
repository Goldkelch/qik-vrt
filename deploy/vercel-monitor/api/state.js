import {
  getRedis,
  STREAM_KEY,
  LATEST_PROJECTION_KEY,
  NODE_PROJECTIONS_KEY,
} from './_redis.js';

const NODE_REGISTRY = Object.freeze([
  Object.freeze({
    id: 'authority',
    repository: 'Goldkelch/qik-vrt',
    role: 'AUTHORITY',
    surface: 'MASTER_MONITOR_AND_FULL_TERMINAL',
    terminal_endpoint: 'http://127.0.0.1:8771',
    external_effect: 'NONE',
  }),
  Object.freeze({
    id: 'mirror',
    repository: 'ingolf-lohmann/qik-vrt',
    role: 'MIRROR',
    surface: 'MONITOR_AND_FULL_TERMINAL',
    terminal_endpoint: 'http://127.0.0.1:8771',
    external_effect: 'NONE',
  }),
]);

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'MONITOR_ONLY' });
  try {
    const redis = await getRedis();
    const [latestRaw, nodeMap, tail] = await redis.multi()
      .get(LATEST_PROJECTION_KEY)
      .hGetAll(NODE_PROJECTIONS_KEY)
      .xRevRange(STREAM_KEY, '+', '-', { COUNT: 1 })
      .exec();
    const projections = Object.values(nodeMap)
      .map(value => JSON.parse(value))
      .sort((left, right) => String(left.node?.id).localeCompare(String(right.node?.id)));
    const latest = latestRaw ? JSON.parse(latestRaw) : null;
    const cursor = tail?.[0]?.id || '0-0';
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-QIKVRT-Role', 'MASTER_MONITOR');
    res.setHeader('X-QIKVRT-Polling', 'disabled');
    return res.status(200).json({
      schema: 'qikvrt_horizon_snapshot_v3',
      authority: 'Goldkelch/qik-vrt',
      framework: 'KubiKAva',
      development_model: 'TESTED_EVENT_MODEL_DRIVEN_DEVELOPMENT',
      state: latest ? 'OBSERVED' : 'REOBSERVE',
      reason: latest ? null : 'NO_EVENT_SNAPSHOT_YET',
      latest_projection: latest,
      node_projections: projections,
      node_registry: NODE_REGISTRY,
      stream_cursor: cursor,
      transport: {
        polling: false,
        snapshot_reads: 1,
        live: '/api/gate-stream',
        resume: 'Last-Event-ID',
      },
      observed_at: new Date().toISOString(),
      claims: {
        pass: false,
        final_pass: false,
        effect_ack_done: false,
        deployment: false,
        publication: false,
      },
    });
  } catch (error) {
    return res.status(503).json({
      schema: 'qikvrt_horizon_snapshot_v3',
      state: 'REOBSERVE',
      reason: error?.message || 'SNAPSHOT_FAILURE',
      stream_cursor: '0-0',
      transport: { polling: false, live: '/api/gate-stream' },
    });
  }
}
