import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity, ArrowDownUp, ArrowRight, Bell, CalendarDays, Check, CheckCheck,
  ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Clock3, Command,
  FolderKanban, LayoutDashboard, ListTodo, Menu, MoreHorizontal, Plus,
  Search, Settings2, Sparkles, Target, Timer, Trash2, UserRound, X, BookOpen, Dumbbell, Coffee,
} from 'lucide-react'
import './style.css'
import './task.css'
import './readability.css'
import { ProjectsPage, SchedulePage, FocusPage, SettingsPage, request } from './features'
import { LifePage } from './life'

const TOKEN = new URLSearchParams(window.location.search).get('token') || ''
const NAV = [
  { id: 'dashboard', label: '今日概览', icon: LayoutDashboard },
  { id: 'tasks', label: '我的任务', icon: ListTodo },
  { id: 'deadlines', label: 'DDL 时间轴', icon: CalendarDays },
  { id: 'schedule', label: '课程表', icon: Clock3 },
  { id: 'projects', label: '项目空间', icon: FolderKanban },
  { id: 'focus', label: '专注模式', icon: Timer },
  { id: 'analytics', label: '数据分析', icon: Activity },
]
const LIFE_NAV = [
  {id:'diary',label:'日记手札',icon:BookOpen},
  {id:'exercise',label:'运动记录',icon:Dumbbell},
  {id:'coffee',label:'咖啡时光',icon:Coffee},
]
const KIND = { general: '普通任务', homework: '课程作业', exam: '考试复习', project: '项目任务' }
const PRIORITY = { low: '低优先级', medium: '普通', high: '高优先级', urgent: '紧急' }
const WEEKDAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

function dateKey(value) {
  const d = value instanceof Date ? value : new Date(value)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function addDays(date, amount) {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  copy.setDate(copy.getDate() + amount)
  return copy
}
function dueLabel(value) {
  if (!value) return '未设置截止时间'
  const d = new Date(value)
  const today = dateKey(new Date())
  const tomorrow = dateKey(addDays(new Date(), 1))
  const prefix = dateKey(d) === today ? '今天' : dateKey(d) === tomorrow ? '明天' : `${d.getMonth() + 1}月${d.getDate()}日`
  return `${prefix} ${d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })}`
}
function timeGreeting(now) {
  const h = now.getHours()
  if (h < 6) return '夜深了，记得休息'
  if (h < 11) return '早上好，开启高效的一天'
  if (h < 14) return '中午好，保持你的节奏'
  if (h < 18) return '下午好，继续稳步向前'
  return '晚上好，收好今天的成果'
}
async function api(path, options = {}) {
  const response = await fetch(`/api/${path}`, {
    ...options,
    headers: { 'X-Task-Token': TOKEN, 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || '操作失败，请稍后重试')
  return data
}

function App() {
  const [page, setPage] = useState('dashboard')
  const [now, setNow] = useState(new Date())
  const [tasks, setTasks] = useState([])
  const [projects, setProjects] = useState([])
  const [nextClasses, setNextClasses] = useState([])
  const [focusData, setFocusData] = useState({current:null,history:[]})
  const [focusStats, setFocusStats] = useState({today_seconds:0,week_seconds:0,total_seconds:0,daily:{}})
  const [profile, setProfile] = useState({display_name:'Task Copilot 用户',avatar_data:''})
  const [profileOpen, setProfileOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState(null)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [mobileNav, setMobileNav] = useState(false)
  const [menuTask, setMenuTask] = useState(null)

  async function refresh() {
    try {
      const start=dateKey(new Date()), end=dateKey(addDays(new Date(), 8))
      const [items,projectRows,classes,focus,stats,settings]=await Promise.all([
        request('tasks'),request('projects'),request(`occurrences?start=${start}&end=${end}`),request('focus'),request('focus/stats'),request('settings')
      ])
      setTasks(items);setProjects(projectRows);setNextClasses(classes);setFocusData(focus);setFocusStats(stats);setProfile(settings);setError('')
    }
    catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }
  useEffect(() => {
    refresh()
    const clock = window.setInterval(() => setNow(new Date()), 1000)
    const data = window.setInterval(refresh, 30000)
    return () => { window.clearInterval(clock); window.clearInterval(data) }
  }, [])

  async function mutateTask(id, values) {
    try {
      await api(`tasks/${id}`, { method: 'PATCH', body: JSON.stringify(values) })
      await refresh()
      setMenuTask(null)
    } catch (e) { setError(e.message) }
  }
  async function saveTask(values) {
    try {
      if (form?.id) await api(`tasks/${form.id}`, { method: 'PATCH', body: JSON.stringify(values) })
      else await api('tasks', { method: 'POST', body: JSON.stringify(values) })
      setForm(null)
      await refresh()
    } catch (e) { setError(e.message) }
  }
  async function deleteTask(task) {
    if (!window.confirm(`确定删除「${task.title}」吗？`)) return
    try {
      await api(`tasks/${task.id}`, { method: 'DELETE' })
      setMenuTask(null)
      await refresh()
    } catch (e) { setError(e.message) }
  }
  const today = dateKey(now)
  const todayTasks = tasks.filter(t => t.due_at && dateKey(t.due_at) === today)
  const active = tasks.filter(t => t.status !== 'done')
  const completed = tasks.filter(t => t.status === 'done')
  const upcoming = active.filter(t => t.due_at).sort((a, b) => new Date(a.due_at) - new Date(b.due_at))
  const doneToday = completed.filter(t => t.completed_at && dateKey(t.completed_at) === today)
  const projectDeadlines = projects.filter(p=>p.status!=='completed'&&p.due_at)
  const nextDue = [...upcoming.map(t=>({...t,entity:'task'})),...projectDeadlines.map(p=>({...p,title:p.name,kind:'project',entity:'project'}))].filter(x=>new Date(x.due_at)>=now).sort((a,b)=>new Date(a.due_at)-new Date(b.due_at))[0]
  const nextClass = nextClasses.find(c=>new Date(`${c.date}T${c.start_time}:00`)>=now)
  const weekFocus=focusStats.week_seconds
  const filtered = tasks.filter(t => {
    if (filter === 'active' && t.status === 'done') return false
    if (filter === 'done' && t.status !== 'done') return false
    if (filter === 'today' && (!t.due_at || dateKey(t.due_at) !== today)) return false
    return `${t.title} ${t.description}`.toLowerCase().includes(search.toLowerCase())
  })
  const currentNav = [...NAV,...LIFE_NAV].find(n => n.id === page)
  const currentMonth = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })

  function navigate(id) { setPage(id); setMobileNav(false); setMenuTask(null) }
  function taskRow(task, compact = false) {
    const isDone = task.status === 'done'
    const overdue = !isDone && task.due_at && new Date(task.due_at) < now
    return <div className={`task-row ${compact ? 'compact' : ''}`} key={task.id}>
      <button className={`task-check ${isDone ? 'checked' : ''}`} title={isDone ? '标记未完成' : '完成任务'} onClick={() => mutateTask(task.id, { status: isDone ? 'todo' : 'done' })}>{isDone && <Check size={14} strokeWidth={3} />}</button>
      <div className="task-content" onClick={() => setForm(task)} role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && setForm(task)}>
        <div className={`task-title ${isDone ? 'done' : ''}`}>{task.title}</div>
        <div className="task-meta"><span>{KIND[task.kind]}</span><span className="meta-dot">·</span><span className={overdue ? 'overdue' : ''}>{dueLabel(task.due_at)}</span>{task.subtask_total>0&&<><span className="meta-dot">·</span><span>子任务 {task.subtask_done}/{task.subtask_total}</span></>}</div>
      </div>
      {!compact && <span className={`priority priority-${task.priority}`}>{PRIORITY[task.priority]}</span>}
      <div className="task-menu-wrap"><button className="icon-btn task-menu-btn" aria-label="更多任务操作" onClick={() => setMenuTask(menuTask === task.id ? null : task.id)}><MoreHorizontal size={18} /></button>
        {menuTask === task.id && <div className="task-menu"><button onClick={() => { setForm(task); setMenuTask(null) }}>编辑任务</button><button className="danger" onClick={() => deleteTask(task)}><Trash2 size={14} />删除任务</button></div>}
      </div>
    </div>
  }

  return <div className="shell" onClick={e => { if (!e.target.closest('.task-menu-wrap')) setMenuTask(null) }}>
    <aside className={`sidebar ${mobileNav ? 'mobile-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Command size={21} strokeWidth={2.5} /></div><div><strong>Task Copilot</strong></div></div>
      <button className={`nav-item home-nav ${page==='dashboard'?'selected':''}`} onClick={()=>navigate('dashboard')}><LayoutDashboard size={18}/><span>今日概览</span></button>
      <div className="side-label">工作空间</div>
      <nav>{NAV.filter(item=>item.id!=='dashboard').map(item => <button key={item.id} className={`nav-item ${page === item.id ? 'selected' : ''}`} onClick={() => navigate(item.id)}><item.icon size={18} strokeWidth={page === item.id ? 2.3 : 1.9} /><span>{item.label}</span>{item.id === 'tasks' && active.length > 0 && <b>{active.length}</b>}</button>)}</nav>
      <div className="side-label life-side-label">生活空间</div>
      <nav>{LIFE_NAV.map(item=><button key={item.id} className={`nav-item ${page===item.id?'selected':''}`} onClick={()=>navigate(item.id)}><item.icon size={18}/><span>{item.label}</span></button>)}</nav>
      <div className="sidebar-bottom"><button className="nav-item muted" onClick={() => navigate('settings')}><Settings2 size={18} />设置与帮助</button></div>
    </aside>
    {mobileNav && <button className="mobile-overlay" onClick={() => setMobileNav(false)} aria-label="关闭导航" />}
    <main className="main">
      <header className="topbar"><button className="icon-btn mobile-menu" onClick={() => setMobileNav(true)} aria-label="打开导航"><Menu size={21} /></button><div className="crumb">{page==='dashboard'?'主页':LIFE_NAV.some(n=>n.id===page)?'生活空间':page==='settings'?'偏好设置':'工作空间'} <ChevronRight size={15} /> <strong>{currentNav?.label || '设置与帮助'}</strong></div><div className="top-actions"><span className="date-chip"><CalendarDays size={16} />{currentMonth}</span><span className="live-dot" title="本地数据已连接" /><button className="profile-trigger" onClick={()=>setProfileOpen(true)} title="编辑个人资料">{profile.avatar_data?<img src={profile.avatar_data} alt="个人头像"/>:<span>{profile.display_name?.trim()?.slice(0,1)?.toUpperCase()||'TC'}</span>}<strong>{profile.display_name||'Task Copilot 用户'}</strong></button></div></header>
      <div className="content">
        {error && <div className="error-banner"><CircleHelp size={17} />{error}<button onClick={() => setError('')}><X size={16} /></button></div>}
        {page === 'dashboard' && <>
          <div className="page-heading"><div><p className="eyebrow">YOUR PERSONAL WORKSPACE</p><h1>{timeGreeting(now)} <span className="wave">✦</span></h1><p className="heading-sub">今天是 {now.getFullYear()} 年 {now.getMonth() + 1} 月 {now.getDate()} 日，{WEEKDAYS[now.getDay()]}。一起把重要的事，慢慢做好。</p></div><button className="primary-btn" onClick={() => setForm({})}><Plus size={18} /> 新建任务</button></div>
          <div className="hero"><div className="hero-content"><h2>每一个小小的完成，<br />都在带你去想去的地方。</h2><p>安排好今天，让计划成为轻松前行的起点。</p><button onClick={() => navigate('tasks')}>查看我的任务 <ArrowRight size={16} /></button></div><div className="hero-clock"><div className="clock-ring"><span>{now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })}</span><small>当前时间</small></div><div className="orbit orbit-one" /><div className="orbit orbit-two" /></div></div>
          <div className="stat-grid"><Stat icon={<ListTodo size={20} />} tint="blue" label="待完成任务" value={active.length} unit="项" foot="保持节奏，逐个完成" /><Stat icon={<CheckCheck size={20} />} tint="green" label="今日已完成" value={doneToday.length} unit="项" foot="每一步都值得记录" /><Stat icon={<CalendarDays size={20} />} tint="orange" label="今日截止" value={todayTasks.filter(t => t.status !== 'done').length} unit="项" foot="别错过重要时间" /><Stat icon={<Timer size={20} />} tint="purple" label="本周专注" value={Math.round(weekFocus/60)} unit="分钟" foot="累计有效专注时长" /></div>
          <div className="dashboard-grid"><section className="panel"><div className="panel-head"><div><h3>今天的任务</h3><p>从一件重要的小事开始</p></div><button className="text-link" onClick={() => navigate('tasks')}>查看全部 <ArrowRight size={15} /></button></div><div className="panel-body">{loading ? <Empty text="正在加载任务…" /> : todayTasks.length ? todayTasks.slice(0, 5).map(t => taskRow(t, true)) : <Empty icon={<ListTodo size={25} />} title="今天还没有截止任务" text="可以新建一项任务，给今天一个清晰的目标。" action="添加任务" onClick={() => setForm({})} />}</div></section>
          <div className="right-stack"><section className="panel"><div className="panel-head"><div><h3>最近截止</h3><p>重要事项，心中有数</p></div><span className="panel-symbol orange"><CalendarDays size={18} /></span></div><div className="due-card">{nextDue ? <><div className="due-date">{new Date(nextDue.due_at).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })}</div><strong>{nextDue.title}</strong><p>{nextDue.entity==='project'?'项目截止':KIND[nextDue.kind]} · {dueLabel(nextDue.due_at)}</p><button className="text-link" onClick={() => navigate('deadlines')}>查看时间轴 <ArrowRight size={15} /></button></> : <Empty title="暂无即将到来的 DDL" text="设置任务或项目截止时间后，会在这里显示。" />}</div></section><section className="panel mini-panel"><div className="mini-icon"><Clock3 size={20} /></div><div><h3>下一节课</h3><p>{nextClass?`${nextClass.name} · ${nextClass.date} ${nextClass.start_time} · ${nextClass.location||'地点待定'}`:'近期暂无课程'}</p></div><button className="mini-arrow" onClick={() => navigate('schedule')} aria-label="打开课程表"><ArrowRight size={18} /></button></section></div></div>
          <div className="bottom-note"><Sparkles size={16} /> 用清晰的计划，换一份从容。Task Copilot 陪你稳步推进每一天。</div>
        </>}
        {page === 'tasks' && <><PageHead kicker="TASK MANAGEMENT" title="我的任务" subtitle="把想做的事放在这里，一件一件完成。" action={() => setForm({})} actionLabel="新建任务" /><div className="task-overview"><div><span>全部任务</span><strong>{tasks.length}</strong></div><div><span>进行中</span><strong>{active.length}</strong></div><div><span>已完成</span><strong>{completed.length}</strong></div><div><span>完成率</span><strong>{tasks.length ? Math.round(completed.length / tasks.length * 100) : 0}%</strong></div></div><section className="panel task-panel"><div className="task-toolbar"><div className="filter-tabs">{[['all','全部'],['active','待完成'],['today','今天截止'],['done','已完成']].map(([id,label]) => <button key={id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}</div><div className="search-box"><Search size={17} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索任务" /></div></div><div className="task-list">{loading ? <Empty text="正在加载任务…" /> : filtered.length ? filtered.map(t => taskRow(t)) : <Empty icon={<ListTodo size={25} />} title={tasks.length ? '没有符合条件的任务' : '先创建第一项任务'} text={tasks.length ? '试试其他筛选条件，或搜索任务名称。' : '把需要完成的事情记下来，接下来就更清楚了。'} action={!tasks.length ? '新建任务' : null} onClick={() => setForm({})} />}</div></section></>}
        {page === 'deadlines' && <Deadlines tasks={tasks} projects={projects} now={now} onTask={setForm} onProject={()=>navigate('projects')} />}
        {page === 'analytics' && <Analytics tasks={tasks} projects={projects} focusStats={focusStats} now={now} />}
        {page === 'schedule' && <SchedulePage onChanged={refresh} />}
        {page === 'projects' && <ProjectsPage tasks={tasks} onNewTask={setForm} onChanged={refresh} />}
        {page === 'focus' && <FocusPage tasks={tasks} projects={projects} onChanged={refresh} />}
        {page === 'settings' && <SettingsPage />}
        {LIFE_NAV.some(n=>n.id===page)&&<LifePage key={page} kind={page}/>} 
      </div>
    </main>
    {form && <TaskModal initial={form} projects={projects} onChanged={refresh} onClose={() => setForm(null)} onSave={saveTask} />}
    {profileOpen && <ProfileModal initial={profile} onClose={()=>setProfileOpen(false)} onSave={async values=>{try{const saved=await request('settings',{method:'PATCH',body:JSON.stringify(values)});setProfile(saved);setProfileOpen(false)}catch(e){setError(e.message)}}}/>} 
  </div>
}

function Stat({ icon, tint, label, value, unit, foot }) { return <div className="stat-card"><div className={`stat-icon ${tint}`}>{icon}</div><span className="stat-label">{label}</span><div className="stat-value">{value}<small>{unit}</small></div><p>{foot}</p></div> }
function Empty({ icon, title, text, action, onClick }) { return <div className="empty-state"><div className="empty-icon">{icon || <Sparkles size={23} />}</div>{title && <strong>{title}</strong>}<p>{text}</p>{action && <button onClick={onClick}>{action} <ArrowRight size={15} /></button>}</div> }
function PageHead({ kicker, title, subtitle, action, actionLabel }) { return <div className="page-heading"><div><p className="eyebrow">{kicker}</p><h1>{title}</h1><p className="heading-sub">{subtitle}</p></div>{action && <button className="primary-btn" onClick={action}><Plus size={18} />{actionLabel}</button>}</div> }

function ProfileModal({initial,onClose,onSave}) {
  const [name,setName]=useState(initial.display_name||''),[avatar,setAvatar]=useState(initial.avatar_data||''),[message,setMessage]=useState('')
  async function chooseAvatar(event) {
    const file=event.target.files?.[0]
    if(!file)return
    if(!file.type.startsWith('image/'))return setMessage('请选择图片文件')
    try{
      const bitmap=await createImageBitmap(file),size=Math.min(256,Math.max(bitmap.width,bitmap.height)),scale=Math.min(1,size/Math.max(bitmap.width,bitmap.height))
      const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale))
      canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();setAvatar(canvas.toDataURL('image/jpeg',.86));setMessage('')
    }catch{setMessage('无法读取这张图片')}
  }
  return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><div className="modal profile-modal"><div className="modal-header"><div><span className="eyebrow">PERSONAL PROFILE</span><h2>个人资料</h2></div><button className="icon-btn" onClick={onClose}><X size={21}/></button></div><form onSubmit={e=>{e.preventDefault();if(!name.trim())return setMessage('请填写昵称');onSave({display_name:name.trim(),avatar_data:avatar})}}><div className="avatar-editor"><div className="avatar-preview">{avatar?<img src={avatar} alt="头像预览"/>:<UserRound size={32}/>}</div><div><label className="avatar-upload">选择头像<input type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseAvatar}/></label>{avatar&&<button type="button" className="avatar-remove" onClick={()=>setAvatar('')}>恢复默认头像</button>}<p>图片会缩小后保存在本机。</p></div></div><label>昵称<input maxLength="30" value={name} onChange={e=>setName(e.target.value)} placeholder="你的昵称"/></label>{message&&<p className="form-error">{message}</p>}<div className="modal-actions"><button type="button" className="secondary-btn" onClick={onClose}>取消</button><button className="primary-btn" type="submit">保存资料</button></div></form></div></div>
}

function Deadlines({ tasks, projects, now, onTask, onProject }) {
  const [range, setRange] = useState(7)
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const end = addDays(today, range)
  const events=[...tasks.filter(t=>t.status!=='done').map(t=>({...t,entity:'task'})),...projects.filter(p=>p.status!=='completed').map(p=>({...p,title:p.name,kind:'project',priority:'high',entity:'project'}))]
  const relevant = events.filter(t => t.due_at && new Date(t.due_at) < end).sort((a,b) => new Date(a.due_at) - new Date(b.due_at))
  const overdue = relevant.filter(t => new Date(t.due_at) < today)
  const future = relevant.filter(t => new Date(t.due_at) >= today)
  const groups = future.reduce((result, item) => {
    const key = dateKey(item.due_at)
    ;(result[key] ||= []).push(item)
    return result
  }, {})
  const open=t=>t.entity==='project'?onProject():onTask(t)
  return <><PageHead kicker="DEADLINE TIMELINE" title="DDL 时间轴" subtitle="重要的截止时间，清清楚楚排在眼前。" /><div className="range-bar"><div className="range-tabs"><button className={range===7?'active':''} onClick={() => setRange(7)}>未来 7 天</button><button className={range===30?'active':''} onClick={() => setRange(30)}>未来 30 天</button></div><span>{future.length} 项即将到期</span></div><div className="timeline-layout"><section className="panel timeline-panel">{overdue.length > 0 && <div className="timeline-group"><div className="timeline-date overdue-date"><span className="timeline-dot" /><strong>已经逾期</strong><small>{overdue.length} 项</small></div>{overdue.map(t => <TimelineTask key={`${t.entity}-${t.id}`} task={t} onClick={() => open(t)} />)}</div>}{Object.entries(groups).map(([key, items]) => <div className="timeline-group" key={key}><div className="timeline-date"><span className="timeline-dot" /><strong>{new Date(`${key}T12:00:00`).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}</strong><small>{items.length} 项</small></div>{items.map(t => <TimelineTask key={`${t.entity}-${t.id}`} task={t} onClick={() => open(t)} />)}</div>)}{!relevant.length && <Empty icon={<CalendarDays size={25} />} title="这段时间没有截止事项" text="给任务或项目设置截止时间后，会自动出现在时间轴上。" />}</section><aside className="panel timeline-aside"><div className="panel-head"><div><h3>合理安排，轻松完成</h3><p>给未来留出一点余量</p></div><Sparkles size={18} /></div><p>为重要任务设置明确的截止时间。你可以在任务页随时调整时间和优先级。</p><div className="aside-stat"><span>未来 {range} 天</span><strong>{future.length} <small>项事项</small></strong></div></aside></div></>
}
function TimelineTask({ task, onClick }) { return <button className="timeline-task" onClick={onClick}><div className={`timeline-task-icon priority-${task.priority}`}><Target size={17} /></div><div><strong>{task.title}</strong><p>{task.entity==='project'?'项目截止':KIND[task.kind]} · {PRIORITY[task.priority]}</p></div><span>{new Date(task.due_at).toLocaleTimeString('zh-CN', { hour:'2-digit', minute:'2-digit', hour12:false })}</span><ChevronRight size={17} /></button> }

function Analytics({ tasks, projects, focusStats, now }) {
  const done = tasks.filter(t => t.status === 'done')
  const rate = tasks.length ? Math.round(done.length / tasks.length * 100) : 0
  const week = Array.from({length: 7}, (_, i) => {
    const base = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    base.setDate(base.getDate() - 6 + i)
    return { date: base, count: done.filter(t => t.completed_at && dateKey(t.completed_at) === dateKey(base)).length }
  })
  const max = Math.max(1, ...week.map(d => d.count))
  const kinds = Object.entries(KIND).map(([key,label]) => ({ key,label,total:tasks.filter(t=>t.kind===key).length,done:done.filter(t=>t.kind===key).length }))
  const totalFocus=focusStats.total_seconds
  return <><PageHead kicker="YOUR PROGRESS" title="数据分析" subtitle="回看每一点积累，看见自己的稳步前进。" /><div className="stat-grid analytics-stats"><Stat icon={<ListTodo size={20}/>} tint="blue" label="全部任务" value={tasks.length} unit="项" foot="已记录的任务"/><Stat icon={<CheckCheck size={20}/>} tint="green" label="完成任务" value={done.length} unit="项" foot="已完成的目标"/><Stat icon={<Target size={20}/>} tint="purple" label="完成率" value={rate} unit="%" foot="基于当前全部任务"/><Stat icon={<Timer size={20}/>} tint="orange" label="累计专注" value={Math.round(totalFocus/60)} unit="分钟" foot="有效专注时长"/></div><div className="dashboard-grid"><section className="panel chart-panel"><div className="panel-head"><div><h3>近 7 天完成趋势</h3><p>按任务实际完成日期统计</p></div><Activity size={18}/></div><div className="chart">{week.map((d,i) => <div className="chart-col" key={i}><span className="bar-value">{d.count||''}</span><div className="bar-track"><div className={`bar ${i===6?'today-bar':''}`} style={{height:`${Math.max(d.count?12:3, d.count/max*100)}%`}}/></div><small>{d.date.toLocaleDateString('zh-CN',{weekday:'short'})}</small></div>)}</div></section><section className="panel categories-panel"><div className="panel-head"><div><h3>任务类型</h3><p>不同方向，都在稳步推进</p></div><ArrowDownUp size={18}/></div><div className="category-list">{kinds.map(k=><div className="category-row" key={k.key}><div><strong>{k.label}</strong><span>{k.done} / {k.total} 完成</span></div><div className="progress"><span style={{width:`${k.total?k.done/k.total*100:0}%`}}/></div></div>)}</div></section></div><section className="panel analytics-projects"><div className="panel-head"><div><h3>项目进度</h3><p>关联任务与子任务的当前进展</p></div><FolderKanban size={18}/></div><div className="category-list">{projects.length?projects.map(p=>{const own=tasks.filter(t=>t.project_id===p.id),progress=own.length?Math.round(own.reduce((n,t)=>n+(t.status==='done'?1:t.subtask_total?t.subtask_done/t.subtask_total:0),0)/own.length*100):0;return <div className="category-row" key={p.id}><div><strong>{p.name}</strong><span>{progress}% · {own.length} 项任务</span></div><div className="progress"><span style={{width:`${progress}%`}}/></div></div>}):<Empty title="暂无项目" text="建立项目并关联任务后，这里会显示进度。"/>}</div></section></>
}

function FuturePage({ page, navigate }) {
  const config = {
    schedule: { icon: CalendarDays, title: '课程表', subtitle: '让每一节课都有清晰的位置。', heading: '课表功能正在准备中', body: '之后可以按周查看课程，记录教师、地点、单双周与临时调课。' },
    projects: { icon: FolderKanban, title: '项目空间', subtitle: '把长期目标拆成能够推进的小步骤。', heading: '项目工作区即将加入', body: '之后可以建立项目、关联任务，并查看整体进度。' },
    focus: { icon: Timer, title: '专注模式', subtitle: '留一段完整的时间给重要的事。', heading: '番茄钟即将加入', body: '之后可以开始专注、记录时长，并回看自己的投入。' },
    settings: { icon: Settings2, title: '设置与帮助', subtitle: '把你的学习空间调整得更顺手。', heading: '设置功能正在准备中', body: '后续将在这里管理提醒时间、外观及数据备份。' },
  }[page]
  const Icon = config.icon
  return <><PageHead kicker="COMING NEXT" title={config.title} subtitle={config.subtitle} /><div className="future-card"><div className="future-decoration"/><div className="future-icon"><Icon size={31}/></div><span className="future-badge">即将推出</span><h2>{config.heading}</h2><p>{config.body}</p><button onClick={() => navigate('dashboard')}>返回今日概览 <ArrowRight size={16}/></button></div></>
}

function TaskModal({ initial, projects, onChanged, onClose, onSave }) {
  const [title, setTitle] = useState(initial.title || '')
  const [description, setDescription] = useState(initial.description || '')
  const [kind, setKind] = useState(initial.kind || 'general')
  const [priority, setPriority] = useState(initial.priority || 'medium')
  const [due, setDue] = useState(initial.due_at ? new Date(initial.due_at).toLocaleString('sv-SE').replace(' ', 'T').slice(0, 16) : '')
  const [projectId, setProjectId] = useState(initial.project_id || '')
  const [subtasks, setSubtasks] = useState([])
  const [subtaskTitle, setSubtaskTitle] = useState('')
  const [message, setMessage] = useState('')
  useEffect(() => { if (initial.id) request(`tasks/${initial.id}/subtasks`).then(setSubtasks).catch(e => setMessage(e.message)) }, [initial.id])
  async function addSubtask() {
    if (!subtaskTitle.trim() || !initial.id) return
    try { await request(`tasks/${initial.id}/subtasks`, { method: 'POST', body: JSON.stringify({title:subtaskTitle.trim()}) }); setSubtaskTitle(''); setSubtasks(await request(`tasks/${initial.id}/subtasks`)); onChanged() }
    catch(e) { setMessage(e.message) }
  }
  async function toggleSubtask(item) {
    try { await request(`tasks/${initial.id}/subtasks/${item.id}`, { method: 'PATCH', body: JSON.stringify({done:!item.done}) }); setSubtasks(await request(`tasks/${initial.id}/subtasks`)); onChanged() }
    catch(e) { setMessage(e.message) }
  }
  async function removeSubtask(item) {
    if (!window.confirm(`删除子任务「${item.title}」？`)) return
    try { await request(`tasks/${initial.id}/subtasks/${item.id}`, { method: 'DELETE' }); setSubtasks(await request(`tasks/${initial.id}/subtasks`)); onChanged() }
    catch(e) { setMessage(e.message) }
  }
  function submit(e) {
    e.preventDefault()
    if (!title.trim()) return setMessage('请填写任务名称')
    if (title.trim().length > 120) return setMessage('任务名称不能超过 120 个字符')
    if (description.length > 1000) return setMessage('描述不能超过 1000 个字符')
    onSave({ title: title.trim(), description: description.trim(), kind, priority, due_at: due ? new Date(due).toISOString() : null, project_id: projectId || null })
  }
  return <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}><div className="modal task-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-header"><div><span className="eyebrow">TASK DETAILS</span><h2 id="modal-title">{initial.id ? '编辑任务' : '新建任务'}</h2></div><button className="icon-btn" onClick={onClose} aria-label="关闭"><X size={21}/></button></div><form onSubmit={submit}><label>任务名称 <span>*</span><input autoFocus maxLength="120" placeholder="例如：完成高数作业第三章" value={title} onChange={e=>setTitle(e.target.value)}/></label><label>任务描述 <textarea rows="3" maxLength="1000" placeholder="补充一些细节，方便之后继续完成…" value={description} onChange={e=>setDescription(e.target.value)}/></label><div className="form-grid"><label>任务类型<select value={kind} onChange={e=>setKind(e.target.value)}>{Object.entries(KIND).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label><label>优先级<select value={priority} onChange={e=>setPriority(e.target.value)}>{Object.entries(PRIORITY).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label></div><div className="form-grid"><label>截止时间 <span className="optional">选填</span><input type="datetime-local" value={due} onChange={e=>setDue(e.target.value)}/></label><label>所属项目 <span className="optional">选填</span><select value={projectId} onChange={e=>setProjectId(e.target.value)}><option value="">不关联项目</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label></div>{initial.id&&<div className="subtasks-editor"><div className="subtasks-head"><strong>子任务</strong><span>{subtasks.filter(s=>s.done).length} / {subtasks.length} 完成</span></div>{subtasks.map(s=><div className="subtask-line" key={s.id}><button type="button" className={`task-check ${s.done?'checked':''}`} onClick={()=>toggleSubtask(s)}>{s.done&&<Check size={13}/>}</button><span className={s.done?'done':''}>{s.title}</span><button type="button" className="icon-btn" onClick={()=>removeSubtask(s)} aria-label="删除子任务"><X size={14}/></button></div>)}<div className="subtask-add"><input value={subtaskTitle} onChange={e=>setSubtaskTitle(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();addSubtask()}}} placeholder="添加一个小步骤"/><button type="button" onClick={addSubtask}><Plus size={16}/></button></div></div>}{message && <p className="form-error">{message}</p>}<div className="modal-actions"><button type="button" className="secondary-btn" onClick={onClose}>取消</button><button className="primary-btn" type="submit">{initial.id ? '保存修改' : '创建任务'}</button></div></form></div></div>
}

createRoot(document.getElementById('root')).render(<App />)
