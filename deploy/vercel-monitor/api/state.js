import { getRedis, LATEST_HEAD_KEY, gatesKey, subjectKey } from './_redis.js';

export default async function handler(req,res){
  if(req.method!=='GET') return res.status(405).json({error:'MONITOR_ONLY'});
  try{
    const redis=await getRedis();
    const head=await redis.get(LATEST_HEAD_KEY);
    if(!head) return res.status(503).json({schema:'qikvrt_monitor_projection_v2',state:'HOLD_UNVERIFIED',reason:'NO_EVENT_SNAPSHOT'});
    const [rawGates,rawSubject]=await Promise.all([redis.hGetAll(gatesKey(head)),redis.get(subjectKey(head))]);
    const workflows=Object.values(rawGates).map(v=>JSON.parse(v)).sort((a,b)=>a.name.localeCompare(b.name));
    const subject=rawSubject?JSON.parse(rawSubject):{kind:'workflow_run',head_sha:head};
    res.setHeader('Cache-Control','no-store');
    res.setHeader('X-QIKVRT-Role','MONITOR_ONLY');
    return res.status(200).json({
      schema:'qikvrt_monitor_projection_v2',authority:'Goldkelch/qik-vrt',subject:{...subject,head_sha:head},
      projection:{role:'MONITOR_ONLY',terminal:false,write:false,effect_commit:false},workflows,
      transport:{polling:false,snapshot_only:true,live:'/api/gate-stream'},observed_at:new Date().toISOString()
    });
  }catch(error){
    return res.status(503).json({schema:'qikvrt_monitor_projection_v2',state:'HOLD_UNVERIFIED',reason:error?.message||'SNAPSHOT_FAILURE'});
  }
}
