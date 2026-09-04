import { createRemoteJWKSet, jwtVerify } from 'jose';
import { getRedis, STREAM_KEY, LATEST_HEAD_KEY, gatesKey, subjectKey, dedupeKey } from './_redis.js';

const GATES = new Set([
  'QIKVRT CI',
  'QIKVRT repository evidence materialization',
  'QIKVRT Collective Proposal Review',
  'QIKVRT code-owner review observer',
  'QIKVRT live status watch',
  'QIKVRT Spark branch work-unit core',
  'QIKVRT zero-bug continuous invariant',
  'QIKVRT explicit HOLD contract'
]);
const JWKS = createRemoteJWKSet(new URL('https://token.actions.githubusercontent.com/.well-known/jwks'));
const AUD = 'https://horizon-by-qik-vrt.vercel.app';

async function authenticate(req) {
  const header = req.headers.authorization || '';
  if (!header.startsWith('Bearer ')) throw new Error('OIDC_REQUIRED');
  const token = header.slice(7);
  const { payload } = await jwtVerify(token, JWKS, { issuer:'https://token.actions.githubusercontent.com', audience:AUD });
  if (payload.repository !== 'Goldkelch/qik-vrt') throw new Error('REPOSITORY_MISMATCH');
  if (payload.event_name !== 'workflow_run') throw new Error('EVENT_MISMATCH');
  return payload;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({error:'EVENT_INGRESS_POST_ONLY'});
  try {
    await authenticate(req);
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    if (!body || body.schema !== 'qikvrt_horizon_gate_event_v1') throw new Error('SCHEMA_MISMATCH');
    if (!GATES.has(body.gate)) throw new Error('UNKNOWN_GATE');
    if (!/^[0-9a-f]{40}$/.test(body.head_sha || '')) throw new Error('EXACT_HEAD_REQUIRED');
    if (!body.event_id || !body.run_id || !body.state) throw new Error('INCOMPLETE_EVENT');

    const redis = await getRedis();
    const first = await redis.set(dedupeKey(body.event_id), '1', {NX:true, EX:604800});
    if (!first) return res.status(200).json({schema:'qikvrt_horizon_ingress_receipt_v1',accepted:true,deduplicated:true,event_id:body.event_id});

    const gate = {
      name:body.gate,state:body.state,status:body.status ?? null,conclusion:body.conclusion ?? null,
      run_id:body.run_id,updated_at:body.updated_at,event_id:body.event_id
    };
    const subject = body.subject || {kind:'workflow_run',head_sha:body.head_sha};
    await redis.multi()
      .hSet(gatesKey(body.head_sha), body.gate, JSON.stringify(gate))
      .set(subjectKey(body.head_sha), JSON.stringify(subject))
      .set(LATEST_HEAD_KEY, body.head_sha)
      .exec();
    const streamId = await redis.xAdd(STREAM_KEY, '*', {payload:JSON.stringify({...body, gate_projection:gate})}, {TRIM:{strategy:'MAXLEN',strategyModifier:'~',threshold:4096}});
    return res.status(202).json({schema:'qikvrt_horizon_ingress_receipt_v1',accepted:true,deduplicated:false,event_id:body.event_id,stream_id:streamId,transport_ack:true,effect_ack:false});
  } catch (error) {
    return res.status(401).json({schema:'qikvrt_horizon_ingress_receipt_v1',accepted:false,state:'HOLD_UNVERIFIED',reason:error?.message || 'INGRESS_REJECTED'});
  }
}
