import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'motion/react'
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Network, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'
import { api, errorMessage } from '../lib/api'
import { useAuth } from '../store/auth'
import type { TokenPair } from '../types'

const registerSchema = z.object({ email: z.email(), password: z.string().min(10), full_name: z.string().min(2), workspace_name: z.string().min(2) })
type AuthValues = z.infer<typeof registerSchema>

export default function Auth() {
  const isRegister = useLocation().pathname === '/register'
  const navigate = useNavigate()
  const setSession = useAuth((state) => state.setSession)
  const [show, setShow] = useState(false)
  const { register, handleSubmit, formState: { errors, isSubmitting }, setValue } = useForm<AuthValues>({ resolver: zodResolver(registerSchema), defaultValues: { email: '', password: '', full_name: 'Demo Analyst', workspace_name: 'Fraud Operations' } })
  const submit = async (values: AuthValues) => {
    try {
      const endpoint = isRegister ? '/auth/register' : '/auth/login'
      const { data } = await api.post<TokenPair>(endpoint, values)
      setSession(data)
      toast.success(isRegister ? 'Workspace secured and ready' : `Welcome back, ${data.user.full_name.split(' ')[0]}`)
      navigate('/app')
    } catch (error) { toast.error(errorMessage(error)) }
  }
  const fillDemo = () => { setValue('email', 'analyst@fraudmesh.dev'); setValue('password', 'FraudMesh!2026') }
  return <main className="auth-page">
    <div className="auth-grid"/><Link className="auth-back" to="/"><ArrowLeft/> Back to overview</Link>
    <section className="auth-visual"><Link className="brand" to="/"><span className="brand-mark"><Network /></span>FraudMesh <b>XAI</b></Link><div className="auth-orbit"><div><Network/><span>38</span><small>active signals</small></div>{[0,1,2,3,4].map((item)=><i key={item}/>)}</div><div className="auth-quote"><ShieldCheck/><h2>Investigate relationships.<br/>Decide with evidence.</h2><p>Every workspace is isolated. Every sensitive action is attributable. Every model score is explainable.</p></div></section>
    <motion.section className="auth-card" initial={{ opacity: 0, x: 25 }} animate={{ opacity: 1, x: 0 }}>
      <div className="auth-card-head"><span>{isRegister ? 'CREATE SECURE WORKSPACE' : 'INVESTIGATION CONSOLE'}</span><h1>{isRegister ? 'Begin your graph.' : 'Welcome back.'}</h1><p>{isRegister ? 'Set up a protected FraudMesh workspace for your investigation team.' : 'Authenticate to access workspace-scoped fraud intelligence.'}</p></div>
      {!isRegister && <button className="demo-credential" onClick={fillDemo}><span><b>Demo analyst</b><small>analyst@fraudmesh.dev</small></span><em>Use credentials <ArrowRight/></em></button>}
      <form onSubmit={handleSubmit(submit)}>
        {isRegister && <><label>Full name<input {...register('full_name')} placeholder="Your full name"/>{errors.full_name && <small>{errors.full_name.message}</small>}</label><label>Workspace name<input {...register('workspace_name')} placeholder="Fraud Operations"/>{errors.workspace_name && <small>{errors.workspace_name.message}</small>}</label></>}
        <label>Email address<input {...register('email')} type="email" autoComplete="email" placeholder="analyst@company.com"/>{errors.email && <small>{errors.email.message}</small>}</label>
        <label>Password<div className="password-field"><input {...register('password')} type={show ? 'text' : 'password'} autoComplete={isRegister ? 'new-password' : 'current-password'} placeholder="At least 10 characters"/><button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'}>{show ? <EyeOff/> : <Eye/>}</button></div>{errors.password && <small>{errors.password.message}</small>}</label>
        {!isRegister && <div className="form-options"><span>Secure workspace session</span><button type="button" onClick={() => navigate('/reset-password')}>Forgot password?</button></div>}
        <button className="auth-submit" disabled={isSubmitting}>{isSubmitting ? 'Securing session…' : isRegister ? 'Create workspace' : 'Enter investigation console'}<ArrowRight/></button>
      </form>
      <p className="auth-switch">{isRegister ? 'Already have access?' : 'Need a protected workspace?'} <Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Sign in' : 'Create one'}</Link></p>
      <div className="security-note"><LockKeyhole/><span><b>Secure by design</b><small>Argon2 password hashing · short-lived JWT · refresh token rotation</small></span></div>
    </motion.section>
  </main>
}
