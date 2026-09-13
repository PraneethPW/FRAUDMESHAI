import { useMutation } from '@tanstack/react-query'
import { useSearchParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { api, errorMessage } from '../lib/api'
export default function ResetPassword() {
  const [params]=useSearchParams();const token=params.get('token');const [message,setMessage]=useState('')
  const reset=useMutation({mutationFn:(form:HTMLFormElement)=>api.post(token?'/auth/reset-password':'/auth/forgot-password',{...Object.fromEntries(new FormData(form)),token}),onSuccess:({data})=>setMessage(data.message),onError:(e)=>setMessage(errorMessage(e))})
  return <main className="auth-page"><section className="auth-card"><div className="auth-card-head"><h1>{token?'Reset password':'Account recovery'}</h1><p>{token?'Choose a new password with at least 10 characters.':'Request a one-time password recovery link.'}</p></div><form onSubmit={(e)=>{e.preventDefault();reset.mutate(e.currentTarget)}}>{token?<label>New password<input type="password" name="new_password" minLength={10} maxLength={128} autoComplete="new-password" required/></label>:<label>Email address<input type="email" name="email" autoComplete="email" required/></label>}<button className="auth-submit" disabled={reset.isPending}>{reset.isPending?'Processing…':token?'Save new password':'Request recovery'}</button></form><p role="status">{message}</p><Link className="back-link" to="/login">Back to sign in</Link></section></main>
}
