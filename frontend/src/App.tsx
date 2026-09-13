import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import { GraphLoader } from './components/UI'
import { useAuth } from './store/auth'

const Landing = lazy(() => import('./pages/Landing'))
const Auth = lazy(() => import('./pages/Auth'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Transactions = lazy(() => import('./pages/Transactions'))
const TransactionDetail = lazy(() => import('./pages/Transactions').then((module) => ({ default: module.TransactionDetail })))
const GraphExplorer = lazy(() => import('./pages/Graph'))
const FraudRings = lazy(() => import('./pages/Graph').then((module) => ({ default: module.FraudRings })))
const Alerts = lazy(() => import('./pages/Alerts'))
const AlertDetail = lazy(() => import('./pages/Alerts').then((module) => ({ default: module.AlertDetail })))
const Cases = lazy(() => import('./pages/Cases'))
const CaseDetail = lazy(() => import('./pages/Cases').then((module) => ({ default: module.CaseDetail })))
const Assistant = lazy(() => import('./pages/Assistant'))
const Models = lazy(() => import('./pages/Models'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const Profile = lazy(() => import('./pages/Profile'))
const Admin = lazy(() => import('./pages/Admin'))

function Protected({ children }: { children: ReactNode }) {
  const token = useAuth((state) => state.accessToken)
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return <Suspense fallback={<GraphLoader />}><Routes>
    <Route path="/" element={<Landing/>}/>
    <Route path="/login" element={<Auth/>}/>
    <Route path="/reset-password" element={<ResetPassword/>}/>
    <Route path="/register" element={<Auth/>}/>
    <Route path="/app" element={<Protected><AppShell/></Protected>}>
      <Route index element={<Dashboard/>}/>
      <Route path="transactions" element={<Transactions/>}/>
      <Route path="transactions/:transactionId" element={<TransactionDetail/>}/>
      <Route path="graph" element={<GraphExplorer/>}/>
      <Route path="rings" element={<FraudRings/>}/>
      <Route path="alerts" element={<Alerts/>}/>
      <Route path="alerts/:alertId" element={<AlertDetail/>}/>
      <Route path="cases" element={<Cases/>}/>
      <Route path="cases/:caseId" element={<CaseDetail/>}/>
      <Route path="assistant" element={<Assistant/>}/>
      <Route path="models" element={<Models/>}/>
      <Route path="profile" element={<Profile/>}/>
      <Route path="admin" element={<Admin/>}/>
    </Route>
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes></Suspense>
}
