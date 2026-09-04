export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-QIKVRT-Polling', 'disabled');
  return res.status(410).json({
    schema: 'qikvrt_horizon_polling_retired_v3',
    state: 'REOBSERVE',
    disposition: 'CONTINUE',
    reason: 'POLLING_DISABLED_USE_EVENT_STREAM',
    snapshot: '/api/state',
    replacement: '/api/gate-stream',
    terminal: '/api/terminal-event',
  });
}
