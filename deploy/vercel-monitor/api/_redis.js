import { createClient } from 'redis';

let clientPromise;

export function getRedis() {
  if (!process.env.REDIS_URL) throw new Error('REDIS_URL_REQUIRED');
  if (!clientPromise) {
    const client = createClient({url: process.env.REDIS_URL});
    client.on('error', error => console.error('horizon redis', error?.message || error));
    clientPromise = client.connect().then(() => client);
  }
  return clientPromise;
}

export const STREAM_KEY = 'qikvrt:horizon:gate-events:v1';
export const LATEST_HEAD_KEY = 'qikvrt:horizon:latest-head:v1';
export const gatesKey = head => `qikvrt:horizon:gates:v1:${head}`;
export const subjectKey = head => `qikvrt:horizon:subject:v1:${head}`;
export const dedupeKey = eventId => `qikvrt:horizon:dedupe:v1:${eventId}`;
