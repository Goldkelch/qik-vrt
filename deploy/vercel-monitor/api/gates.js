const GATE_NAMES = [
  'QIKVRT CI',
  'QIKVRT repository evidence materialization',
  'QIKVRT Collective Proposal Review',
  'QIKVRT code-owner review observer',
  'QIKVRT live status watch',
  'QIKVRT Spark branch work-unit core',
  'QIKVRT zero-bug continuous invariant',
  'QIKVRT explicit HOLD contract'
];

function gateState(run) {
  if (!run) return 'NOT_OBSERVED';
  if (['queued','in_progress','requested','waiting','pending'].includes(run.status)) return 'RUNNING';
  if (run.conclusion === 'success') return 'SUCCESS';
  if (run.conclusion === 'skipped' || run.conclusion === 'neutral') return 'SKIPPED';
  if (run.conclusion === 'cancelled') return 'CANCELLED';
  if (['failure','action_required','timed_out','startup_failure'].includes(run.conclusion)) return 'BLOCKED';
  return 'UNKNOWN';
}

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({error:'MONITOR_ONLY'});
  }

  const head = typeof req.query?.head === 'string' && /^[0-9a-f]{40}$/.test(req.query.head)
    ? req.query.head
    : null;
  if (!head) {
    return res.status(400).json({
      schema:'qikvrt_gate_projection_v1',
      role:'MONITOR_ONLY',
      state:'HOLD_UNVERIFIED',
      reason:'EXACT_HEAD_REQUIRED'
    });
  }

  const token = process.env.GITHUB_READ_TOKEN || process.env.GITHUB_TOKEN || '';
  const headers = {
    'Accept':'application/vnd.github+json',
    'User-Agent':'qikvrt-vercel-monitor/2'
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const runsResp = await fetch(
      'https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs?event=pull_request&per_page=100',
      {headers, cache:'no-store'}
    );
    if (!runsResp.ok) {
      res.setHeader('Cache-Control','no-store');
      return res.status(502).json({
        schema:'qikvrt_gate_projection_v1',
        role:'MONITOR_ONLY',
        state:'HOLD_UNVERIFIED',
        reason:'UPSTREAM_GATE_READBACK_UNAVAILABLE',
        upstream_status:runsResp.status
      });
    }

    const runs = await runsResp.json();
    const exactRuns = (runs.workflow_runs || []).filter(run => run.head_sha === head);
    const latestByName = new Map();
    for (const run of exactRuns) {
      if (!GATE_NAMES.includes(run.name)) continue;
      const previous = latestByName.get(run.name);
      const observed = Date.parse(run.updated_at || run.created_at || '') || 0;
      const prior = previous ? (Date.parse(previous.updated_at || previous.created_at || '') || 0) : -1;
      if (!previous || observed > prior) latestByName.set(run.name, run);
    }

    const gates = GATE_NAMES.map((name, index) => {
      const run = latestByName.get(name) || null;
      return {
        ordinal:index + 1,
        name,
        state:gateState(run),
        run_id:run?.id || null,
        status:run?.status || null,
        conclusion:run?.conclusion || null,
        updated_at:run?.updated_at || null
      };
    });

    res.setHeader('Cache-Control','public, max-age=0, s-maxage=1, stale-while-revalidate=1');
    res.setHeader('X-QIKVRT-Role','MONITOR_ONLY');
    res.setHeader('X-QIKVRT-Gate-Refresh','1s');
    return res.status(200).json({
      schema:'qikvrt_gate_projection_v1',
      authority:'Goldkelch/qik-vrt',
      exact_head:head,
      projection:{role:'MONITOR_ONLY',terminal:false,write:false,effect_commit:false},
      gate_count:gates.length,
      gates,
      observed_at:new Date().toISOString()
    });
  } catch (error) {
    res.setHeader('Cache-Control','no-store');
    return res.status(502).json({
      schema:'qikvrt_gate_projection_v1',
      role:'MONITOR_ONLY',
      state:'HOLD_UNVERIFIED',
      reason:'GATE_MONITOR_EXCEPTION'
    });
  }
}
