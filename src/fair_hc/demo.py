"""An offline worked example, generated exclusively from actual operation traces."""

from pathlib import Path
import json
from .algorithm import make_fair
from .data import synthetic
from .geometry import average_linkage, similarities
from .metrics import evaluate
from .tree import Tree, preorder, postorder
from .plotting import pyplot, save


def create_demo(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = synthetic(64, seed=12, colors=2, skewed=False, correlated=True)
    w = similarities(data.features)
    initial = average_linkage(w, data.labels)
    result = make_fair(initial, data.labels, h=16, k=2, epsilon=1 / 64, trace=True)
    events = []
    for event in result.trace:
        tree = Tree.from_dict(event["tree"])
        metrics = evaluate(tree, w, data.labels)
        events.append({**event, "metrics": metrics})
    payload = {
        "events": events,
        "parameters": result.diagnostics["parameters"],
        "seed": 12,
        "source": "synthetic(64, seed=12, colors=2, correlated=True)",
        "diagnostics": result.diagnostics,
    }
    content = TEMPLATE.replace(
        "__DATA__", json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c")
    )
    output.write_text(content)
    output.with_suffix(".trace.json").write_text(json.dumps(payload, indent=2) + "\n")
    plt = pyplot()
    fig, axes = plt.subplots(
        2, 2, figsize=(12, 7), layout="constrained", gridspec_kw={"height_ratios": [2, 1]}
    )
    for column, (tree, title) in enumerate(
        [(initial, "Average linkage"), (result.tree, "MakeFair")]
    ):
        ax = axes[0, column]
        nodes = list(preorder(tree.root))
        leaves = [n for n in nodes if n.is_leaf]
        pos = {n: (i, 0) for i, n in enumerate(leaves)}
        for node in postorder(tree.root):
            if node.children:
                pos[node] = (
                    sum(pos[c][0] for c in node.children) / len(node.children),
                    max(pos[c][1] for c in node.children) + 1,
                )
                for c in node.children:
                    ax.plot(
                        [pos[c][0], pos[c][0], pos[node][0]],
                        [pos[c][1], pos[node][1], pos[node][1]],
                        color="#8d9ba1",
                        lw=0.7,
                    )
        for leaf in leaves:
            ax.scatter(
                *pos[leaf],
                s=14,
                color=["#007e87", "#d46143"][int(tree.labels[leaf.leaf_id])],
                zorder=3,
            )
        m = evaluate(tree, w, data.labels)
        ax.set_title(
            f"{title} · cost {m['cost']:.1f}\n{m['cluster_count']} nonsingleton clusters · depth {m['depth']}"
        )
        ax.set(xlabel="Leaves in tree order", ylabel="Subtree height")
        stats = m["clusters"]
        axes[1, column].scatter(
            [c["size"] for c in stats],
            [c["proportions"][0] for c in stats],
            color="#007e87",
            alpha=0.7,
            s=24,
        )
        axes[1, column].axhline(0.5, color="#d46143", ls="--", lw=1)
        axes[1, column].set(
            xlabel="Cluster size", ylabel="Color 0 proportion", ylim=(-0.04, 1.04), xscale="log"
        )
    fig.suptitle(
        "A traced 64-point example · h=16, k=2, ε=1/64 · no approximation-to-optimum claim",
        fontsize=12,
    )
    save(fig, output.parent, "demo-companion", plt)
    print(f"Wrote {output} with {len(events)} actual trace states")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MakeFair — a worked example</title>
<style>
:root{color-scheme:light;--ink:#17363e;--muted:#526b73;--teal:#007e87;--coral:#d46143;--line:#d6e1e2}
*{box-sizing:border-box}body{margin:0;background:#f4f7f6;color:var(--ink);font:16px/1.5 system-ui,sans-serif}
main{max-width:1420px;margin:auto;padding:36px 28px}header{max-width:920px}h1{font-size:clamp(30px,4vw,48px);letter-spacing:-1.5px;line-height:1.1;margin:10px 0 18px}h2{font-size:20px;margin:0 0 8px}.eyebrow{text-transform:uppercase;letter-spacing:.15em;font-size:12px;color:var(--teal);font-weight:700}p{color:var(--muted)}.controls{position:sticky;top:0;z-index:2;background:#f4f7f6ee;backdrop-filter:blur(8px);border-block:1px solid var(--line);padding:14px 0;margin:22px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}button{font:inherit;border:1px solid #a8bbbe;border-radius:7px;background:white;color:var(--ink);padding:8px 12px;cursor:pointer}button:hover{background:#e2eeee}button:disabled{opacity:.4;cursor:default}button:focus-visible,input:focus-visible{outline:3px solid #d48a12;outline-offset:3px}input{flex:1;min-width:160px;accent-color:var(--teal)}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:20px}.stat,.card{min-width:0;overflow-wrap:anywhere;background:white;border:1px solid var(--line);border-radius:12px;padding:18px}.stat strong{display:block;font-size:28px;font-variant-numeric:tabular-nums}.stat span{font-size:13px;color:var(--muted)}.layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:18px}.card p{margin:6px 0 12px}.scroll{max-width:100%;overflow:auto}svg{width:100%;min-width:720px;height:440px}.node{cursor:pointer}.node:focus{outline:none}.node:focus circle{stroke:#d48a12;stroke-width:4}.edge{stroke:#bccbd0;stroke-width:1;fill:none}table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;border-bottom:1px solid var(--line);padding:8px 4px}.legend{display:flex;gap:20px;font-size:13px;flex-wrap:wrap}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}.note{background:#fff4db;border-left:3px solid #d48a12;padding:10px;font-size:13px}.event{font-size:18px;color:var(--ink);min-height:62px}footer{font-size:13px;margin-top:25px;color:var(--muted)}#inspect{overflow-wrap:anywhere}details{margin:15px 0}summary{cursor:pointer}code{font-size:13px}@media(max-width:900px){main{padding:22px 14px}.layout{grid-template-columns:minmax(0,1fr)}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.controls{position:static}svg{height:390px}}
@media(max-width:360px){.stats{grid-template-columns:1fr}}
</style></head><body><main>
<header><div class="eyebrow">Fair hierarchical clustering · reproducible notebook</div><h1>Follow the tree, one operation at a time.</h1><p>Start with average linkage on 64 synthetic points whose geometry is correlated with color. Watch subtree moves balance a split, then follow density-ordered folds and the terminal stars that finish the hierarchy.</p></header>
<div class="legend"><span><i class="dot" style="background:#007e87"></i>Color 0</span><span><i class="dot" style="background:#d46143"></i>Color 1</span><span><i class="dot" style="background:#e5a52b"></i>Moved, recipient, or folded node</span></div>
<nav class="controls" aria-label="Trace navigation"><button id="first">Start</button><button id="prev" aria-label="Previous step">← Back</button><button id="next">Next →</button><button id="fold">Next fold</button><input id="slider" type="range" min="0" value="0" aria-label="Trace step"><span id="position"></span><button id="last">Final tree</button></nav>
<section class="stats" aria-label="Current tree metrics"><div class="stat"><span>Dasgupta cost</span><strong id="cost"></strong><span id="ratio"></span></div><div class="stat"><span>Nonsingleton clusters</span><strong id="clusters"></strong><span id="depth"></span></div><div class="stat"><span>Max color-proportion deviation</span><strong id="error"></strong><span>From global proportions: 50% / 50%</span></div><div class="stat"><span>Largest size imbalance</span><strong id="imbalance"></strong><span>Actual relative child-size deviation</span></div></section>
<section class="layout"><div class="card"><div class="eyebrow" id="phase"></div><p class="event" id="event" aria-live="polite"></p><div class="scroll"><svg id="tree" role="img" aria-label="Current hierarchy; select a cluster for its composition"></svg></div><p style="font-size:12px">Leaf IDs preserve matrix rows. Branch heights show topology, not distance. Node color shows composition. Select a node to inspect it.</p></div><aside class="card"><h2>Cluster inspector</h2><div id="inspect"></div><h2 style="margin-top:22px">Parameters</h2><table><tr><th>Seed</th><td>12</td></tr><tr><th>h / k / colors</th><td>16 / 2 / 2</td></tr><tr><th>ε</th><td>1/64</td></tr><tr><th>Children after folds</th><td>16 / 2² = 4</td></tr><tr><th>Recursion threshold</th><td>32 leaves</td></tr></table><p class="note">Terminal stars trade hierarchy resolution for representation. Lower error alone does not establish a better hierarchy.</p></aside></section>
<details><summary>What the steps mean</summary><p><b>Move:</b> transfer the selected donor subtree to the recipient, contracting the donor’s old parent. <b>Fold:</b> sort root children by one color’s density, divide into k contiguous chunks, and merge corresponding positions. <b>Terminal:</b> replace a subtree below the size threshold, or one whose prescribed integer split cannot proceed, with a star.</p><p>Empty placeholders carry no data and are omitted from the drawing. Intermediate descendants need not satisfy fairness. Folding balance is measured anew; ε is never silently rescaled. This example uses raw coordinates and similarity 1/(1 + Euclidean distance).</p></details>
<footer>Generated from actual Python operation traces. All data and controls are embedded; this page works offline. Costs are compared with the same starting hierarchy, not an unknown optimum. Arrow keys navigate the steps.</footer>
</main><script>
const DATA=__DATA__;const events=DATA.events;let step=0,selected=null;
const el=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
function svg(tag,attrs,parent){let n=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));parent.appendChild(n);return n;}
function state(e){const map=new Map(e.tree.nodes.map(n=>[n.id,{...n}]));const order=[],stack=[[e.tree.root,0]];while(stack.length){const [id,d]=stack.pop(),n=map.get(id);n.depth=d;order.push(n);n.children.slice().reverse().forEach(c=>stack.push([c,d+1]));}let index=0;for(const n of order){if(n.leaf_id!==null){n.x=25+(index+++.5)*950/64;n.counts=[0,0];n.counts[Number(e.tree.labels[n.leaf_id])]=1;n.size=1;}}for(const n of order.slice().reverse()){if(n.children.length){n.counts=[0,0];n.children.forEach(id=>{let c=map.get(id);n.counts[0]+=c.counts[0];n.counts[1]+=c.counts[1];});n.size=n.counts[0]+n.counts[1];n.x=n.children.reduce((a,id)=>a+map.get(id).x,0)/n.children.length;}}const maxDepth=Math.max(...order.map(n=>n.depth));for(const n of order)n.y=n.leaf_id!==null?390:25+n.depth*340/Math.max(maxDepth,1);return{map,order};}
function inspect(n){if(!n)return;el('inspect').innerHTML=`<p><b>${n.leaf_id!==null?'Leaf '+n.leaf_id:'Node '+n.id}</b> · ${n.size} ${n.size===1?'point':'points'}</p><table><tr><th>Color</th><th>Count</th><th>Share</th></tr>${n.counts.map((v,i)=>`<tr><td>${i}</td><td>${v}</td><td>${(100*v/n.size).toFixed(1)}%</td></tr>`).join('')}<tr><th>Children</th><td colspan="2">${n.children.length}</td></tr></table>`;}
function render(){const e=events[step],m=e.metrics,first=events[0].metrics;const {map,order}=state(e);el('position').textContent=`${step+1} / ${events.length}`;el('slider').value=step;el('prev').disabled=step===0;el('first').disabled=step===0;el('next').disabled=step===events.length-1;el('last').disabled=step===events.length-1;el('fold').disabled=!events.slice(step+1).some(e=>e.operation==='fold');el('cost').textContent=m.cost.toFixed(1);el('ratio').textContent=`${(m.cost/first.cost).toFixed(3)}× starting cost (${first.cost.toFixed(1)})`;el('clusters').textContent=m.cluster_count;el('depth').textContent=`Hierarchy depth ${m.depth}`;el('error').textContent=m.max_representation_error.toFixed(3);el('imbalance').textContent=m.max_size_imbalance.toFixed(3);el('phase').textContent=e.operation;const text={start:'The original average-linkage hierarchy.',move:`Move donor ${e.donor} (${e.leaves} leaves) to recipient ${e.recipient}.`,split:`Root ${e.root} now has balanced children: ${(e.sizes||[]).join(', ')}.`,fold:`Fold ${e.groups?.length} groups for color ${e.color}; resulting sizes: ${(e.sizes||[]).join(', ')}.`,terminal:`Make node ${e.root} a terminal star: ${(e.reason||'').replaceAll('_',' ')}.`,finish:'The completed nonbinary hierarchy. Compare its cost, representation, and resolution with the start.'};el('event').textContent=text[e.operation];let target=el('tree');target.replaceChildren();target.setAttribute('viewBox','0 0 1000 430');const highlight=new Set([e.donor,e.recipient,...(e.folded||[])]);for(const n of order){for(const id of n.children){const c=map.get(id);svg('path',{d:`M${n.x},${n.y} V${(n.y+c.y)/2} H${c.x} V${c.y}`,class:'edge'},target);}}for(const n of order){const g=svg('g',{class:'node',tabindex:0,role:'button','aria-label':`Node ${n.id}, ${n.size} points`},target);const p=n.counts[0]/n.size;const color=`rgb(${Math.round(0*p+212*(1-p))},${Math.round(126*p+97*(1-p))},${Math.round(135*p+67*(1-p))})`;svg('circle',{cx:n.x,cy:n.y,r:n.leaf_id===null?Math.min(8,4+Math.log2(n.size)/2):3.5,fill:color,stroke:highlight.has(n.id)?'#e5a52b':'white','stroke-width':highlight.has(n.id)?4:1},g);let title=svg('title',{},g);title.textContent=`ID ${n.id} · size ${n.size} · colors ${n.counts.join(' / ')}`;if(n.leaf_id!==null){let label=svg('text',{x:n.x,y:410,'font-size':8,'text-anchor':'middle',fill:'#526b73'},g);label.textContent=n.leaf_id;}g.onclick=()=>{selected=n.id;inspect(n);};g.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selected=n.id;inspect(n);}};}inspect(map.get(selected)??map.get(e.root??e.tree.root));}
function go(n){step=Math.max(0,Math.min(events.length-1,n));render();}el('slider').max=events.length-1;el('slider').oninput=e=>go(Number(e.target.value));el('prev').onclick=()=>go(step-1);el('next').onclick=()=>go(step+1);el('first').onclick=()=>go(0);el('last').onclick=()=>go(events.length-1);el('fold').onclick=()=>{let next=events.findIndex((e,i)=>i>step&&e.operation==='fold');if(next>=0)go(next);};document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;if(e.key==='ArrowRight'){e.preventDefault();go(step+1);}if(e.key==='ArrowLeft'){e.preventDefault();go(step-1);}});render();
</script></body></html>"""
