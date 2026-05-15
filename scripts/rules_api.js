const path = require('path');
const fs = require('fs');
const ROOT = path.resolve(__dirname, '..');
module.exports = (req,res,next)=>{
  const p = path.join(ROOT,'rules',...req.path.split('/').slice(2));
  if(!fs.existsSync(p)) return res.status(404).json({ok:false,error:'not found',path:p});
  res.json(JSON.parse(fs.readFileSync(p,'utf8')));
};