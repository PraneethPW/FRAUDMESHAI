import { useQuery } from '@tanstack/react-query'
import { Bot, BrainCircuit, KeyRound, LockKeyhole, ScrollText, Settings2, ShieldCheck, Users } from 'lucide-react'
import { ErrorState, GraphLoader, PageIntro, Panel, PanelTitle, RiskBadge } from '../components/UI'
import { api, errorMessage } from '../lib/api'

interface AdminData {
  users:Array<{id:string;email:string;full_name:string;role:string;is_active:boolean}>
  models:Array<{id:string;name:string;version:string;type:string;active:boolean}>
  risk_thresholds:{medium:number;high:number;critical:number}
  ai_provider:{configured:boolean;provider:string}
  audit_logs:Array<{id:string;action:string;resource_type?:string;created_at:string}>
}

export default function Admin() {
  const {data,isLoading,error}=useQuery<AdminData>({queryKey:['admin'],queryFn:()=>api.get('/admin/overview').then((response)=>response.data),retry:false})
  if(isLoading)return <GraphLoader label="Verifying administrative authority"/>
  if(error)return <div className="admin-denied"><LockKeyhole/><h1>Administrative clearance required</h1><p>{errorMessage(error)}</p><span>Sign in as the development admin to inspect protected configuration.</span></div>
  if(!data)return <ErrorState message="Administrative data unavailable"/>
  return <><PageIntro eyebrow="Protected control plane" title="Administration" text="Workspace users, model versions, risk policy, provider state, and sensitive audit history." actions={<div className="admin-verified"><ShieldCheck/><span><b>ADMIN session</b><small>Role enforcement active</small></span></div>}/><div className="admin-grid"><Panel className="admin-users"><PanelTitle aside={<Users/>}>Workspace users</PanelTitle><div className="admin-list">{data.users.map((user)=><div key={user.id}><span>{user.full_name.split(' ').map((part)=>part[0]).slice(0,2).join('')}</span><div><b>{user.full_name}</b><small>{user.email}</small></div><em>{user.role}</em><i className={user.is_active?'active':''}/></div>)}</div></Panel><Panel><PanelTitle aside={<Settings2/>}>Risk policy</PanelTitle><div className="thresholds">{Object.entries(data.risk_thresholds).map(([level,value])=><div key={level}><RiskBadge level={level.toUpperCase()}/><span><i style={{width:`${value*100}%`}}/></span><b>{Math.round(value*100)}%</b></div>)}</div><p className="policy-note">Thresholds load from secure backend environment configuration.</p></Panel><Panel><PanelTitle aside={<BrainCircuit/>}>Model versions</PanelTitle><div className="model-version-list">{data.models.map((model)=><div key={model.id}><BrainCircuit/><span><b>{model.name}</b><small>{model.type} · {model.version}</small></span><em>{model.active?'ACTIVE':'INACTIVE'}</em></div>)}</div></Panel><Panel><PanelTitle aside={<Bot/>}>AI provider</PanelTitle><div className="provider-state"><div className={data.ai_provider.configured?'configured':''}><KeyRound/></div><h3>{data.ai_provider.provider}</h3><p>{data.ai_provider.configured?'Provider and model are configured through the environment.':'AI Investigation Assistant unavailable. Core fraud detection remains operational.'}</p></div></Panel><Panel className="audit-panel"><PanelTitle aside={<ScrollText/>}>Sensitive action audit</PanelTitle><div className="audit-list">{data.audit_logs.map((log)=><div key={log.id}><i/><span><b>{log.action.replaceAll('_',' ')}</b><small>{log.resource_type??'system'} · {new Date(log.created_at).toLocaleString()}</small></span></div>)}</div></Panel></div></>
}

