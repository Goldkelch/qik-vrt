import { getRedis, STREAM_KEY } from './_redis.js';

const CURSOR = /^(?:\$|[0-9]+-[0-9]+)$/;

function eventName(payload) {
  try {
    const value = JSON.parse(payload);
    if (value?.schema === 'qikvrt_horizon_terminal_stream_event_v2') return 'terminal-transition';
    return 'projection';
  } catch {
    return 'projection';
  }
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();
  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.setHeader('X-QIKVRT-Polling', 'disabled');
  res.flushHeaders?.();

  let closed = false;
  req.on('close', () => { closed = true; });
  const base = await getRedis();
  const reader = base.duplicate();
  await reader.connect();
  const parsed = new URL(req.url || '/', 'http://localhost');
  const requested = String(req.headers['last-event-id'] || parsed.searchParams.get('cursor') || '$');
  let cursor = CURSOR.test(requested) ? requested : '$';
  const heartbeat = setInterval(() => {
    if (!closed) res.write(': transport-heartbeat-only\n\n');
  }, 15000);

  try {
    while (!closed) {
      const rows = await reader.xRead(
        [{ key: STREAM_KEY, id: cursor }],
        { BLOCK: 25000, COUNT: 100 },
      );
      if (!rows) continue;
      for (const stream of rows) {
        for (const message of stream.messages) {
          cursor = message.id;
          const payload = message.message.payload;
          res.write(`id: ${message.id}\n`);
          res.write(`event: ${eventName(payload)}\n`);
          res.write(`data: ${payload}\n\n`);
        }
      }
    }
  } catch (error) {
    if (!closed) {
      res.write('event: monitor-reobserve\n');
      res.write(`data: ${JSON.stringify({ state: 'REOBSERVE', disposition: 'CONTINUE', reason: error?.message || 'STREAM_FAILURE' })}\n\n`);
    }
  } finally {
    clearInterval(heartbeat);
    try { await reader.quit(); } catch {}
    if (!res.writableEnded) res.end();
  }
}
