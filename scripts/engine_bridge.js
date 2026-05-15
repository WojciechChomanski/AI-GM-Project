const sessions = new Map();
module.exports = (req,res,next)=>{
  const sid = req.query.session || 'default';
  if(req.method==='POST' && req.path==='/start'){
    sessions.set(sid,{started:true,log:[]});
    return res.json({started:true});
  }
  if(req.path==='/log'){
    return res.send(sessions.get(sid)?.log?.join('\n') || '');
  }
  res.status(404).json({ok:false});
};