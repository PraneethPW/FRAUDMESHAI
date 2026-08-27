import Lenis from 'lenis'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowRight, ArrowUpRight, Binary, Bot, Braces, CheckCircle2, Clock3, Fingerprint, GitBranch, Layers3, Network, Radar, ScanSearch, ShieldCheck, Sparkles, Workflow } from 'lucide-react'
import { lazy, Suspense, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const HeroNetwork = lazy(() => import('../components/HeroNetwork'))

const flow = [
  { icon: Binary, label: 'Transaction', text: 'Streaming events enter a workspace-scoped evidence pipeline.' },
  { icon: Network, label: 'Graph', text: 'Entities become a living heterogeneous relationship map.' },
  { icon: Clock3, label: 'Temporal model', text: 'Velocity, change, and time decay reveal coordinated behavior.' },
  { icon: ScanSearch, label: 'XAI', text: 'Every score resolves into inspectable signals and paths.' },
  { icon: Workflow, label: 'Case', text: 'Verified evidence moves into a complete analyst workflow.' },
]

const stream = [
  { id: 'TX-84219', merchant: 'Northstar Electronics', amount: '$8,420', score: 94 },
  { id: 'TX-84218', merchant: 'Meridian Market', amount: '$148', score: 12 },
  { id: 'TX-84217', merchant: 'Orbit Travel', amount: '$2,240', score: 47 },
  { id: 'TX-84216', merchant: 'Atlas Digital', amount: '$6,910', score: 88 },
]

export default function Landing() {
  const [activeStream, setActiveStream] = useState(0)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    gsap.registerPlugin(ScrollTrigger)
    const lenis = new Lenis({ duration: 1.15, smoothWheel: true })
    const raf = (time: number) => { lenis.raf(time); frame = requestAnimationFrame(raf) }
    let frame = requestAnimationFrame(raf)
    const sections = gsap.utils.toArray<HTMLElement>('[data-reveal]')
    sections.forEach((section) => gsap.fromTo(section, { opacity: 0, y: 54, filter: 'blur(10px)' }, { opacity: 1, y: 0, filter: 'blur(0)', duration: 1, scrollTrigger: { trigger: section, start: 'top 84%' } }))
    return () => { cancelAnimationFrame(frame); lenis.destroy(); ScrollTrigger.getAll().forEach((trigger) => trigger.kill()) }
  }, [])
  useEffect(() => { const timer = window.setInterval(() => setActiveStream((value) => (value + 1) % stream.length), 1800); return () => clearInterval(timer) }, [])
  return <main className="landing min-h-screen">
    <nav className="landing-nav">
      <Link className="brand" to="/"><span className="brand-mark"><Network /></span>FraudMesh <b>XAI</b></Link>
      <div className="landing-links"><a href="#intelligence">Intelligence</a><a href="#explainability">Explainability</a><a href="#workflow">Workflow</a></div>
      <div className="landing-actions"><Link to="/login">Sign in</Link><Link className="nav-cta" to="/login">Launch console <ArrowUpRight /></Link></div>
    </nav>
    <section className="landing-hero">
      <div className="hero-grid" />
      <div className="landing-network"><Suspense fallback={<div className="network-fallback"><Network /></div>}><HeroNetwork /></Suspense></div>
      <div className="hero-copy landing-copy">
        <motion.div className="eyebrow" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}><ShieldCheck /> Explainable temporal graph intelligence</motion.div>
        <motion.h1 initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .08 }}>See the fraud network.<br /><em>Not just the transaction.</em></motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .18 }}>Temporal graph intelligence for detecting coordinated financial fraud, explaining suspicious relationships, and accelerating investigations.</motion.p>
        <motion.div className="hero-actions" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .25 }}><Link className="primary-action" to="/login">Launch investigation console <ArrowUpRight /></Link><a className="secondary-action" href="#network">Explore fraud network <ArrowRight /></a></motion.div>
        <div className="hero-proof"><div><strong>7</strong><span>connected entity types</span></div><div><strong>Real-time</strong><span>simulation stream</span></div><div><strong>Grounded</strong><span>explanation layer</span></div></div>
      </div>
      <div className="hero-signal-card"><div><Radar /><span>Coordinated cluster</span><b>94</b></div><p>Shared infrastructure links four accounts across a compressed transaction window.</p><small><i /> Detection event · simulated</small></div>
      <div className="scroll-cue"><span>Trace the network</span><i /></div>
    </section>

    <section className="problem-section" id="intelligence" data-reveal>
      <div className="section-kicker">The blind spot</div><h2>Fraud rarely arrives alone.<br /><em>Legacy scoring acts like it does.</em></h2>
      <div className="problem-grid"><div className="isolated-card"><span>Isolated transaction</span><div className="isolated-score"><b>18</b><small>LOW RISK</small></div><ul><li><CheckCircle2 /> Amount within range</li><li><CheckCircle2 /> Merchant recognized</li><li><CheckCircle2 /> Account history normal</li></ul></div><div className="versus"><ArrowRight /></div><div className="connected-card"><span>Connected behavior</span><div className="mini-topology"><i/><i/><i/><i/><i/><svg viewBox="0 0 300 160"><path d="M40 35L145 75L255 30M145 75L55 135M145 75L245 132M55 135L245 132"/></svg></div><div className="network-verdict"><b>94</b><span><strong>CRITICAL NETWORK RISK</strong><small>4 accounts · 1 shared device · 2 shared IPs</small></span></div></div></div>
    </section>

    <section className="network-story" id="network" data-reveal>
      <div className="story-copy"><div className="section-kicker">Network intelligence</div><h2>One event becomes<br />a field of evidence.</h2><p>FraudMesh constructs a heterogeneous financial graph as activity arrives. Accounts, devices, IPs, merchants, customers, locations, and transactions retain both their relationships and their timing.</p><div className="story-questions"><span><Fingerprint /> Who is connected?</span><span><GitBranch /> How are they connected?</span><span><Clock3 /> When did it happen?</span><span><Radar /> How quickly is it changing?</span></div></div>
      <div className="story-visual"><div className="topology-rings"><i/><i/><i/></div>{['ACC-704','DEV-X104','185.71.67.44','ORBIT TRAVEL','ACC-721'].map((label,index)=><motion.div key={label} className={`story-node node-${index}`} animate={{ y: [0, index % 2 ? 7 : -7, 0] }} transition={{ repeat: Infinity, duration: 4 + index, ease: 'easeInOut' }}><span/><small>{label}</small></motion.div>)}<svg viewBox="0 0 600 460"><path d="M80 105L260 210L490 96M260 210L110 365M260 210L480 358M110 365L480 358"/></svg></div>
    </section>

    <section className="pipeline-section" data-reveal>
      <div className="section-kicker">From signal to decision</div><h2>A continuous investigation pipeline.</h2><div className="pipeline">{flow.map(({ icon: Icon, label, text }, index)=><div className="pipeline-step" key={label}><div className="step-head"><span>{String(index+1).padStart(2,'0')}</span><Icon /></div><h3>{label}</h3><p>{text}</p>{index < flow.length-1 && <ArrowRight className="step-arrow" />}</div>)}</div>
    </section>

    <section className="xai-section" id="explainability" data-reveal>
      <div className="xai-console"><div className="console-bar"><span><i/> ALERT / AL-9218</span><small>SIMULATED EVIDENCE</small></div><div className="alert-hero"><div className="alert-score"><b>94</b><span>fraud probability</span></div><div><span className="critical-pill">CRITICAL</span><h3>Coordinated infrastructure reuse</h3><p>Four accounts converged on the same device and IP within eleven minutes.</p></div></div><div className="evidence-bars">{[['Graph relationship risk',31],['Behavioral anomaly',27],['Velocity anomaly',21],['Device sharing risk',11],['Location anomaly',4]].map(([label,value])=><div key={String(label)}><span>{label}</span><i><b style={{width:`${Number(value)*3}%`}}/></i><strong>{value}%</strong></div>)}</div><div className="evidence-path"><span>ACC-704</span><ArrowRight/><span>DEV-X104</span><ArrowRight/><span>ACC-721</span><ArrowRight/><span>ORBIT TRAVEL</span></div></div>
      <div className="xai-copy"><div className="section-kicker">Explainable AI</div><h2>Every score arrives<br />with its reasoning.</h2><p>Analysts can inspect the neighborhood, temporal anomalies, suspicious paths, and contribution of each verified feature—without treating the model as an oracle.</p><ul><li><ShieldCheck /> Structured evidence, never invented reasons</li><li><Braces /> Model version and prediction time preserved</li><li><Bot /> Optional summaries grounded only in case evidence</li></ul><Link to="/login">Inspect an alert <ArrowUpRight /></Link></div>
    </section>

    <section className="realtime-section" data-reveal>
      <div><div className="section-kicker">Live detection</div><h2>Watch the graph evolve<br />with every event.</h2><p>A clearly labelled simulation mode generates realistic transaction traffic, executes scoring, updates the graph, and pushes alerts through a WebSocket stream.</p><div className="sim-controls"><button><span /> Running</button><button>5 events / sec</button></div></div>
      <div className="stream-card"><div className="stream-head"><span><i/> LIVE TRANSACTION STREAM</span><small>SIMULATED DATA</small></div><AnimatePresence mode="popLayout">{stream.map((item,index)=><motion.div layout key={item.id} className={`stream-row ${index===activeStream?'active':''}`} initial={{opacity:0,x:18}} animate={{opacity:1,x:0}}><small>{item.id}</small><span>{item.merchant}</span><b>{item.amount}</b><em className={item.score>70?'hot':''}>{item.score}</em></motion.div>)}</AnimatePresence></div>
    </section>

    <section className="workflow-section" id="workflow" data-reveal><div className="section-kicker">Investigator workflow</div><h2>Evidence stays connected<br />from alert to audit.</h2><div className="workflow-line">{['Alert','Evidence','Graph','AI summary','Analyst decision'].map((item,index)=><div key={item}><span>{index+1}</span><b>{item}</b>{index<4&&<i/>}</div>)}</div></section>

    <section className="tech-section" data-reveal><div className="section-kicker">Intelligence layer</div><h2>Designed for operational truth.</h2><div className="tech-grid"><article><Layers3/><h3>Temporal graph engine</h3><p>Relational graph persistence with time-aware rolling aggregation and decay-weighted neighborhood risk.</p></article><article><Binary/><h3>Multi-model lab</h3><p>Executed Logistic Regression, XGBoost, static graph, and temporal graph evaluations.</p></article><article><Sparkles/><h3>Grounded summaries</h3><p>Provider abstraction for OpenRouter and OpenAI, with an explicit no-key fallback.</p></article></div></section>

    <section className="demo-stats" data-reveal><span>DEMONSTRATION CAPABILITIES · NOT CUSTOMER CLAIMS</span><div><article><b>7</b><p>entity types mapped</p></article><article><b>4</b><p>model families compared</p></article><article><b>5</b><p>evidence dimensions</p></article><article><b>17</b><p>step demo narrative</p></article></div></section>
    <section className="testimonials" data-reveal><div className="section-kicker">Prototype stakeholder feedback</div><div className="quote-grid"><blockquote>“The relationship-first view turns an abstract risk score into something an investigator can actually challenge.”<footer>Risk operations lead <span>· prototype review</span></footer></blockquote><blockquote>“The strongest part is the continuity—from a live signal to a case, decision, and auditable history.”<footer>FinTech product advisor <span>· prototype review</span></footer></blockquote></div></section>
    <section className="final-cta" data-reveal><div className="cta-glow"/><Network/><span>FRAUD DOESN'T HAPPEN IN ISOLATION</span><h2>Investigate the network<br />behind the transaction.</h2><Link to="/login">Enter FraudMesh XAI <ArrowUpRight /></Link></section>
    <footer className="landing-footer"><Link className="brand" to="/"><span className="brand-mark"><Network /></span>FraudMesh <b>XAI</b></Link><p>Explainable temporal graph intelligence · Research demonstration</p><span>© 2026 FraudMesh XAI</span></footer>
  </main>
}
