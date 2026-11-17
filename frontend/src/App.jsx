import { createContext, useContext, useEffect, useRef, useState } from 'react';
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
} from 'react-router-dom';
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
} from 'lucide-react';
import {
  API_BASE_URL,
  api,
  getErrorMessage,
  initializeCsrf,
  streamChat,
  updateCsrfToken,
} from './api';

const AuthContext = createContext(null);
function useAuth() {
  return useContext(AuthContext);
}

function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [connectionError, setConnectionError] = useState('');

  useEffect(() => {
    initializeCsrf()
      .then(() => api.get('/users/api/session/'))
      .then(({ data }) => setUser(data.user))
      .catch((error) => {
        if (error.response?.status !== 401) {
          setConnectionError(getErrorMessage(error));
        }
      })
      .finally(() => setAuthLoading(false));
  }, []);

  const value = {
    user,
    setUser,
    authLoading,
    connectionError,
    setConnectionError,
  };

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
  );
}

function RequireAuth() {
  const { user, authLoading, connectionError } = useAuth();
  const location = useLocation();

  if (authLoading) return <LoadingPage />;
  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location, connectionError }}
      />
    );
  }
  return <Outlet />;
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
            Bring your workouts, nutrition, progress and AI fitness assistant together in one calm, focused dashboard.
          </p>
          <div className="hero-actions">
            <Link className="button button-primary" to="/register">Create your account <ArrowRight size={17} /></Link>
            <Link className="button button-quiet" to="/login">I already have an account</Link>
          </div>
          <div className="hero-proof"><ShieldCheck size={16} /> Private, session-based access to your FitAI account</div>
        </div>
        <div className="hero-visual">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="hero-core"><Activity size={46} /></div>
          <div className="float-card float-card-top"><Dumbbell size={17} />Move with purpose</div>
          <div className="float-card float-card-bottom"><HeartPulse size={17} />Progress at your pace</div>
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
  );
}

function Feature({ icon: Icon, title, text }) {
  return (
    <article className="feature-card">
      <span className="feature-icon"><Icon size={19} /></span>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

function AuthPage({ mode }) {
  const isRegister = mode === 'register';
  const navigate = useNavigate();
  const location = useLocation();
  const { user, setUser, connectionError } = useAuth();
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
  });
  const [error, setError] = useState(location.state?.connectionError || '');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const update = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
  };

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      await initializeCsrf();
      const { data } = await api.post(
        isRegister ? '/users/api/register/' : '/users/api/login/',
        isRegister
          ? {
              username: form.username,
              email: form.email,
              password1: form.password,
              password2: form.password2,
            }
          : { username: form.username, password: form.password }
      );
      updateCsrfToken(data.csrfToken);
      setUser(data.user);
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  };

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
  );
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
];

function AppLayout() {
  const { user, setUser } = useAuth();
  const [logoutError, setLogoutError] = useState('');

  const signOut = async () => {
    setLogoutError('');
    try {
      const { data } = await api.post('/users/api/logout/');
      updateCsrfToken(data.csrfToken);
      setUser(null);
    } catch (error) {
      setLogoutError(getErrorMessage(error));
    }
  };

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
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
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
          <button className="nav-item signout" onClick={signOut}>
            <LogOut size={17} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="topbar-brand">
            <span className="brand-mark"><Activity size={18} /></span> Fit<span className="brand-accent">AI</span>
          </div>
          <div className="topbar-note"><span className="status-dot" /> Your personal fitness space</div>
          <span className="topbar-user">{user?.username}</span>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  );
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
  );
}

function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/dashboard/api/summary/')
      .then(({ data }) => setSummary(data))
      .catch((requestError) => setError(getErrorMessage(requestError)));
  }, []);

  const dayName = summary?.day_name || 'TODAY';

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
        <div className="section-title"><h2>Today's Diet Meals</h2><span><Utensils size={14} /> {dayName.toUpperCase()}</span></div>
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
                  {meal.protein && <span>Protein: <b style={{ color: '#e5e1ed' }}>{meal.protein}g</b></span>}
                  {meal.cost && <span>₹{meal.cost}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ marginTop: '14px', padding: '12px 0', color: 'var(--muted)', fontSize: '12px' }}>
            No diet meals planned for today yet. <Link to="/diet" style={{ color: 'var(--purple)', fontWeight: 600 }}>View or generate your weekly diet plan →</Link>
          </div>
        )}
      </section>
      <section className="dashboard-lower">
        <div className="glass-card welcome-card">
          <div className="card-overline"><Sparkles size={15} /> YOUR NEXT STEP</div>
          <h2>Small steps add up.</h2>
          <p>Choose one focus for today. Your progress page can update the steps, goal and weight whenever you need.</p>
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
  );
}

function Metric({ icon: Icon, label, value, unit }) {
  return (
    <article className="metric-card glass-card">
      <span className="metric-icon"><Icon size={18} /></span>
      <p>{label}</p>
      <div className="metric-value">{typeof value === 'number' ? value.toLocaleString() : value}<small>{unit}</small></div>
    </article>
  );
}

function QuickLink({ to, icon: Icon, title, text }) {
  return (
    <Link to={to} className="quick-link">
      <span className="quick-icon"><Icon size={18} /></span>
      <span><strong>{title}</strong><small>{text}</small></span>
      <ArrowRight size={16} />
    </Link>
  );
}

function NutritionPage() {
  const [image, setImage] = useState('');
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const chooseImage = (event) => {
    setError('');
    setResult(null);
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Choose an image file to scan.');
      return;
    }
    const startResize = performance.now();
    const img = new Image();
    const reader = new FileReader();
    reader.onload = () => {
      img.onload = () => {
        // Resize to max 640px while keeping aspect ratio
        const maxDim = 640;
        let { width, height } = img;
        if (width > height) {
          if (width > maxDim) { height = Math.round((height * maxDim) / width); width = maxDim; }
        } else {
          if (height > maxDim) { width = Math.round((width * maxDim) / height); height = maxDim; }
        }
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        // Compress to JPEG (quality 0.7)
        const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
        const resizeTime = performance.now() - startResize;
        console.log('Image resized/compressed in', (resizeTime/1000).toFixed(2), 's');
        setImage(dataUrl);
        setPreview(dataUrl);
      };
      img.src = reader.result;
    };
    reader.onerror = () => setError('The selected image could not be read.');
    reader.readAsDataURL(file);
    // Do not set preview until resize complete
    return;
  };
    setError('');
    setResult(null);
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Choose an image file to scan.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const value = typeof reader.result === 'string' ? reader.result : '';
      setImage(value);
      setPreview(value);
    };
    reader.onerror = () => setError('The selected image could not be read.');
    reader.readAsDataURL(file);
  };

  const scan = async (event) => {
    event.preventDefault();
    // Clear previous result but keep image preview
    setResult(null);
    setError('');
    if (!image) {
      setError('Choose a meal photo first.');
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post('/nutrition/scan/', { image });
      setResult(data.nutrition || data);
    } catch (requestError) {
      const status = requestError.response?.status;
      if (status === 503) {
        setError('Gemini is temporarily unavailable. Please try again later.');
      } else if (status === 429) {
        setError('Gemini API quota exceeded. Please try again later.');
      } else {
        setError(getErrorMessage(requestError));
      }
    } finally {
      setBusy(false);
    }
  };

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
  );
}

function NutritionValue({ label, value, unit }) {
  return (
    <div className="nutrition-value"><small>{label}</small><strong>{value ?? '—'}<span>{unit}</span></strong></div>
  );
}

// ... The rest of the components (WorkoutPage, AssistantPage, DietPage, ProgressPage, etc.) remain unchanged.

export default App;
