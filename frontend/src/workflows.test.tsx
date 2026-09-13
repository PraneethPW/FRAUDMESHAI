import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Transactions from './pages/Transactions'
import Models from './pages/Models'
import { api } from './lib/api'

function mount(child:React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})}><MemoryRouter>{child}</MemoryRouter></QueryClientProvider>)
}
afterEach(()=>{cleanup();vi.restoreAllMocks()})

describe('v2 investigator controls',()=>{
  it('submits a transaction with numeric amount and keeps server validation errors visible',async()=>{
    vi.spyOn(api,'get').mockImplementation((url)=>Promise.resolve({data:url==='/simulation/status'?{state:'STOPPED',sequence:0}:[]}) as never)
    const post=vi.spyOn(api,'post').mockRejectedValue(new Error('Duplicate transaction conflict'))
    mount(<Transactions/>)
    fireEvent.click(await screen.findByRole('button',{name:'Submit transaction'}))
    for (const [label,value] of [['Account','A-1'],['Merchant ID','M-1'],['Merchant name','Shop'],['Device','D-1'],['IP address','198.51.100.1'],['Location','London'],['Amount','125.50']]) fireEvent.change(screen.getByLabelText(label,{exact:true}),{target:{value}})
    fireEvent.click(screen.getByRole('button',{name:'Score transaction'}))
    await waitFor(()=>expect(post).toHaveBeenCalledWith('/transactions',expect.objectContaining({amount:125.5,account_id:'A-1',currency:'USD'})))
    expect(screen.getByRole('button',{name:'Score transaction'})).toBeInTheDocument()
  })
  it('preserves the live monitor search field while server filtering is pending',async()=>{
    const get=vi.spyOn(api,'get').mockImplementation((url)=>Promise.resolve({data:url==='/simulation/status'?{state:'STOPPED'}:[]}) as never)
    mount(<Transactions/>)
    const input=await screen.findByPlaceholderText('Search feed')
    fireEvent.change(input,{target:{value:'Northstar'}})
    await waitFor(()=>expect(get).toHaveBeenCalledWith('/transactions',expect.objectContaining({params:expect.objectContaining({search:'Northstar',offset:0})})))
    expect(screen.getByPlaceholderText('Search feed')).toHaveValue('Northstar')
  })
  it('sends the selected workspace dataset and graph model to the training endpoint',async()=>{
    vi.spyOn(api,'get').mockResolvedValue({data:[]})
    const post=vi.spyOn(api,'post').mockRejectedValue(new Error('Not enough labelled transactions'))
    mount(<Models/>)
    await screen.findByRole('button',{name:'Execute training run'})
    fireEvent.change(screen.getByRole('combobox',{name:'Dataset'}),{target:{value:'WORKSPACE'}})
    fireEvent.change(screen.getByRole('combobox',{name:'Model family'}),{target:{value:'TEMPORAL_GNN'}})
    fireEvent.click(screen.getByRole('button',{name:'Execute training run'}))
    await waitFor(()=>expect(post).toHaveBeenCalledWith('/models/train',{model_type:'TEMPORAL_GNN',samples:1200,dataset:'WORKSPACE'},{timeout:180000}))
  })
})
