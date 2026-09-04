export default async function handler(req,res){
  res.setHeader('Cache-Control','no-store');
  return res.status(410).json({
    schema:'qikvrt_horizon_polling_retired_v1',
    state:'HOLD_UNVERIFIED',
    reason:'POLLING_DISABLED_USE_EVENT_STREAM',
    replacement:'/api/gate-stream'
  });
}
