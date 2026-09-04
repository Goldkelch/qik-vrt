import { createClient } from 'redis';

let clientPromise;

export function getRedis() {
  if (!process.env.REDIS_URL) throw new Error('REDIS_URL_REQUIRED');
  if (!clientPromise) {
    const client = createClient({ url: process.env.REDIS_URL });
    client.on('error', error => console.error('horizon redis', error?.message || error));
    clientPromise = client.connect().then(() => client);
  }
  return clientPromise;
}

function segment(value) {
  return encodeURIComponent(String(value || 'unbound')).replace(/%/g, '_').slice(0, 180);
}

export const STREAM_KEY = 'qikvrt:horizon:metatransistor-events:v3';
export const LATEST_PROJECTION_KEY = 'qikvrt:horizon:latest-projection:v3';
export const NODE_PROJECTIONS_KEY = 'qikvrt:horizon:node-projections:v3';
export const gatesKey = (nodeId, subjectId, head) =>
  `qikvrt:horizon:gates:v3:${segment(nodeId)}:${segment(subjectId)}:${segment(head)}`;
export const projectionKey = (nodeId, subjectId) =>
  `qikvrt:horizon:projection:v3:${segment(nodeId)}:${segment(subjectId)}`;
export const dedupeKey = eventId => `qikvrt:horizon:dedupe:v3:${segment(eventId)}`;
