import React, { useEffect, useRef, useState } from 'react'
import { BookOpen, Coffee, Dumbbell, Edit3, LockKeyhole, Plus, Trash2, X } from 'lucide-react'
import { request } from './features'
import './life.css'

const config = {
  diary: { title:'日记手札', subtitle:'留一页给自己，记录今天的心情与故事。', icon:BookOpen, placeholder:'今天想记住什么？' },
  exercise: { title:'运动记录', subtitle:'记录每一次活动，慢慢积累更好的状态。', icon:Dumbbell, placeholder:'例如：慢跑、瑜伽、力量训练' },
  coffee: { title:'咖啡时光', subtitle:'记下一杯咖啡，也记下片刻的生活。', icon:Coffee, placeholder:'例如：拿铁 · 街角咖啡馆' },
}
const today = () => { const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }

export function LifePage({kind}) {
  const c=config[kind], Icon=c.icon, token=useRef('')
  const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[enabled,setEnabled]=useState(false),[unlocked,setUnlocked]=useState(kind!=='diary'),[password,setPassword]=useState(''),[error,setError]=useState(''),[dialog,setDialog]=useState(null),[saving,setSaving]=useState(false)
  async function call(path, options={}) {
    try { return await request(path,{...options,headers:{'X-Diary-Token':token.current}}) }
    catch(e) { if(e.message.includes('日记已锁定')){setRows([]);setUnlocked(false);setDialog(null)} throw e }
  }
  async function load(){setRows(await call(`life/${kind}`))}
  useEffect(()=>{
    if(kind!=='diary'||!enabled||!unlocked)return
    const timer=setTimeout(()=>{
      request('diary/lock',{method:'POST',body:'{}',headers:{'X-Diary-Token':token.current}}).catch(()=>{})
      token.current='';setRows([]);setDialog(null);setUnlocked(false)
    },1800000)
    return ()=>clearTimeout(timer)
  },[kind,enabled,unlocked,token.current])
  useEffect(()=>{
    let live=true
    async function init(){try{if(kind==='diary'){const status=await request('diary/status');if(!live)return;setEnabled(status.enabled);setUnlocked(!status.enabled);if(status.enabled)return}const data=await request(`life/${kind}`);if(live)setRows(data)}catch(e){if(live)setError(e.message)}finally{if(live)setLoading(false)}}
    init()
    return ()=>{live=false;if(kind==='diary'&&token.current)request('diary/lock',{method:'POST',body:'{}',headers:{'X-Diary-Token':token.current}}).catch(()=>{})}
  },[kind])
  async function unlock(e){e.preventDefault();setSaving(true);try{const result=await request('diary/unlock',{method:'POST',body:JSON.stringify({password})});token.current=result.token;await load();setUnlocked(true);setPassword('');setError('')}catch(e){setError(e.message)}finally{setSaving(false)}}
  async function lock(){try{await call('diary/lock',{method:'POST',body:'{}'});token.current='';setRows([]);setUnlocked(false);setError('')}catch(e){setError(e.message)}}
  async function save(values){setSaving(true);try{await call(dialog.id?`life/${kind}/${dialog.id}`:`life/${kind}`,{method:dialog.id?'PATCH':'POST',body:JSON.stringify(values)});await load();setDialog(null);setError('')}catch(e){setError(e.message)}finally{setSaving(false)}}
  async function remove(row){if(!window.confirm(`删除「${row.title}」？`))return;try{await call(`life/${kind}/${row.id}`,{method:'DELETE'});await load();setError('')}catch(e){setError(e.message)}}
  async function security(values){setSaving(true);try{const result=await call('diary/security',{method:'POST',body:JSON.stringify(values)});token.current=result.token;setEnabled(result.enabled);setDialog(null);setError('')}catch(e){setError(e.message)}finally{setSaving(false)}}
  const month=today().slice(0,7), recent=rows.filter(r=>r.date.startsWith(month))
  return <div className="life-page"><div className="page-heading"><div><p className="eyebrow">LIFE SPACE</p><h1>{c.title}</h1><p className="heading-sub">{c.subtitle}</p></div>{unlocked&&!loading&&<div className="life-actions">{kind==='diary'&&<><button className="secondary-btn" onClick={()=>{setError('');setDialog({security:true})}}><LockKeyhole size={16}/>密码设置</button>{enabled&&<button className="secondary-btn" onClick={lock}>锁定</button>}</>}<button className="primary-btn" onClick={()=>{setError('');setDialog({})}}><Plus size={17}/>新增记录</button></div>}</div>
    {error&&<div className="feature-error">{error}</div>}
    {loading?<div className="panel life-empty">正在读取记录…</div>:!unlocked?<section className="panel diary-gate"><div className="life-mark"><LockKeyhole size={26}/></div><h3>这一页，只留给你</h3><p>输入日记密码，打开你的手札。</p><form onSubmit={unlock}><input type="password" autoFocus autoComplete="current-password" placeholder="日记密码" value={password} onChange={e=>setPassword(e.target.value)}/><button className="primary-btn" disabled={saving||!password}>{saving?'正在打开…':'打开日记'}</button></form></section>:<>
      <div className="life-summary"><section className="panel"><span>全部记录</span><strong>{rows.length}<small>篇</small></strong></section><section className="panel"><span>本月记录</span><strong>{recent.length}<small>篇</small></strong></section><section className="panel"><span>{kind==='exercise'?'本月运动时长':kind==='coffee'?'平均评分':'打开方式'}</span><strong>{kind==='exercise'?recent.reduce((n,r)=>n+r.minutes,0):kind==='coffee'?(rows.length?(rows.reduce((n,r)=>n+r.rating,0)/rows.length).toFixed(1):'—'):enabled?'密码保护':'直接打开'}<small>{kind==='exercise'?'分钟':kind==='coffee'?' / 5':''}</small></strong></section></div>
      {rows.length?<div className="life-grid">{rows.map(row=><article className="panel life-card" key={row.id}><div className="life-card-head"><span className="life-mark"><Icon size={20}/></span><span>{row.date}</span><div><button className="feature-icon-btn" title="编辑记录" onClick={()=>{setError('');setDialog(row)}}><Edit3 size={16}/></button><button className="feature-icon-btn" title="删除记录" onClick={()=>remove(row)}><Trash2 size={16}/></button></div></div><h3>{row.title}</h3>{kind!=='diary'&&<div className="life-tag">{kind==='exercise'?`${row.minutes} 分钟`:'★'.repeat(row.rating)+'☆'.repeat(5-row.rating)}</div>}<p>{row.notes||'暂无补充记录'}</p></article>)}</div>:<section className="panel life-empty"><Icon size={32}/><h3>写下第一条记录</h3><p>从今天开始，收藏生活中的一点一滴。</p><button className="primary-btn" onClick={()=>setDialog({})}><Plus size={16}/>新增记录</button></section>}
    </>}
    {dialog&&<div className="modal-backdrop"><div className="modal life-modal" role="dialog" aria-modal="true"><div className="modal-header"><h2>{dialog.security?'日记密码设置':dialog.id?'编辑记录':'新增记录'}</h2><button className="feature-icon-btn" onClick={()=>setDialog(null)} aria-label="关闭"><X size={20}/></button></div>{dialog.security?<SecurityForm enabled={enabled} saving={saving} error={error} onSave={security} onClose={()=>setDialog(null)}/>:<EntryForm kind={kind} initial={dialog} saving={saving} error={error} onSave={save} onClose={()=>setDialog(null)}/>}</div></div>}
  </div>
}

function EntryForm({kind,initial,saving,error,onSave,onClose}) {
  const [values,setValues]=useState({date:today(),title:'',notes:'',minutes:30,rating:3,...initial})
  const change=(key,value)=>setValues(v=>({...v,[key]:value}))
  return <form onSubmit={e=>{e.preventDefault();onSave(values)}}><label>日期<input type="date" required value={values.date} onChange={e=>change('date',e.target.value)}/></label><label>{kind==='diary'?'标题':kind==='exercise'?'运动项目':'咖啡名称 / 店铺'}<input required maxLength={120} placeholder={config[kind].placeholder} value={values.title} onChange={e=>change('title',e.target.value)}/></label>{kind==='exercise'&&<label>时长（分钟）<input type="number" min="1" max="1440" required value={values.minutes} onChange={e=>change('minutes',e.target.value)}/></label>}{kind==='coffee'&&<label>评分<select value={values.rating} onChange={e=>change('rating',e.target.value)}>{[1,2,3,4,5].map(n=><option key={n} value={n}>{'★'.repeat(n)}</option>)}</select></label>}<label>{kind==='diary'?'正文':'随手记'}<textarea rows={kind==='diary'?10:4} maxLength={20000} value={values.notes} onChange={e=>change('notes',e.target.value)} placeholder={kind==='diary'?'写下今天的故事…':'感受、体验或其他想记录的细节…'}/></label>{error&&<p className="form-error">{error}</p>}<div className="modal-actions"><button type="button" className="secondary-btn" onClick={onClose}>取消</button><button className="primary-btn" disabled={saving}>{saving?'正在保存…':'保存记录'}</button></div></form>
}
function SecurityForm({enabled,saving,error,onSave,onClose}) {
  const [usePassword,setUsePassword]=useState(enabled),[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[message,setMessage]=useState('')
  return <form onSubmit={e=>{e.preventDefault();if(usePassword&&password!==confirm)return setMessage('两次密码不一致');setMessage('');onSave({enabled:usePassword,password})}}><label className="password-option"><input type="checkbox" checked={usePassword} onChange={e=>setUsePassword(e.target.checked)}/>使用密码打开日记</label><p className="life-security-note">关闭后可直接打开日记；启用后离开日记页面会自动锁定，打开30分钟后也需重新输入。此功能保护应用内访问，本地数据库未加密。</p>{usePassword&&<><label>{enabled?'设置新密码':'设置密码'}<input type="password" autoComplete="new-password" required minLength={6} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)}/></label><label>再次输入密码<input type="password" autoComplete="new-password" required value={confirm} onChange={e=>setConfirm(e.target.value)}/></label><p className="life-security-note">请记住密码，暂不支持找回。</p></>}{(message||error)&&<p className="form-error">{message||error}</p>}<div className="modal-actions"><button className="secondary-btn" type="button" onClick={onClose}>取消</button><button className="primary-btn" disabled={saving}>{saving?'正在保存…':'保存设置'}</button></div></form>
}
