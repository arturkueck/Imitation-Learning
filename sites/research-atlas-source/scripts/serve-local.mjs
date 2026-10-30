import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../public/',import.meta.url));
const port=Number(process.env.PORT||4173);
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.md':'text/plain; charset=utf-8','.mp4':'video/mp4','.png':'image/png','.svg':'image/svg+xml'};
const server=http.createServer((req,res)=>{
 let url;try{url=decodeURIComponent(new URL(req.url,'http://localhost').pathname)}catch{res.writeHead(400).end();return}
 if(url.startsWith('/api/')){res.writeHead(503,{'Content-Type':'application/json'}).end(JSON.stringify({error:'Local read-only preview. Use npm run dev for the research import API.'}));return}
 if(url==='/')url='/index.html';if(['/findings','/library'].includes(url))url+='.html';
 const file=path.resolve(root,'.'+url),relative=path.relative(root,file);
 if(relative.startsWith('..')||path.isAbsolute(relative)){res.writeHead(403).end();return}
 fs.stat(file,(err,stat)=>{if(err||!stat.isFile()){res.writeHead(404).end('Not found');return}
 const headers={'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-cache','Accept-Ranges':'bytes'};
 let start=0,end=stat.size-1,status=200;
 if(req.headers.range){const m=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range);if(!m){res.writeHead(416,{'Content-Range':`bytes */${stat.size}`}).end();return}start=Number(m[1]);end=m[2]?Math.min(Number(m[2]),end):end;if(start>end||start>=stat.size){res.writeHead(416,{'Content-Range':`bytes */${stat.size}`}).end();return}status=206;headers['Content-Range']=`bytes ${start}-${end}/${stat.size}`}
 headers['Content-Length']=end-start+1;res.writeHead(status,headers);if(req.method==='HEAD'){res.end();return}const stream=fs.createReadStream(file,{start,end});stream.on('error',()=>res.destroy());stream.pipe(res);
 });
});
server.on('error',error=>{console.error(error.code==='EADDRINUSE'?`Port ${port} belegt. Anderen Port setzen: $env:PORT=4175; npm start`:error.message);process.exitCode=1});
server.listen(port,'127.0.0.1',()=>console.log(`Research Atlas: http://127.0.0.1:${port}\nLokale Trainingsergebnisse, Grafiken, Videos und Paperbibliothek.\nBeenden: Strg+C. Paper-Import/API: npm run dev (mit installierten Abhängigkeiten).`));
