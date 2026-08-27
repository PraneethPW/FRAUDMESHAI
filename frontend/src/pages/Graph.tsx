import { useMutation, useQuery } from '@tanstack/react-query'
import cytoscape, { type Core } from 'cytoscape'
import { Boxes, ChevronDown, CircleDot, Crosshair, Filter, Focus, GitBranch, Orbit, Radar, Search, Share2, Sparkles, ZoomIn, ZoomOut } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { EmptyState, ErrorState, GraphLoader, PageIntro, Panel, RiskBadge, ScoreRing } from '../components/UI'
import { api, errorMessage } from '../lib/api'
import type { GraphResponse, InvestigationCase, Ring } from '../types'

const nodeColors: Record<string,string> = { CUSTOMER:'#60d6ff',ACCOUNT:'#a78bfa',TRANSACTION:'#f3f0ff',MERCHANT:'#65e6c4',DEVICE:'#ffba69',IP:'#ef70ff',LOCATION:'#5f7cff' }

export default function GraphExplorer() {
  const container = useRef<HTMLDivElement>(null)
  const graph = useRef<Core | null>(null)
  const [type, setType] = useState('ALL')
  const [minRisk, setMinRisk] = useState(0)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null)
  const { data, isLoading, error } = useQuery<GraphResponse>({ queryKey: ['graph',type,minRisk], queryFn: () => api.get(`/graph?${type==='ALL'?'':`node_type=${type}&`}min_risk=${minRisk}&limit=300`).then((response)=>response.data) })
  useEffect(() => {
    if (!container.current || !data) return
    graph.current?.destroy()
    graph.current = cytoscape({ container: container.current, elements: [...data.nodes,...data.edges], minZoom:.25, maxZoom:3, wheelSensitivity:.22, style: [
      { selector:'node', style:{ 'background-color':'#9b7cff','label':'data(label)','font-family':'DM Mono','font-size':8,'color':'#a9a1b6','text-valign':'bottom','text-margin-y':8,'width':20,'height':20,'border-width':2,'border-color':'#ffffff30','overlay-opacity':0 } },
      { selector:'node[risk >= 0.72]', style:{'border-color':'#ff5578','border-width':4,'background-color':'#ff5578'}},
      { selector:'edge', style:{'width':.7,'line-color':'#7a64a348','curve-style':'bezier','target-arrow-shape':'triangle','target-arrow-color':'#7a64a355','arrow-scale':.55,'opacity':.75}},
      { selector:'.focused', style:{'border-width':5,'border-color':'#ffffff','width':30,'height':30}},
      { selector:'.suspicious', style:{'line-color':'#ff5578','target-arrow-color':'#ff5578','width':2,'opacity':1}},
    ], layout:{name:'cose',animate:false,padding:45,nodeRepulsion:140000,idealEdgeLength:95,gravity:.25} })
    graph.current.on('tap','node',(event)=>setSelected(event.target.data() as Record<string,unknown>))
    return () => graph.current?.destroy()
  }, [data])
  const focusSearch = () => { const cy=graph.current; if(!cy||!search)return; cy.elements().removeClass('focused'); const match=cy.nodes().filter((node)=>String(node.data('label')).toLowerCase().includes(search.toLowerCase())).first(); if(match.nonempty()){match.addClass('focused');cy.animate({fit:{eles:match,padding:130},duration:450});setSelected(match.data() as Record<string,unknown>)} else toast.error('No graph entity matched that search') }
  const highlightSuspicious = () => { const cy=graph.current;if(!cy)return;cy.elements().removeClass('suspicious');cy.edges().filter((edge)=>Number(edge.source().data('risk'))>=.65||Number(edge.target().data('risk'))>=.65).addClass('suspicious');toast.success('Suspicious paths highlighted') }
  if(isLoading)return <GraphLoader label="Constructing heterogeneous graph"/>
  if(error||!data)return <ErrorState message={errorMessage(error)}/>
  return <>
    <PageIntro eyebrow="Flagship intelligence surface" title="Fraud graph explorer" text="Inspect heterogeneous entity relationships, temporal edges, communities, and suspicious paths." actions={<div className="graph-stats"><span><b>{data.meta?.nodes??0}</b> nodes</span><span><b>{data.meta?.edges??0}</b> edges</span><span><b>{data.meta?.communities??0}</b> communities</span></div>}/>
    <Panel className="graph-panel"><div className="graph-toolbar"><label className="graph-search"><Search/><input value={search} onChange={(event)=>setSearch(event.target.value)} onKeyDown={(event)=>event.key==='Enter'&&focusSearch()} placeholder="Focus an account, device, IP…"/><button onClick={focusSearch}><Focus/></button></label><div><label><Filter/><select value={type} onChange={(event)=>setType(event.target.value)}><option>ALL</option>{Object.keys(nodeColors).map((item)=><option key={item}>{item}</option>)}</select><ChevronDown/></label><label>Risk ≥<select value={minRisk} onChange={(event)=>setMinRisk(Number(event.target.value))}><option value={0}>Any</option><option value={.45}>45%</option><option value={.72}>72%</option><option value={.9}>90%</option></select></label><button onClick={highlightSuspicious}><GitBranch/> Suspicious paths</button><button onClick={()=>graph.current?.fit(undefined,40)}><Crosshair/> Fit</button></div></div>
      <div className="graph-workspace"><div ref={container} className="cytoscape-canvas"/><div className="graph-legend">{Object.entries(nodeColors).map(([label,color])=><span key={label}><i style={{background:color}}/>{label}</span>)}</div><div className="zoom-controls"><button onClick={()=>graph.current?.zoom(graph.current.zoom()*1.2)}><ZoomIn/></button><button onClick={()=>graph.current?.zoom(graph.current.zoom()*.8)}><ZoomOut/></button><button onClick={()=>graph.current?.layout({name:'cose',animate:true,animationDuration:500}).run()}><Orbit/></button></div>{selected&&<div className="node-inspector"><div><span style={{background:nodeColors[String(selected.type)]}}><CircleDot/></span><button onClick={()=>setSelected(null)}>×</button></div><small>{String(selected.type)}</small><h3>{String(selected.label)}</h3><div><span>Risk score</span><b>{Math.round(Number(selected.risk)*100)}%</b></div><div><span>Community</span><b>#{Number(selected.community)+1}</b></div><button onClick={()=>{const cy=graph.current;const node=cy?.getElementById(String(selected.id));if(node)cy?.animate({fit:{eles:node.closedNeighborhood(),padding:80},duration:400})}}><Share2/> Expand neighborhood</button></div>}</div>
    </Panel>
  </>
}

export function FraudRings() {
  const { data=[],isLoading,error,refetch }=useQuery<Ring[]>({queryKey:['rings'],queryFn:()=>api.get('/fraud-rings').then((response)=>response.data),refetchInterval:7000})
  const createCase=useMutation({mutationFn:(ring:Ring)=>api.post<InvestigationCase>('/cases',{title:`Investigation · ${ring.name}`,severity:ring.risk_level,evidence:{ring_id:ring.id,...ring.properties}}),onSuccess:()=>{toast.success('Investigation case created from ring');void refetch()},onError:(err)=>toast.error(errorMessage(err))})
  if(isLoading)return <GraphLoader label="Detecting connected suspicious subgraphs"/>
  if(error)return <ErrorState message={errorMessage(error)}/>
  return <><PageIntro eyebrow="Coordinated threat discovery" title="Fraud ring detector" text="Dense communities and shared infrastructure clusters detected from persisted graph relationships." actions={<div className="detector-state"><Sparkles/><span><b>Community detection active</b><small>NetworkX modularity + shared infrastructure</small></span></div>}/>{data.length?<div className="ring-grid">{data.map((ring,index)=><Panel key={ring.id} className="ring-card"><div className="ring-head"><div><span>RING / {String(index+1).padStart(3,'0')}</span><h2>{ring.name}</h2></div><ScoreRing value={ring.risk_score} size={72}/></div><div className="ring-topology"><svg viewBox="0 0 420 170"><path d="M55 85L150 40L250 90L360 35M55 85L155 140L250 90L355 138M150 40L155 140"/></svg>{ring.members.slice(0,6).map((member,nodeIndex)=><i key={member.id} className={`ring-node ring-node-${nodeIndex}`} title={member.id}/>)}</div><div className="ring-reason"><Radar/><p>{ring.reason}</p></div><div className="ring-facts"><div><span>Accounts</span><b>{ring.members.filter((member)=>member.type==='ACCOUNT').length}</b></div><div><span>Shared device</span><b>{String(ring.properties.shared_device??'—')}</b></div><div><span>Suspicious amount</span><b>{new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(ring.estimated_amount)}</b></div></div><div className="ring-actions"><RiskBadge level={ring.risk_level}/><button onClick={()=>createCase.mutate(ring)} disabled={createCase.isPending}><Boxes/> Create case</button></div></Panel>)}</div>:<EmptyState title="No fraud rings detected yet" text="Start Simulation Mode. FraudMesh will surface a ring when multiple accounts converge on suspicious infrastructure."/>}</>
}
