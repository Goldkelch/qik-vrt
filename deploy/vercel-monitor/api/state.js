import { bootstrapProjection, summarizeMesh } from './_mesh.js';
import {
  getRedis,
  STREAM_KEY,
  LATEST_PROJECTION_KEY,
  LATEST_MESH_KEY,
  LATEST_TERMINAL_KEY,
  NODE_PROJECTIONS_KEY,
  NODE_MESHES_KEY,
} from './_redis.js';

const NODE_REGISTRY = Object.freeze({
  schema: 'qikvrt_horizon_node_registry_v2',
  framework: 'KubiKAva',
  development_model: 'TESTED_EVENT_MODEL_DRIVEN_DEVELOPMENT',
  repository_nodes: Object.freeze([
    Object.freeze({
      id: 'authority',
      repository: 'Goldkelch/qik-vrt',
      role: 'AUTHORITY',
      surface: 'MASTER_MONITOR_AND_FULL_TERMINAL',
      terminal_endpoint: 'http://127.0.0.1:8771',
      event_projection: 'IMPLEMENTED_ON_PR_992_REQUIRES_TRUSTED_MAIN_PROMOTION',
      external_effect: 'NONE',
    }),
    Object.freeze({
      id: 'mirror',
      repository: 'ingolf-lohmann/qik-vrt',
      role: 'MIRROR',
      surface: 'MONITOR_AND_FULL_TERMINAL',
      terminal_endpoint: 'http://127.0.0.1:8771',
      event_projection: 'PORTABLE_REQUIRES_MIRROR_MAIN_PROMOTION',
      external_effect: 'NONE',
    }),
  ]),
  recursive_node_template: Object.freeze({
    topology: 'EIGHT_ARY_RECURSIVE_TREE_WITH_8_BY_8_AUTHORITY_RING',
    fanout: 8,
    each_mirror_becomes_authority: true,
    each_authority_defines_eight_children: true,
    every_node_reflects_monitor_state: true,
    terminal_slots: Object.freeze([0, 7]),
    serialized_transport: 'CANONICAL_JSON_UTF8_SHA256',
    complete_manifestation: true,
    lossless_derealization: true,
    browser_visible_depth: 2,
    logical_retirement_depth: 9,
    logical_node_count_through_depth_9: 153391689,
    physical_hardware_execution: false,
  }),
});

function parseMap(values) {
  return Object.values(values || {})
    .map(value => JSON.parse(value))
    .sort((left, right) => String(left.node?.id || left.root_node_id || '')
      .localeCompare(String(right.node?.id || right.root_node_id || '')));
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'MONITOR_READ_ONLY' });
  try {
    const redis = await getRedis();
    const [latestRaw, meshRaw, terminalRaw, nodeMap, nodeMeshMap, tail] = await redis.multi()
      .get(LATEST_PROJECTION_KEY)
      .get(LATEST_MESH_KEY)
      .get(LATEST_TERMINAL_KEY)
      .hGetAll(NODE_PROJECTIONS_KEY)
      .hGetAll(NODE_MESHES_KEY)
      .xRevRange(STREAM_KEY, '+', '-', { COUNT: 1 })
      .exec();
    const latest = latestRaw ? JSON.parse(latestRaw) : null;
    const latestMesh = meshRaw ? JSON.parse(meshRaw) : null;
    const latestTerminal = terminalRaw ? JSON.parse(terminalRaw) : null;
    const bootstrap = bootstrapProjection();
    const bootstrapMesh = summarizeMesh(bootstrap.mesh, 1);
    const cursor = tail?.[0]?.id || '0-0';

    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-QIKVRT-Role', 'MASTER_MONITOR_AND_BOUNDED_TERMINAL');
    res.setHeader('X-QIKVRT-Polling', 'disabled');
    return res.status(200).json({
      schema: 'qikvrt_horizon_snapshot_v4',
      authority: 'Goldkelch/qik-vrt',
      framework: 'KubiKAva',
      development_model: 'TESTED_EVENT_MODEL_DRIVEN_DEVELOPMENT',
      state: latest ? 'OBSERVED' : 'REOBSERVE',
      reason: latest ? null : 'NO_REPOSITORY_EVENT_SNAPSHOT_YET',
      latest_projection: latest,
      latest_mesh: latestMesh,
      latest_terminal: latestTerminal,
      node_projections: parseMap(nodeMap),
      node_meshes: parseMap(nodeMeshMap),
      node_registry: NODE_REGISTRY,
      bootstrap_projection: latest ? null : {
        ...bootstrap,
        mesh: bootstrapMesh,
        demo_only: true,
      },
      stream_cursor: cursor,
      transport: {
        polling: false,
        snapshot_reads: 1,
        live: '/api/gate-stream',
        terminal: '/api/terminal-event',
        resume: 'Last-Event-ID',
        heartbeat_is_state_observation: false,
      },
      observed_at: new Date().toISOString(),
      claims: {
        pass: false,
        final_pass: false,
        effect_ack_done: false,
        deployment: false,
        publication: false,
        physical_hardware_execution: false,
      },
    });
  } catch (error) {
    return res.status(503).json({
      schema: 'qikvrt_horizon_snapshot_v4',
      state: 'REOBSERVE',
      reason: error?.message || 'SNAPSHOT_FAILURE',
      stream_cursor: '0-0',
      transport: {
        polling: false,
        live: '/api/gate-stream',
        terminal: '/api/terminal-event',
      },
    });
  }
}
