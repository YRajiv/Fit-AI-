import { createContext, useContext, useEffect, useRef, useState } from 'react'
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  Camera,
  Check,
  ChevronRight,
  Dumbbell,
  Droplets,
  Flame,
  HeartPulse,
  Leaf,
  LogOut,
  MessageCircle,
  Salad,
  ShieldCheck,
  Sparkles,
  Timer,
  UserRound,
  UserPlus,
  Footprints,
  Scale,
  Send,
  RotateCcw,
  Utensils,
  X,
} from 'lucide-react'
import {
  API_BASE_URL,
  api,
  getErrorMessage,
  initializeCsrf,
  streamChat,
  updateCsrfToken,
} from './api'

const AuthContext = createContext(null)

function useAuth() {
  return useContext(AuthContext)
}

function App() {
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [connectionError, setConnectionError] = useState('')

  useEffect(() => {
    initializeCsrf()
      .then(() => api.get('/users/api/session/'))
      .then(({ data }) => setUser(data.user))
      .catch((error) => {
        if (error.response?.status !== 401) {
          setConnectionError(getErrorMessage(error))
        }
      })
      .finally(() => setAuthLoading(false))
  }, [])

  const value = {
    user,
    setUser,
    authLoading,
    connectionError,
    setConnectionError,
  }

  return (
    <AuthContext.Provider value={value}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/nutrition" element={<NutritionPage />} />
              <Route path="/workout" element={<WorkoutPage />} />
              <Route path="/assistant" element={<AssistantPage />} />
              <Route path="/diet" element={<DietPage />} />
              <Route path="/progress" element={<ProgressPage />} />
              <Route path="/reminders" element={<RemindersPage />} />
              <Route path="/posture" element={<PosturePage />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}

function RequireAuth() {
  const { user, authLoading, connectionError } = useAuth()
  const location = useLocation()

  if (authLoading) return <LoadingPage />
  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location, connectionError }}
      />
    )
  }
  return <Outlet />
}

function LandingPage() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Link className="brand" to="/">
          <span className="brand-mark"><Activity size={19} /></span>
          <span>Fit<span className="brand-accent">AI</span></span>
        </Link>
        <nav className="landing-actions">
          <Link className="text-link" to="/login">Sign in</Link>
          <Link className="button button-primary button-small" to="/register">
            Get started <ArrowRight size={16} />
          </Link>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><Sparkles size={14} /> YOUR PERSONAL FITNESS SPACE</div>
          <h1>Build a stronger you, <span>one day at a time.</span></h1>
          <p>
            Bring your workouts, nutrition, progress and AI fitness assistant
            together in one calm, focused dashboard.
          </p>
          <div className="hero-actions">
            <Link className="button button-primary" to="/register">
              Create your account <ArrowRight size={17} />
            </Link>
            <Link className="button button-quiet" to="/login">I already have an account</Link>
          </div>
          <div className="hero-proof">
            <ShieldCheck size={16} /> Private, session-based access to your FitAI account
          </div>
        </div>
        <div className="hero-visual">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="hero-core"><Activity size={46} /></div>
          <div className="float-card float-card-top"><Dumbbell size={17} /><span>Move with purpose</span></div>
          <div className="float-card float-card-bottom"><HeartPulse size={17} /><span>Progress at your pace</span></div>
          <div className="hero-glow" />
        </div>
      </section>

      <section className="landing-features">
        <Feature icon={Dumbbell} title="Training" text="Personalized workouts with a completion flow." />
        <Feature icon={Salad} title="Nutrition" text="Scan meals and review AI-estimated nutrition." />
        <Feature icon={BarChart3} title="Progress" text="Track daily steps, goals and weight changes." />
        <Feature icon={MessageCircle} title="AI assistant" text="Ask questions with FitAI's streaming assistant." />
      </section>
      <footer className="landing-footer">FITAI · A thoughtful companion for your fitness journey</footer>
    </main>
  )
}

function Feature({ icon: Icon, title, text }) {
  return (
    <article className="feature-card">
      <span className="feature-icon"><Icon size={19} /></span>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  )
}

function AuthPage({ mode }) {
  const isRegister = mode === 'register'
  const navigate = useNavigate()
  const location = useLocation()
  const { user, setUser, connectionError } = useAuth()
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
  })
  const [error, setError] = useState(location.state?.connectionError || '')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/dashboard" replace />

  const update = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await initializeCsrf()
      const { data } = await api.post(
        isRegister ? '/users/api/register/' : '/users/api/login/',
        isRegister
          ? {
              username: form.username,
              email: form.email,
              password1: form.password,
              password2: form.password2,
            }
          : { username: form.username, password: form.password },
      )
      updateCsrfToken(data.csrfToken)
      setUser(data.user)
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-page">
      <Link className="brand auth-brand" to="/">
        <span className="brand-mark"><Activity size={19} /></span>
        <span>Fit<span className="brand-accent">AI</span></span>
      </Link>
      <section className="auth-card glass-card">
        <div className="auth-icon">{isRegister ? <UserPlus size={21} /> : <UserRound size={21} />}</div>
        <p className="eyebrow">WELCOME {isRegister ? 'TO FITAI' : 'BACK'}</p>
        <h1>{isRegister ? 'Create your account' : 'Sign in to FitAI'}</h1>
        <p className="muted">{isRegister ? 'Start building a routine that feels like yours.' : 'Your fitness space is ready when you are.'}</p>
        {error && <Notice tone="error">{error}</Notice>}
        {!error && connectionError && <Notice tone="warning">{connectionError}</Notice>}
        <form className="form-stack" onSubmit={submit}>
          <label>
            Username
            <input autoComplete="username" name="username" value={form.username} onChange={update} required />
          </label>
          {isRegister && (
            <label>
              Email
              <input autoComplete="email" name="email" type="email" value={form.email} onChange={update} required />
            </label>
          )}
          <label>
            Password
            <input autoComplete={isRegister ? 'new-password' : 'current-password'} name="password" type="password" value={form.password} onChange={update} required />
          </label>
          {isRegister && (
            <label>
              Confirm password
              <input autoComplete="new-password" name="password2" type="password" value={form.password2} onChange={update} required />
            </label>
          )}
          <button className="button button-primary button-full" disabled={busy}>
            {busy ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}
            {!busy && <ArrowRight size={16} />}
          </button>
        </form>
        <p className="auth-switch">
          {isRegister ? 'Already have an account?' : 'New to FitAI?'}{' '}
          <Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Sign in' : 'Create an account'}</Link>
        </p>
        <Link className="back-home" to="/">Back to home</Link>
      </section>
    </main>
  )
}

const navigation = [
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { to: '/nutrition', label: 'Nutrition', icon: Utensils },
  { to: '/workout', label: 'Workout', icon: Dumbbell },
  { to: '/assistant', label: 'AI Assistant', icon: MessageCircle },
  { to: '/diet', label: 'Diet plan', icon: Leaf },
  { to: '/progress', label: 'Progress', icon: Activity },
  { to: '/reminders', label: 'Reminders', icon: Bell },
  { to: '/posture', label: 'Posture check', icon: Camera },
]

function AppLayout() {
  const { user, setUser } = useAuth()
  const [logoutError, setLogoutError] = useState('')

  const signOut = async () => {
    setLogoutError('')
    try {
      const { data } = await api.post('/users/api/logout/')
      updateCsrfToken(data.csrfToken)
      setUser(null)
    } catch (error) {
      setLogoutError(getErrorMessage(error))
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand sidebar-brand" to="/dashboard">
          <span className="brand-mark"><Activity size={19} /></span>
          <span>Fit<span className="brand-accent">AI</span></span>
        </Link>
        <p className="nav-caption">WORKSPACE</p>
        <nav className="side-nav">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
              {to === '/dashboard' && <ChevronRight className="nav-chevron" size={15} />}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="user-chip">
            <div className="avatar">{user?.username?.slice(0, 1).toUpperCase() || 'F'}</div>
            <div className="user-meta"><strong>{user?.username}</strong><small>FitAI member</small></div>
          </div>
          {logoutError && <p className="inline-error">{logoutError}</p>}
          <button className="nav-item signout" onClick={signOut}><LogOut size={17} /><span>Sign out</span></button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="topbar-brand"><span className="brand-mark"><Activity size={18} /></span> Fit<span className="brand-accent">AI</span></div>
          <div className="topbar-note"><span className="status-dot" /> Your personal fitness space</div>
          <span className="topbar-user">{user?.username}</span>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  )
}

function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {action}
    </div>
  )
}

function DashboardPage() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/dashboard/api/summary/')
      .then(({ data }) => setSummary(data))
      .catch((requestError) => setError(getErrorMessage(requestError)))
  }, [])

  const dayName = summary?.day_name || 'TODAY'

  return (
    <>
      <PageHeading eyebrow="YOUR OVERVIEW" title={`Good to see you, ${user?.username}.`} description="A clear view of your routine, with room to make it your own." />
      {error && <Notice tone="warning">{error} Your other pages remain available.</Notice>}
      <section className="metric-grid">
        <Metric icon={Footprints} label="Steps today" value={summary?.steps ?? '—'} unit="steps" />
        <Metric icon={Flame} label="Calories consumed" value={summary?.consumed_calories ?? '—'} unit="kcal" />
        <Metric icon={Dumbbell} label="Protein consumed" value={summary?.consumed_protein ?? '—'} unit="g" />
        <Metric icon={Droplets} label="Water intake" value={summary ? `${summary.water_amount} / ${summary.water_target}` : '—'} unit="L" />
        <Metric icon={ArrowUpRight} label="Daily goal" value={summary?.steps_goal?.toLocaleString() ?? '—'} unit="steps" />
        <Metric icon={Timer} label="Active time" value={summary?.active_minutes ?? '—'} unit="min" />
      </section>

      <section className="glass-card panel" style={{ marginTop: '16px' }}>
        <div className="section-title">
          <h2>Today's Diet Meals</h2>
          <span><Utensils size={14} /> {dayName.toUpperCase()}</span>
        </div>
        {summary?.today_diet_meals?.length ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '12px', marginTop: '14px' }}>
            {summary.today_diet_meals.map((meal, index) => (
              <div key={index} className="glass-card" style={{ padding: '14px', borderRadius: '13px', background: 'rgba(255,255,255,0.02)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span className="eyebrow" style={{ margin: 0 }}>{meal.meal || `Meal ${index + 1}`}</span>
                  <small className="muted">{meal.calories ? `${meal.calories} kcal` : ''}</small>
                </div>
                <strong style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>{meal.food}</strong>
                <div style={{ display: 'flex', gap: '10px', fontSize: '11px', color: 'var(--muted)' }}>
                  {meal.protein ? <span>Protein: <b style={{ color: '#e5e1ed' }}>{meal.protein}g</b></span> : null}
                  {meal.cost ? <span>₹{meal.cost}</span> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ marginTop: '14px', padding: '12px 0', color: 'var(--muted)', fontSize: '12px' }}>
            No diet meals planned for today yet.{' '}
            <Link to="/diet" style={{ color: 'var(--purple)', fontWeight: 600 }}>
              View or generate your weekly diet plan →
            </Link>
          </div>
        )}
      </section>

      <section className="dashboard-lower">
        <div className="glass-card welcome-card">
          <div className="card-overline"><Sparkles size={15} /> YOUR NEXT STEP</div>
          <h2>Small steps add up.</h2>
          <p>Choose one focus for today. Your progress page can update your steps, goal and weight whenever you need.</p>
          <Link to="/progress" className="button button-primary">Update progress <ArrowRight size={16} /></Link>
        </div>
        <div className="glass-card quick-card">
          <div className="section-title"><h2>Explore FitAI</h2><span>YOUR TOOLS</span></div>
          <div className="quick-links">
            <QuickLink to="/workout" icon={Dumbbell} title="Start a workout" text="Your personalized routine" />
            <QuickLink to="/nutrition" icon={Utensils} title="Scan a meal" text="AI nutrition estimate" />
            <QuickLink to="/assistant" icon={MessageCircle} title="Ask FitAI" text="Chat with your assistant" />
          </div>
        </div>
      </section>
      <p className="api-footnote">Dashboard metrics are aggregated from your daily progress, food scans, water records, and weekly diet plan.</p>
    </>
  )
}

function Metric({ icon: Icon, label, value, unit }) {
  return (
    <article className="metric-card glass-card">
      <span className="metric-icon"><Icon size={18} /></span>
      <p>{label}</p>
      <div className="metric-value">{typeof value === 'number' ? value.toLocaleString() : value}<small>{unit}</small></div>
    </article>
  )
}

function QuickLink({ to, icon: Icon, title, text }) {
  return (
    <Link to={to} className="quick-link">
      <span className="quick-icon"><Icon size={18} /></span>
      <span><strong>{title}</strong><small>{text}</small></span>
      <ArrowRight size={16} />
    </Link>
  )
}

function NutritionPage() {
  const [image, setImage] = useState('')
  const [preview, setPreview] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const chooseImage = (event) => {
    setError('')
    setResult(null)
    const file = event.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Choose an image file to scan.')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const value = typeof reader.result === 'string' ? reader.result : ''
      setImage(value)
      setPreview(value)
    }
    reader.onerror = () => setError('The selected image could not be read.')
    reader.readAsDataURL(file)
  }

  const scan = async (event) => {
    event.preventDefault()
    if (!image) {
      setError('Choose a meal photo first.')
      return
    }
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const { data } = await api.post('/nutrition/scan/', { image })
      setResult(data.nutrition || data)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeading eyebrow="NOURISH WELL" title="Nutrition" description="Scan a meal to get an AI-estimated nutrition breakdown." />
      <div className="two-column">
        <section className="glass-card panel">
          <div className="section-title"><h2>Meal scanner</h2><span><Camera size={14} /> GEMINI VISION</span></div>
          <p className="muted">Choose a clear photo of your meal. The existing Django API analyzes and saves the scan to your account.</p>
          <form onSubmit={scan} className="form-stack scan-form">
            <label className="upload-box">
              {preview ? <img className="food-preview" src={preview} alt="Selected meal preview" /> : <><span className="upload-icon"><Camera size={22} /></span><strong>Choose a meal photo</strong><small>PNG, JPG or another image format</small></>}
              <input type="file" accept="image/*" onChange={chooseImage} />
            </label>
            {error && <Notice tone="error">{error}</Notice>}
            <button className="button button-primary button-full" disabled={busy || !image}>
              {busy ? 'Analyzing your meal…' : 'Analyze meal'} {!busy && <Sparkles size={16} />}
            </button>
          </form>
          <p className="api-footnote">Nutrition values are estimates, not medical advice.</p>
        </section>
        <section className="glass-card panel result-panel">
          <div className="section-title"><h2>Scan result</h2><span>YOUR MEAL</span></div>
          {result ? (
            <>
              <div className="food-title"><span className="food-icon"><Salad size={20} /></span><div><h3>{result.food_name || 'Scanned meal'}</h3><small>Estimated per serving</small></div></div>
              <div className="nutrition-grid">
                <NutritionValue label="Calories" value={result.calories} unit="kcal" />
                <NutritionValue label="Protein" value={result.protein} unit="g" />
                <NutritionValue label="Carbs" value={result.carbs} unit="g" />
                <NutritionValue label="Fat" value={result.fat} unit="g" />
                <NutritionValue label="Fiber" value={result.fiber} unit="g" />
                <NutritionValue label="Sugar" value={result.sugar} unit="g" />
              </div>
              {result.ai_tip && <div className="tip-box"><Sparkles size={15} />{result.ai_tip}</div>}
            </>
          ) : <EmptyState icon={Salad} title="Your scan will appear here" text="Upload a meal photo to see estimated calories and macros." />}
        </section>
      </div>
    </>
  )
}

function NutritionValue({ label, value, unit }) {
  return <div className="nutrition-value"><small>{label}</small><strong>{value ?? '—'}<span>{unit}</span></strong></div>
}

function WorkoutPage() {
  const [plan, setPlan] = useState(null)
  const [workoutId, setWorkoutId] = useState(null)
  const [completed, setCompleted] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const loadPlan = async () => {
    setError('')
    try {
      const { data } = await api.get('/workouts/api/recommendation/')
      setPlan(data)
    } catch (requestError) {
      setPlan(null)
      setError(getErrorMessage(requestError))
    }
  }

  useEffect(() => {
    let active = true
    api.get('/workouts/api/recommendation/')
      .then(({ data }) => {
        if (active) setPlan(data)
      })
      .catch((requestError) => {
        if (active) {
          setPlan(null)
          setError(getErrorMessage(requestError))
        }
      })
    return () => { active = false }
  }, [])

  const startWorkout = async () => {
    if (!plan?.name || busy) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const body = new URLSearchParams({ workout_name: plan.name })
      const { data } = await api.post('/workouts/start/', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      if (data.status !== 'success' || !data.workout_id) {
        throw new Error(data.message || 'The workout could not be started.')
      }
      setWorkoutId(data.workout_id)
      setCompleted(false)
      setNotice(data.message || 'Workout started.')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  const completeWorkout = async () => {
    if (!workoutId || completed || busy) return
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post(`/workouts/complete/${workoutId}/`)
      if (data.status !== 'success') {
        throw new Error(data.message || 'The workout was not marked complete.')
      }
      setCompleted(true)
      setNotice(data.message || 'Workout completed.')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeading eyebrow="TRAIN WITH INTENTION" title="Workout" description="Your recommendation uses the fitness profile already saved in FitAI." action={<button className="button button-quiet button-small" onClick={loadPlan}><RotateCcw size={15} /> Refresh</button>} />
      {error && <Notice tone="error">{error}</Notice>}
      {notice && <Notice tone="success">{notice}</Notice>}
      {plan ? (
        <section className="glass-card workout-plan">
          <div className="workout-top">
            <div><p className="eyebrow">PERSONALIZED SESSION</p><h2>{plan.name}</h2><p className="muted">{plan.difficulty} · {plan.category} · {plan.equipment}</p></div>
            <div className="duration-pill"><Timer size={16} /> {plan.duration} min</div>
          </div>
          <div className="exercise-list">
            {(plan.exercises || []).map((exercise, index) => (
              <article className="exercise-row" key={`${exercise.name}-${index}`}>
                <span className="exercise-number">{String(index + 1).padStart(2, '0')}</span>
                <div className="exercise-name"><strong>{exercise.name}</strong><small>{exercise.muscle} · {exercise.difficulty}</small></div>
                <div className="exercise-count">{exercise.sets} sets <span>×</span> {exercise.reps} reps</div>
              </article>
            ))}
            {!plan.exercises?.length && <EmptyState icon={Dumbbell} title="No suitable exercises yet" text="Check your saved goal, equipment and fitness profile in the existing FitAI app." />}
          </div>
          <div className="workout-actions">
            <button className="button button-primary" onClick={startWorkout} disabled={busy || !plan.exercises?.length || Boolean(workoutId)}>
              {workoutId ? 'Workout started' : busy ? 'Starting…' : 'Start workout'} {!workoutId && <ArrowRight size={16} />}
            </button>
            {workoutId && <button className="button button-complete" onClick={completeWorkout} disabled={busy || completed}>{completed ? <><Check size={16} /> Completed</> : busy ? 'Saving…' : 'Mark completed'}</button>}
            {workoutId && <span className="workout-id">Session #{workoutId}</span>}
          </div>
        </section>
      ) : !error && <LoadingCard text="Loading your recommendation…" />}
      <p className="api-footnote">Starting or completing a workout saves it to your FitAI account. Completion uses the existing user-owned endpoint.</p>
    </>
  )
}

function AssistantPage() {
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages])

  const send = async (event) => {
    event.preventDefault()
    const message = text.trim()
    if (!message || busy) return
    setText('')
    setError('')
    setBusy(true)
    const previous = messages
    setMessages([...previous, { role: 'user', content: message }, { role: 'assistant', content: '' }])
    try {
      await streamChat(message, previous, (chunk) => {
        setMessages((current) => current.map((item, index) => (
          index === current.length - 1
            ? { ...item, content: item.content + chunk }
            : item
        )))
      })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
      setMessages((current) => current.map((item, index) => (
        index === current.length - 1 && item.role === 'assistant' && !item.content
          ? { ...item, content: 'I could not complete that response.' }
          : item
      )))
    } finally {
      setBusy(false)
    }
  }

  const clearChat = async () => {
    setError('')
    try {
      const { data } = await api.post('/chat/clear/')
      if (data?.success !== true) {
        throw new Error('The chat could not be cleared. Please sign in again.')
      }
      setMessages([])
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }
  }

  return (
    <>
      <PageHeading eyebrow="HERE TO HELP" title="AI Fitness Assistant" description="Ask about fitness, nutrition, routines or everyday questions." action={<button className="button button-quiet button-small" onClick={clearChat} disabled={!messages.length || busy}><RotateCcw size={15} /> Clear chat</button>} />
      <section className="glass-card chat-card">
        <div className="chat-topline"><span className="assistant-avatar"><Sparkles size={18} /></span><div><strong>FitAI Assistant</strong><small>Replies stream from your Django chatbot</small></div><span className="online-indicator">READY</span></div>
        <div className="chat-messages">
          {!messages.length && <div className="chat-welcome"><span className="chat-spark"><Sparkles size={22} /></span><h2>What would you like to work on?</h2><p>Start with a question and FitAI will help you think it through.</p></div>}
          {messages.map((item, index) => (
            <div className={`chat-message ${item.role}`} key={`${item.role}-${index}`}>
              <span className="message-label">{item.role === 'user' ? 'YOU' : 'FITAI'}</span>
              <p>{item.content || (busy && index === messages.length - 1 ? 'Thinking…' : '')}</p>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        {error && <div className="chat-error"><X size={15} />{error}</div>}
        <form className="chat-form" onSubmit={send}>
          <input value={text} onChange={(event) => setText(event.target.value)} placeholder="Ask your fitness assistant…" maxLength={4000} aria-label="Message" />
          <button className="send-button" disabled={busy || !text.trim()} aria-label="Send message">{busy ? <span className="spinner" /> : <Send size={17} />}</button>
        </form>
        <p className="chat-disclaimer">AI responses can be inaccurate. For medical concerns, consult a qualified professional.</p>
      </section>
    </>
  )
}

const DIET_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function DietPage() {
  const [height, setHeight] = useState('')
  const [weight, setWeight] = useState('')
  const [result, setResult] = useState(null)
  const [weeklyPlan, setWeeklyPlan] = useState(null)
  const [selectedDay, setSelectedDay] = useState(DIET_DAYS[0])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadPlan = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/diet/api/plan/')
      if (data?.has_profile && data.profile) {
        setHeight(String(data.profile.height_cm))
        setWeight(String(data.profile.weight_kg))
        setResult(data.profile)
      }
      if (data?.weekly_plan) {
        setWeeklyPlan(data.weekly_plan)
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    api.get('/diet/api/plan/')
      .then(({ data }) => {
        if (!active) return
        if (data?.has_profile && data.profile) {
          setHeight(String(data.profile.height_cm))
          setWeight(String(data.profile.weight_kg))
          setResult(data.profile)
        }
        if (data?.weekly_plan) {
          setWeeklyPlan(data.weekly_plan)
        }
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  const save = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post('/diet/api/save-profile/', {
        height: Number(height),
        weight: Number(weight),
      })
      if (data?.success !== true) {
        throw new Error(data?.error || 'The profile could not be saved.')
      }
      setResult(data)
      await loadPlan()
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  const currentDayData = weeklyPlan?.[selectedDay]
  const meals = currentDayData?.meals || []
  const totals = currentDayData?.total || currentDayData || {}

  return (
    <>
      <PageHeading
        eyebrow="PERSONALIZED NUTRITION"
        title="Diet plan"
        description="Save your measurements to calculate BMI and review your balanced 7-day Indian diet plan."
        action={
          <button className="button button-quiet button-small" onClick={loadPlan} disabled={busy || loading}>
            <RotateCcw size={15} /> Refresh plan
          </button>
        }
      />

      {error && <Notice tone="error">{error}</Notice>}
      {result && (
        <Notice tone="success">
          BMI {result.bmi} · <strong>{result.bmi_category}</strong> (Height: {height} cm, Weight: {weight} kg)
        </Notice>
      )}

      <div className="two-column" style={{ marginBottom: '24px' }}>
        <section className="glass-card panel">
          <div className="section-title">
            <h2>Your measurements</h2>
            <span><Scale size={14} /> PROFILE</span>
          </div>
          <form className="form-stack" onSubmit={save}>
            <label>
              Height <span className="unit-label">cm</span>
              <input
                type="number"
                min="50"
                max="250"
                step="0.1"
                value={height}
                onChange={(event) => setHeight(event.target.value)}
                required
              />
            </label>
            <label>
              Weight <span className="unit-label">kg</span>
              <input
                type="number"
                min="10"
                max="300"
                step="0.1"
                value={weight}
                onChange={(event) => setWeight(event.target.value)}
                required
              />
            </label>
            <button className="button button-primary button-full" disabled={busy}>
              {busy ? 'Saving & Generating…' : 'Save measurements'} {!busy && <Check size={16} />}
            </button>
          </form>
          <p className="api-footnote">
            Saving new measurements recalculates your BMI and generates your personalized weekly diet recommendations.
          </p>
        </section>

        <section className="glass-card panel feature-panel">
          <span className="feature-icon large"><Leaf size={22} /></span>
          <p className="eyebrow">BALANCED INDIAN NUTRITION</p>
          <h2>{result?.bmi_category || 'Personalized'} Diet Plan</h2>
          <p className="muted">
            FitAI crafts a structured 5-meal daily schedule tailored to your BMI category with realistic Indian foods,
            macro estimates, and approximate costs.
          </p>
          <a className="button button-quiet button-small" href={`${API_BASE_URL}/diet/`} target="_blank" rel="noreferrer" style={{ marginTop: 'auto' }}>
            Open Django view <ArrowUpRight size={15} />
          </a>
        </section>
      </div>

      {loading ? (
        <LoadingCard text="Loading your weekly diet plan…" />
      ) : weeklyPlan ? (
        <section className="glass-card panel" style={{ marginTop: '20px' }}>
          <div className="section-title" style={{ marginBottom: '16px' }}>
            <h2>Weekly Meal Plan</h2>
            <span><Utensils size={14} /> 7-DAY SCHEDULE</span>
          </div>

          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '10px', marginBottom: '18px' }}>
            {DIET_DAYS.map((day) => {
              const active = selectedDay === day
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => setSelectedDay(day)}
                  className={`button button-small ${active ? 'button-primary' : 'button-quiet'}`}
                  style={{ flexShrink: 0 }}
                >
                  {day}
                </button>
              )
            })}
          </div>

          {totals?.calories ? (
            <div
              className="nutrition-grid"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
                gap: '10px',
                marginBottom: '20px',
                padding: '14px',
                borderRadius: '13px',
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.05)',
              }}
            >
              <NutritionValue label="Day Calories" value={totals.calories} unit="kcal" />
              <NutritionValue label="Day Protein" value={totals.protein} unit="g" />
              <NutritionValue label="Day Carbs" value={totals.carbs} unit="g" />
              <NutritionValue label="Day Fat" value={totals.fat} unit="g" />
              <NutritionValue label="Day Fiber" value={totals.fiber} unit="g" />
              <NutritionValue label="Est. Cost" value={totals.cost ? `₹${totals.cost}` : '—'} unit="" />
            </div>
          ) : null}

          <div style={{ display: 'grid', gap: '12px' }}>
            {meals.map((meal, index) => (
              <article
                key={`${meal.meal}-${index}`}
                className="glass-card"
                style={{
                  padding: '16px 18px',
                  borderRadius: '14px',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.05)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span className="eyebrow" style={{ margin: 0 }}>
                    {meal.meal || `Meal ${index + 1}`}
                  </span>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: 'var(--muted)' }}>
                    {meal.calories ? <span><b>{meal.calories}</b> kcal</span> : null}
                    {meal.cost ? <span>₹{meal.cost}</span> : null}
                  </div>
                </div>

                <strong style={{ fontSize: '15px', color: '#f3f1fa', display: 'block', marginBottom: '6px' }}>
                  {meal.food}
                </strong>

                {meal.ingredients?.length ? (
                  <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--muted)' }}>
                    Ingredients: {Array.isArray(meal.ingredients) ? meal.ingredients.join(', ') : meal.ingredients}
                  </p>
                ) : null}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', fontSize: '11px', color: 'var(--muted)' }}>
                  {meal.protein ? <span>Protein: <b style={{ color: '#e5e1ed' }}>{meal.protein}g</b></span> : null}
                  {meal.carbs ? <span>Carbs: <b style={{ color: '#e5e1ed' }}>{meal.carbs}g</b></span> : null}
                  {meal.fat ? <span>Fat: <b style={{ color: '#e5e1ed' }}>{meal.fat}g</b></span> : null}
                  {meal.fiber ? <span>Fiber: <b style={{ color: '#e5e1ed' }}>{meal.fiber}g</b></span> : null}
                </div>
              </article>
            ))}
            {!meals.length && (
              <EmptyState
                icon={Leaf}
                title="No meals found for this day"
                text="Save your measurements above to generate your complete 7-day Indian meal plan."
              />
            )}
          </div>
        </section>
      ) : (
        <EmptyState
          icon={Leaf}
          title="No diet plan generated yet"
          text="Enter your height and weight above and save your measurements to create your personalized weekly diet plan."
        />
      )}
    </>
  )
}

function ProgressPage() {
  const [summary, setSummary] = useState(null)
  const [steps, setSteps] = useState('')
  const [goal, setGoal] = useState('')
  const [weight, setWeight] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    const { data } = await api.get('/progress/api/summary/')
    setSummary(data)
    setGoal(String(data.steps_goal))
    if (data.weight_kg != null) setWeight(String(data.weight_kg))
  }

  useEffect(() => {
    let active = true
    api.get('/progress/api/summary/')
      .then(({ data }) => {
        if (!active) return
        setSummary(data)
        setGoal(String(data.steps_goal))
        if (data.weight_kg != null) setWeight(String(data.weight_kg))
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError))
      })
    return () => { active = false }
  }, [])

  const update = async (event, endpoint, payload, successText) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await api.post(endpoint, payload)
      await load()
      setNotice(successText)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeading eyebrow="CONSISTENCY OVER PERFECTION" title="Progress" description="Update your steps, daily target and weight using your existing FitAI endpoints." />
      {error && <Notice tone="error">{error}</Notice>}
      {notice && <Notice tone="success">{notice}</Notice>}
      <section className="metric-grid progress-metrics">
        <Metric icon={Footprints} label="Steps today" value={summary?.steps ?? '—'} unit="steps" />
        <Metric icon={ArrowUpRight} label="Step goal" value={summary?.steps_goal?.toLocaleString() ?? '—'} unit="steps" />
        <Metric icon={Timer} label="Active minutes" value={summary?.active_minutes ?? '—'} unit="min" />
        <Metric icon={Scale} label="Weight" value={summary?.weight_kg ?? '—'} unit="kg" />
      </section>
      <div className="progress-forms">
        <form className="glass-card panel form-stack" onSubmit={(event) => update(event, '/progress/update-steps/', { steps_increment: Number(steps) }, 'Steps updated.')}>
          <div className="section-title"><h2>Add steps</h2><span><Footprints size={14} /> TODAY</span></div>
          <p className="muted">Adds to your current daily step count.</p>
          <label>Steps to add<input type="number" min="1" max="100000" value={steps} onChange={(event) => setSteps(event.target.value)} required /></label>
          <button className="button button-primary button-full" disabled={busy}>Add steps <ArrowUpRight size={16} /></button>
        </form>
        <form className="glass-card panel form-stack" onSubmit={(event) => update(event, '/progress/update-goal/', { goal: Number(goal) }, 'Step goal saved.')}>
          <div className="section-title"><h2>Step goal</h2><span><HeartPulse size={14} /> DAILY</span></div>
          <p className="muted">Choose a goal between 1,000 and 50,000 steps.</p>
          <label>Daily target<input type="number" min="1000" max="50000" step="500" value={goal} onChange={(event) => setGoal(event.target.value)} required /></label>
          <button className="button button-primary button-full" disabled={busy}>Save goal <Check size={16} /></button>
        </form>
        <form className="glass-card panel form-stack" onSubmit={(event) => update(event, '/progress/update-weight/', { weight: Number(weight) }, 'Weight saved.')}>
          <div className="section-title"><h2>Update weight</h2><span><Scale size={14} /> PROFILE</span></div>
          <p className="muted">Record a weight between 20 and 300 kg.</p>
          <label>Weight in kg<input type="number" min="20" max="300" step="0.1" value={weight} onChange={(event) => setWeight(event.target.value)} required /></label>
          <button className="button button-primary button-full" disabled={busy}>Save weight <Check size={16} /></button>
        </form>
      </div>
      <section className="glass-card panel weekly-panel">
        <div className="section-title"><h2>Recent steps</h2><span>LAST 7 DAYS</span></div>
        {summary?.weekly_progress?.length ? (
          <div className="week-bars">
            {summary.weekly_progress.map((day) => {
              const heightPercent = Math.min(100, Math.round((day.steps / Math.max(summary.steps_goal, 1)) * 100))
              return <div className="week-day" key={day.date}><div className="bar-track"><span style={{ height: `${heightPercent}%` }} /></div><small>{day.date}</small><b>{day.steps.toLocaleString()}</b></div>
            })}
          </div>
        ) : <p className="muted">No saved daily progress records yet. Saving your first update will start your history.</p>}
      </section>
    </>
  )
}

function RemindersPage() {
  return (
    <>
      <PageHeading eyebrow="A LITTLE NUDGE" title="Reminders" description="Keep your routine close, without adding noise to your day." />
      <section className="glass-card feature-panel wide-feature">
        <span className="feature-icon large"><Bell size={22} /></span>
        <p className="eyebrow">EXISTING DJANGO EXPERIENCE</p>
        <h2>Manage your reminders</h2>
        <p className="muted">Reminder scheduling and browser notification controls currently live in the existing Django form page. No JSON read/write API is available yet, so changes are managed there.</p>
        <a className="button button-primary" href={`${API_BASE_URL}/reminders/`} target="_blank" rel="noreferrer">Open reminders <ArrowUpRight size={16} /></a>
      </section>
      <p className="api-footnote">Your existing reminder records and notification behavior are unchanged.</p>
    </>
  )
}

function PosturePage() {
  return (
    <>
      <PageHeading eyebrow="MOVE WITH AWARENESS" title="AI Posture Check" description="Use the camera-based posture experience in your existing FitAI app." />
      <section className="glass-card posture-card">
        <div className="posture-visual"><span><Camera size={30} /></span><div className="scan-line" /></div>
        <div className="posture-copy">
          <p className="eyebrow">CAMERA EXPERIENCE</p>
          <h2>Check your form in the browser</h2>
          <p className="muted">The current posture feature is an HTML page using browser camera access and external frontend dependencies. Open it directly to grant camera permission in its own tab.</p>
          <a className="button button-primary" href={`${API_BASE_URL}/ai-features/posture-check/`} target="_blank" rel="noreferrer">Open posture check <ArrowUpRight size={16} /></a>
          <p className="api-footnote">Camera access requires HTTPS and your permission. The feature has not been reimplemented as a React API.</p>
        </div>
      </section>
    </>
  )
}

function EmptyState({ icon: Icon, title, text }) {
  return <div className="empty-state"><span><Icon size={22} /></span><h3>{title}</h3><p>{text}</p></div>
}

function LoadingCard({ text }) {
  return <div className="glass-card loading-card"><span className="spinner" />{text}</div>
}

function LoadingPage() {
  return <main className="loading-page"><span className="spinner" />Connecting to FitAI…</main>
}

function Notice({ tone, children }) {
  return <div className={`notice ${tone}`}>{tone === 'success' ? <Check size={16} /> : <X size={16} />}{children}</div>
}

function NotFoundPage() {
  return <main className="auth-page"><section className="glass-card auth-card"><p className="eyebrow">404</p><h1>Page not found</h1><p className="muted">That FitAI page doesn't exist.</p><Link className="button button-primary" to="/">Back to home <ArrowRight size={16} /></Link></section></main>
}

export default App
