import { render } from "@coldtea/pr-lens-renderer";
import { parseGraphDoc } from "@coldtea/pr-lens-schema";
import fs from "node:fs";
const ex = JSON.parse(fs.readFileSync("node_modules/@coldtea/pr-lens-schema/examples/postmark-refactor.graph.json","utf8"));
const doc = parseGraphDoc(ex);
const t0 = performance.now();
const r = render(doc, { lens: "architecture", theme: "dark" });
console.log("postmark", r.width, r.height, r.animated, (performance.now()-t0).toFixed(1)+"ms", r.svg.length, "bytes");
console.log("atlas keys", Object.keys(r.atlas), Object.keys(r.atlas.nodes).length, Object.keys(r.atlas.edges).length, JSON.stringify(Object.entries(r.atlas.nodes)[0]), JSON.stringify(Object.entries(r.atlas.lanes)[0]), JSON.stringify(Object.entries(r.atlas.edges)[0]));
const tags = {}; for (const m of r.svg.matchAll(/<([a-zA-Z]+)[\s>]/g)) tags[m[1]] = (tags[m[1]]||0)+1;
console.log("tags", JSON.stringify(tags));
console.log("attrs", [...new Set([...r.svg.matchAll(/\s([a-zA-Z:-]+)=/g)].map(m=>m[1]))].join(","));
console.log(r.svg.slice(0, 600));
fs.writeFileSync("postmark-dark.svg", r.svg);
// synthetic: 256 nodes in 4 lanes, 300 edges
const lanes = ["l0","l1","l2","l3"].map((id,i)=>({id, label:"lane "+i}));
const nodes = []; for (let i=0;i<256;i++) nodes.push({id:"s"+i,label:"module.function_name_"+i,kind:"function",delta:["added","modified","removed","unchanged"][i%4],lane:"l"+(i%4),files:[],badges:["+12 -3"]});
const edges = []; for (let i=0;i<300;i++){const a=i%256,b=(i*7+3)%256; if(a!==b) edges.push({id:"e"+i,from:"s"+a,to:"s"+b,kind:"call",delta:["added","removed","unchanged"][i%3]});}
const big = parseGraphDoc({schemaVersion:"0.2.0",kind:"graph",title:"synthetic",lenses:["architecture"],provenance:{repo:{owner:"o",name:"r"},base:{sha:"1111111"},head:{sha:"2222222"}},lanes,nodes,edges});
const t1 = performance.now();
const rb = render(big, { lens: "architecture", theme: "dark" });
console.log("big", rb.width, rb.height, (performance.now()-t1).toFixed(1)+"ms", rb.svg.length, "bytes", Object.keys(rb.atlas.nodes).length, "nodes in atlas");
fs.writeFileSync("big-dark.svg", rb.svg);
