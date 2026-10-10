import { parseGraphDoc } from "@coldtea/pr-lens-schema";
import fs from "node:fs";
const lanes = ["l0","l1","l2","l3"].map((id,i)=>({id, label:"lane "+i}));
const nodes = []; for (let i=0;i<256;i++) nodes.push({id:"s"+i,label:"module.function_name_"+i,kind:"function",delta:["added","modified","removed","unchanged"][i%4],lane:"l"+(i%4)});
const edges = []; for (let i=0;i<300;i++){const a=i%256,b=(i*7+3)%256; if(a!==b) edges.push({id:"e"+i,from:"s"+a,to:"s"+b,kind:"call",delta:["added","removed","unchanged"][i%3]});}
const big = parseGraphDoc({schemaVersion:"0.2.0",kind:"graph",title:"synthetic <b>&amp;",lenses:["architecture"],provenance:{repo:{owner:"o",name:"r"},base:{sha:"1111111"},head:{sha:"2222222"}},lanes,nodes,edges});
fs.writeFileSync("big.parsed.json", JSON.stringify(big));
console.log(Object.keys(big), JSON.stringify(big.edges[0]), JSON.stringify(big.nodes[0]));
