export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({error:'MONITOR_ONLY'});
  }
  const prUrl = 'https://api.github.com/repos/Goldkelch/qik-vrt/pulls/966';
  const runUrl = 'https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs?event=pull_request&per_page=30';
  const headers = {
    'Accept':'application/vnd.github+json',
    'User-Agent':'qikvrt-vercel-monitor/1'
  };
  try {
    const [prResp, runsResp] = await Promise.all([fetch(prUrl,{headers}), fetch(runUrl,{headers})]);
    if (!prResp.ok || !runsResp.ok) {
      return res.status(502).json({
        schema:'qikvrt_monitor_projection_v1',
        role:'MONITOR_ONLY',
        state:'HOLD_UNVERIFIED',
        reason:'UPSTREAM_READBACK_UNAVAILABLE'
      });
    }
    const pr = await prResp.json();
    const runs = await runsResp.json();
    const exactHead = pr.head?.sha || null;
    const exactRuns = (runs.workflow_runs || []).filter(r => r.head_sha === exactHead).map(r => ({
      id:r.id,
      name:r.name,
      status:r.status,
      conclusion:r.conclusion,
      updated_at:r.updated_at
    }));
    res.setHeader('Cache-Control','no-store');
    res.setHeader('X-QIKVRT-Role','MONITOR_ONLY');
    return res.status(200).json({
      schema:'qikvrt_monitor_projection_v1',
      authority:'Goldkelch/qik-vrt',
      subject:{kind:'pull_request',number:966,head_sha:exactHead,base_sha:pr.base?.sha || null},
      projection:{role:'MONITOR_ONLY',terminal:false,write:false,effect_commit:false},
      workflows:exactRuns,
      rule:'On projection change, non-authority nodes must request and reobserve the exact change from Goldkelch; this projection is never itself EFFECT_ACK.',
      observed_at:new Date().toISOString()
    });
  } catch (error) {
    return res.status(502).json({
      schema:'qikvrt_monitor_projection_v1',
      role:'MONITOR_ONLY',
      state:'HOLD_UNVERIFIED',
      reason:'MONITOR_EXCEPTION'
    });
  }
}
