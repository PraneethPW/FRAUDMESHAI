import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, errorMessage } from '../lib/api'
import { useAuth } from '../store/auth'
import { PageIntro, Panel, PanelTitle } from '../components/UI'
export default function Profile() {
  const user=useAuth((s)=>s.user)
  const change=useMutation({mutationFn:(form:HTMLFormElement)=>api.post('/auth/change-password',Object.fromEntries(new FormData(form))),onSuccess:()=>toast.success('Password changed'),onError:(e)=>toast.error(errorMessage(e))})
  return <><PageIntro eyebrow="Account" title={user?.full_name??'Your profile'} text={`${user?.email} · ${user?.role}`}/><Panel className="train-panel"><PanelTitle>Change password</PanelTitle><form onSubmit={(e)=>{e.preventDefault();change.mutate(e.currentTarget)}}><label>Current password<input type="password" autoComplete="current-password" name="current_password" required/></label><label>New password<input type="password" autoComplete="new-password" name="new_password" minLength={10} maxLength={128} required/></label><button className="button-primary" disabled={change.isPending}>Save password</button></form></Panel></>
}
