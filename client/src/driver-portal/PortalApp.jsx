import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { PortalProvider, usePortal } from './PortalContext'
import { portalRequest, portalToken } from './api'
import './portal.css'

const path = '/portal'
const displayStatus = value => String(value || 'unknown').replaceAll('_', ' ')
const money = (amount, currency = 'PHP') => amount == null
  ? 'Not assessed'
  : new Intl.NumberFormat('en-PH', { style: 'currency', currency }).format(Number(amount))

function useRequest(url, key) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setData(await portalRequest(url)) }
    catch (cause) { setError(cause.message || 'Could not load data') }
    finally { setLoading(false) }
  }, [url])
  useEffect(() => { void reload() }, [reload, key])
  return { data, loading, error, reload }
}

function Status({ value }) {
  return <span className={`portal-status status-${String(value || 'pending').toLowerCase().replaceAll(' ', '-')}`}>{displayStatus(value)}</span>
}

function PublicLayout() {
  const { user } = usePortal()
  return (
    <div className="portal-public">
      <header className="portal-public-header">
        <Link className="portal-brand" to={path}><span className="portal-brand-mark">V</span><span>VERITAS<small>DRIVER PORTAL</small></span></Link>
        <nav aria-label="Portal navigation">
          <NavLink to={`${path}/track`}>Track registration</NavLink>
          {user ? <Link className="portal-button portal-button-dark" to={`${path}/dashboard`}>My account</Link> : <><Link to={`${path}/login`}>Log in</Link><Link className="portal-button portal-button-dark" to={`${path}/signup`}>Create account</Link></>}
        </nav>
      </header>
      <main className="portal-public-main"><Outlet /></main>
      <footer className="portal-public-footer"><span>VERITAS · Driver Portal</span><nav><Link to={`${path}/privacy`}>Privacy</Link><Link to={`${path}/terms`}>Terms</Link><Link to="/dashboard">Staff dashboard</Link></nav></footer>
    </div>
  )
}

function HomePage() {
  return (
    <div className="portal-home">
      <section className="portal-hero">
        <div className="portal-hero-copy">
          <span className="portal-eyebrow">VERITAS TRAFFIC MANAGEMENT</span>
          <h1>Registration and verification for safer roads.</h1>
          <p>Register your vehicle, follow its verification status, and review confirmed traffic violations linked to your verified vehicle.</p>
          <div className="portal-actions"><Link className="portal-button portal-button-green" to={`${path}/signup`}>Create an account</Link><Link className="portal-button portal-button-outline" to={`${path}/login`}>Log in</Link></div>
          <p className="portal-fine-print">Staff review ownership details before a vehicle is linked to an account.</p>
        </div>
        <div className="portal-hero-card"><span className="portal-signal"><i /><i /><i /></span><div className="portal-hero-grid"><span>VEHICLE CHECK</span><b>Pending staff review</b><small>Registration · Ownership · Verified plate</small></div><div className="portal-road"><i /><i /><i /></div></div>
      </section>
      <section className="portal-feature-grid" aria-label="Portal features">
        <article><span>01</span><h2>Register your vehicle</h2><p>Submit plate, vehicle details and OR/CR numbers for staff review.</p></article>
        <article><span>02</span><h2>Track your application</h2><p>See pending, verified or rejected status and staff notes.</p></article>
        <article><span>03</span><h2>Review your record</h2><p>Confirmed detections appear only for vehicles verified under your account.</p></article>
      </section>
      <section className="portal-faq"><span className="portal-eyebrow">HELP</span><h2>Frequently asked questions</h2><details><summary>Why is my vehicle pending?</summary><p>An administrator is checking the submitted registration and ownership details.</p></details><details><summary>Where do I see a rejected registration?</summary><p>Sign in and open Track registration. The administrator’s reason appears with the application.</p></details><details><summary>When will a traffic record appear?</summary><p>After staff confirm the detection and the plate matches a vehicle verified under your account.</p></details><details><summary>Can I pay a penalty online?</summary><p>No payment provider is configured in this local portal. The payment pages are informational only.</p></details><details><summary>How do I get a password reset?</summary><p>Email delivery is not configured. Contact a VERITAS portal administrator for help.</p></details></section>
    </div>
  )
}

function AuthCard({ title, intro, children }) {
  return <section className="portal-auth-card"><span className="portal-eyebrow">DRIVER ACCOUNT</span><h1>{title}</h1><p>{intro}</p>{children}</section>
}

function LoginPage() {
  const { signIn } = usePortal()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async event => {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try { await signIn(form.get('email'), form.get('password')); navigate(location.state?.from || `${path}/dashboard`, { replace: true }) }
    catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }
  return <AuthCard title="Welcome back" intro="Sign in to view your vehicle registrations and confirmed violations."><form className="portal-form" onSubmit={submit}><label>Email<input type="email" name="email" autoComplete="username" required /></label><label>Password<input type="password" name="password" autoComplete="current-password" required /></label>{error && <p className="portal-error" role="alert">{error}</p>}<button className="portal-button portal-button-green" disabled={busy}>{busy ? 'Signing in…' : 'Log in'}</button></form><p className="portal-auth-links"><Link to={`${path}/forgot`}>Forgot password?</Link><span>New here? <Link to={`${path}/signup`}>Create account</Link></span></p></AuthCard>
}

function SignupPage() {
  const { signUp } = usePortal()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async event => {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    if (form.get('password') !== form.get('confirm_password')) { setError('The passwords do not match.'); setBusy(false); return }
    try {
      await signUp({ email: form.get('email'), password: form.get('password'), first_name: form.get('first_name'), last_name: form.get('last_name'), phone: form.get('phone') })
      navigate(`${path}/dashboard`, { replace: true })
    } catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }
  return <AuthCard title="Create your account" intro="Use your details to register vehicles and track staff review."><form className="portal-form" onSubmit={submit}><div className="portal-form-row"><label>First name<input name="first_name" autoComplete="given-name" required /></label><label>Last name<input name="last_name" autoComplete="family-name" required /></label></div><label>Email<input type="email" name="email" autoComplete="email" required /></label><label>Mobile number <small>Optional</small><input type="tel" name="phone" autoComplete="tel" /></label><div className="portal-form-row"><label>Password<input type="password" name="password" minLength={10} autoComplete="new-password" required /><small>At least 10 characters</small></label><label>Confirm password<input type="password" name="confirm_password" minLength={10} autoComplete="new-password" required /></label></div>{error && <p className="portal-error" role="alert">{error}</p>}<button className="portal-button portal-button-green" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button></form><p className="portal-auth-links"><span>Already registered? <Link to={`${path}/login`}>Log in</Link></span></p><p className="portal-fine-print">This local portal does not send email verification codes. Staff verify vehicle ownership after you submit registration details.</p></AuthCard>
}

function ForgotPage() {
  return <AuthCard title="Password help" intro="Email-based password reset is not configured for this local SQLite portal."><div className="portal-note"><b>Need to reset your password?</b><p>Ask a VERITAS administrator to reset your account, or sign in and change it from Profile &amp; Settings.</p></div><Link className="portal-button portal-button-outline" to={`${path}/login`}>Back to log in</Link></AuthCard>
}

function LegalPage({ title, kind }) {
  return <section className="portal-legal"><span className="portal-eyebrow">VERITAS DRIVER PORTAL</span><h1>{title}</h1><p className="portal-fine-print">Draft policy for the local VERITAS demonstration portal.</p>{kind === 'privacy' ? <><h2>Information stored</h2><p>Account details, submitted vehicle information, ownership review decisions, and portal disputes are stored in the local SQLite database on the VERITAS server.</p><h2>Who can see your data</h2><p>Drivers can view their own account and verified vehicle records. Portal administrators can review vehicle applications and disputes.</p><h2>Traffic records</h2><p>Confirmed camera detections are associated with a driver only when the plate matches a vehicle verified under their account.</p></> : <><h2>Vehicle registration</h2><p>Submitted vehicle details remain pending until an authorised VERITAS administrator reviews them. Do not submit information for a vehicle you do not own or manage.</p><h2>Traffic records</h2><p>Camera detections require staff review before they are shown as confirmed records in a driver account.</p><h2>Local demonstration</h2><p>This portal does not process online payments or send email verification codes.</p></>}</section>
}

function RequirePortalUser() {
  const { user, loading } = usePortal()
  const location = useLocation()
  if (loading) return <div className="portal-loading">Loading your account…</div>
  return user ? <Outlet /> : <Navigate to={`${path}/login`} replace state={{ from: location.pathname }} />
}

function RequirePortalAdmin() {
  const { user, loading } = usePortal()
  if (loading) return <div className="portal-loading">Checking administrator access…</div>
  return user?.role === 'admin' ? <Outlet /> : <Navigate to={user ? `${path}/dashboard` : `${path}/login`} replace />
}

const driverLinks = [
  ['dashboard', 'Overview'], ['vehicles', 'My vehicles'], ['register', 'Register vehicle'],
  ['track', 'Track registration'], ['violations', 'Violations'], ['payments', 'Payments'], ['profile', 'Profile & settings'],
]

function DriverLayout() {
  const { user, signOut } = usePortal()
  const navigate = useNavigate()
  const logout = async () => { await signOut(); navigate(path, { replace: true }) }
  return <div className="portal-workspace"><aside className="portal-nav"><Link className="portal-brand" to={path}><span className="portal-brand-mark">V</span><span>VERITAS<small>DRIVER PORTAL</small></span></Link><div className="portal-nav-user"><b>{user.first_name} {user.last_name}</b><small>{user.email}</small></div><nav aria-label="Driver account">{driverLinks.map(([to, label]) => <NavLink key={to} to={`${path}/${to}`} className={({ isActive }) => isActive ? 'active' : ''}>{label}</NavLink>)}{user.role === 'admin' && <NavLink to={`${path}/admin/vehicles`}>Portal administration</NavLink>}</nav><button className="portal-nav-logout" onClick={logout}>Log out</button></aside><main className="portal-content"><Outlet /></main></div>
}

function PageHeading({ eyebrow, title, detail, action }) {
  return <header className="portal-page-heading"><div><span className="portal-eyebrow">{eyebrow}</span><h1>{title}</h1>{detail && <p>{detail}</p>}</div>{action}</header>
}

function Empty({ children }) { return <div className="portal-empty">{children}</div> }

function DashboardPage() {
  const { user } = usePortal()
  const { data: vehicleData, loading: vehiclesLoading } = useRequest('/me/vehicles', user.id)
  const { data: violationData, loading: violationsLoading } = useRequest('/me/violations', user.id)
  const vehicles = vehicleData?.vehicles || []
  const violations = violationData?.violations || []
  return <><PageHeading eyebrow="YOUR ACCOUNT" title={`Hello, ${user.first_name}`} detail="Your registrations and confirmed traffic records at a glance." action={<Link className="portal-button portal-button-green" to={`${path}/register`}>Register a vehicle</Link>} /><section className="portal-stat-grid"><article><small>Vehicles</small><b>{vehiclesLoading ? '—' : vehicles.length}</b><span>In your garage</span></article><article><small>Pending review</small><b>{vehicles.filter(vehicle => vehicle.verification_status === 'pending').length}</b><span>Waiting for staff</span></article><article><small>Confirmed violations</small><b>{violationsLoading ? '—' : violations.length}</b><span>Linked to verified vehicles</span></article></section><section className="portal-panel"><div className="portal-panel-heading"><div><span className="portal-eyebrow">REGISTRATION STATUS</span><h2>Your vehicles</h2></div><Link to={`${path}/vehicles`}>View all</Link></div>{vehiclesLoading ? <Empty>Loading vehicles…</Empty> : vehicles.length ? <div className="portal-table-wrap"><table className="portal-table"><thead><tr><th>Plate</th><th>Vehicle</th><th>Status</th><th>Submitted</th></tr></thead><tbody>{vehicles.slice(0, 5).map(vehicle => <tr key={vehicle.id}><td><b>{vehicle.plate_number}</b></td><td>{[vehicle.year, vehicle.make, vehicle.model].filter(Boolean).join(' ') || vehicle.vehicle_type}</td><td><Status value={vehicle.verification_status} /></td><td>{new Date(vehicle.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div> : <Empty>No vehicles yet. <Link to={`${path}/register`}>Register your first vehicle.</Link></Empty>}</section>{violations.length > 0 && <section className="portal-panel"><div className="portal-panel-heading"><div><span className="portal-eyebrow">LATEST ACTIVITY</span><h2>Recent violations</h2></div><Link to={`${path}/violations`}>View history</Link></div><ViolationTable violations={violations.slice(0, 5)} /></section>}</>
}

function VehiclesPage() {
  const { user } = usePortal()
  const { data, loading, error, reload } = useRequest('/me/vehicles', user.id)
  const [actionError, setActionError] = useState('')
  const remove = async id => {
    if (!window.confirm('Remove this vehicle from your active portal list?')) return
    setActionError('')
    try { await portalRequest(`/me/vehicles/${encodeURIComponent(id)}`, { method: 'DELETE' }); await reload() }
    catch (cause) { setActionError(cause.message) }
  }
  const vehicles = data?.vehicles || []
  return <><PageHeading eyebrow="YOUR GARAGE" title="My vehicles" detail="Review ownership status and manage your registered vehicles." action={<Link className="portal-button portal-button-green" to={`${path}/register`}>Register vehicle</Link>} />{(error || actionError) && <p className="portal-error">{actionError || error}</p>}{loading ? <Empty>Loading vehicles…</Empty> : vehicles.length ? <div className="portal-card-list">{vehicles.map(vehicle => <article className="portal-vehicle-card" key={vehicle.id}><div><span className="portal-eyebrow">{vehicle.vehicle_type}</span><h2>{vehicle.plate_number}</h2><p>{[vehicle.year, vehicle.make, vehicle.model, vehicle.color].filter(Boolean).join(' · ') || 'Vehicle details submitted'}</p><small>Submitted {new Date(vehicle.created_at).toLocaleDateString()}</small></div><div className="portal-vehicle-state"><Status value={vehicle.verification_status} />{vehicle.remarks && <p>{vehicle.remarks}</p>}</div><button className="portal-button portal-button-outline" onClick={() => remove(vehicle.id)}>Remove</button></article>)}</div> : <Empty>Your vehicle list is empty. <Link to={`${path}/register`}>Submit a vehicle for review.</Link></Empty>}</>
}

function RegisterVehiclePage() {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const submit = async event => {
    event.preventDefault(); setBusy(true); setError(''); setSuccess('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const body = Object.fromEntries(form.entries())
    try { await portalRequest('/me/vehicles', { method: 'POST', body }); setSuccess('Vehicle submitted for staff review.'); formElement.reset(); setTimeout(() => navigate(`${path}/track`), 700) }
    catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }
  return <><PageHeading eyebrow="VEHICLE OWNERSHIP" title="Register a vehicle" detail="Provide the registration details staff need to verify ownership." /><section className="portal-panel portal-form-panel"><form className="portal-form" onSubmit={submit}><label>Plate number<input name="plate_number" placeholder="ABC 1234" autoCapitalize="characters" maxLength={24} required /></label><div className="portal-form-row"><label>Vehicle type<select name="vehicle_type" required><option value="">Select type</option>{['Car', 'Motorcycle', 'SUV', 'Van', 'Truck', 'Tricycle', 'Other'].map(type => <option key={type}>{type}</option>)}</select></label><label>Color<input name="color" maxLength={40} /></label></div><div className="portal-form-row"><label>Make<input name="make" maxLength={80} /></label><label>Model<input name="model" maxLength={80} /></label><label>Year<input name="year" inputMode="numeric" maxLength={4} /></label></div><div className="portal-form-row"><label>OR number<input name="or_number" maxLength={80} required /></label><label>CR number<input name="cr_number" maxLength={80} required /></label></div><label>Registration valid until<input name="registration_expiry" type="date" /></label><div className="portal-note"><b>What happens next?</b><p>Your application stays pending until an administrator reviews the ownership details. Rejected applications include the staff reason and can be resubmitted.</p></div>{error && <p className="portal-error" role="alert">{error}</p>}{success && <p className="portal-success" role="status">{success}</p>}<button className="portal-button portal-button-green" disabled={busy}>{busy ? 'Submitting…' : 'Submit for review'}</button></form></section></>
}

function TrackPage() {
  const { user } = usePortal()
  const { data, loading, error, reload } = useRequest('/me/vehicles', user.id)
  const vehicles = data?.vehicles || []
  return <><PageHeading eyebrow="APPLICATION TRACKING" title="Track registration" detail="Only registrations submitted from your account are shown here." action={<button className="portal-button portal-button-outline" onClick={reload}>Refresh</button>} />{error && <p className="portal-error">{error}</p>}{loading ? <Empty>Loading application status…</Empty> : vehicles.length ? <div className="portal-table-wrap"><table className="portal-table"><thead><tr><th>Reference</th><th>Plate</th><th>Vehicle</th><th>Status</th><th>Staff note</th><th>Submitted</th></tr></thead><tbody>{vehicles.map(vehicle => <tr key={vehicle.id}><td>{vehicle.id.slice(0, 8).toUpperCase()}</td><td><b>{vehicle.plate_number}</b></td><td>{[vehicle.year, vehicle.make, vehicle.model].filter(Boolean).join(' ') || vehicle.vehicle_type}</td><td><Status value={vehicle.verification_status} /></td><td>{vehicle.remarks || (vehicle.verification_status === 'pending' ? 'Waiting for staff review' : '—')}</td><td>{new Date(vehicle.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div> : <Empty>No registrations to track yet. <Link to={`${path}/register`}>Register a vehicle.</Link></Empty>}</>
}

function ViolationTable({ violations, onDispute }) {
  if (!violations.length) return <Empty>No confirmed violations are linked to your verified vehicles.</Empty>
  return <div className="portal-table-wrap"><table className="portal-table"><thead><tr><th>Violation</th><th>Plate</th><th>Recorded</th><th>Zone</th><th>Penalty</th><th>Record</th></tr></thead><tbody>{violations.map(item => <tr key={item.violation_id}><td><b>{displayStatus(item.violation_type)}</b></td><td>{item.plate_number}</td><td>{item.occurred_at ? new Date(item.occurred_at).toLocaleString() : '—'}</td><td>{item.location || '—'}</td><td>{money(item.amount, item.currency)}</td><td>{onDispute ? <button className="portal-link-button" onClick={() => onDispute(item)}>Dispute</button> : <Status value={item.status} />}</td></tr>)}</tbody></table></div>
}

function ViolationsPage() {
  const { user } = usePortal()
  const { data, loading, error, reload } = useRequest('/me/violations', user.id)
  const [selected, setSelected] = useState(null)
  const [reason, setReason] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const submitDispute = async event => {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      await portalRequest('/me/disputes', { method: 'POST', body: { leanbot_id: selected.leanbot_id, violation_type: selected.violation_type, reason } })
      setSelected(null); setReason(''); setMessage('Your dispute was submitted for staff review.'); await reload()
    } catch (cause) { setMessage(cause.message) }
    finally { setBusy(false) }
  }
  return <><PageHeading eyebrow="CONFIRMED RECORDS" title="Violations" detail="Records appear here only when a confirmed plate matches one of your verified vehicles." action={<button className="portal-button portal-button-outline" onClick={reload}>Refresh</button>} />{error && <p className="portal-error">{error}</p>}{loading ? <Empty>Loading violations…</Empty> : <ViolationTable violations={data?.violations || []} onDispute={setSelected} />}{message && <p className={message.startsWith('Your dispute') ? 'portal-success' : 'portal-error'} role="status">{message}</p>}{selected && <div className="portal-dialog-backdrop" role="presentation" onMouseDown={event => event.target === event.currentTarget && setSelected(null)}><section className="portal-dialog" role="dialog" aria-modal="true" aria-labelledby="dispute-title"><h2 id="dispute-title">Dispute {displayStatus(selected.violation_type)}</h2><p>{selected.plate_number} · {selected.violation_id}</p><form className="portal-form" onSubmit={submitDispute}><label>Explain why you believe this record is incorrect<textarea value={reason} onChange={event => setReason(event.target.value)} minLength={10} maxLength={2000} required rows={5} /></label><div className="portal-actions"><button className="portal-button portal-button-green" disabled={busy}>{busy ? 'Submitting…' : 'Submit dispute'}</button><button type="button" className="portal-button portal-button-outline" onClick={() => setSelected(null)}>Cancel</button></div></form></section></div>}</>
}

function PaymentsPage() {
  const { data, loading } = useRequest('/me/payments')
  return <><PageHeading eyebrow="PAYMENT HISTORY" title="Payments" detail="Payment status for your account." />{loading ? <Empty>Loading payment history…</Empty> : data?.payments?.length ? <Empty>Payment entries are available, but online checkout is not configured.</Empty> : <div className="portal-note portal-note-large"><b>Online payments are not enabled</b><p>This portal is connected to the local SQLite database. No payment provider is configured, so it cannot collect or confirm payments.</p></div>}</>
}

function ProfilePage() {
  const { user, setUser } = usePortal()
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const saveProfile = async event => {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    const form = new FormData(event.currentTarget)
    try { const result = await portalRequest('/me/profile', { method: 'PATCH', body: Object.fromEntries(form.entries()) }); setUser(result.user); setMessage('Profile saved.') }
    catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }
  const savePassword = async event => {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    if (form.get('new_password') !== form.get('confirm_password')) { setError('The new passwords do not match.'); setBusy(false); return }
    try { const result = await portalRequest('/me/password', { method: 'POST', body: { current_password: form.get('current_password'), new_password: form.get('new_password') } }); portalToken.set(result.token); setMessage('Password changed. Other sessions were signed out.'); formElement.reset() }
    catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }
  return <><PageHeading eyebrow="ACCOUNT SETTINGS" title="Profile & settings" detail="Update your contact details and password." />{error && <p className="portal-error">{error}</p>}{message && <p className="portal-success" role="status">{message}</p>}<div className="portal-settings-grid"><section className="portal-panel"><h2>Personal details</h2><form className="portal-form" onSubmit={saveProfile}><label>Email<input value={user.email} readOnly /></label><div className="portal-form-row"><label>First name<input name="first_name" defaultValue={user.first_name} required /></label><label>Last name<input name="last_name" defaultValue={user.last_name} required /></label></div><label>Mobile number<input name="phone" type="tel" defaultValue={user.phone || ''} /></label><button className="portal-button portal-button-green" disabled={busy}>Save profile</button></form></section><section className="portal-panel"><h2>Change password</h2><form className="portal-form" onSubmit={savePassword}><label>Current password<input name="current_password" type="password" autoComplete="current-password" required /></label><label>New password<input name="new_password" type="password" minLength={10} autoComplete="new-password" required /></label><label>Confirm new password<input name="confirm_password" type="password" minLength={10} autoComplete="new-password" required /></label><button className="portal-button portal-button-outline" disabled={busy}>Update password</button></form></section></div></>
}

const adminLinks = [['overview', 'Overview'], ['vehicles', 'Vehicle review'], ['unassigned', 'Unassigned violations'], ['disputes', 'Disputes'], ['fines', 'Penalty amounts'], ['payments', 'Payments']]

function AdminLayout() {
  const { user, signOut } = usePortal()
  const navigate = useNavigate()
  const logout = async () => { await signOut(); navigate(path, { replace: true }) }
  return <div className="portal-workspace portal-admin-workspace"><aside className="portal-nav"><Link className="portal-brand" to={path}><span className="portal-brand-mark">V</span><span>VERITAS<small>PORTAL ADMIN</small></span></Link><div className="portal-nav-user"><b>{user.first_name} {user.last_name}</b><small>Administrator</small></div><nav aria-label="Portal administration">{adminLinks.map(([page, label]) => <NavLink key={page} to={`${path}/admin/${page}`} className={({ isActive }) => isActive ? 'active' : ''}>{label}</NavLink>)}<Link to="/dashboard">Traffic dashboard</Link></nav><button className="portal-nav-logout" onClick={logout}>Log out</button></aside><main className="portal-content"><Outlet /></main></div>
}

function AdminVehiclesPage() {
  const { data, loading, error, reload } = useRequest('/admin/vehicles?status=pending')
  const [notes, setNotes] = useState({})
  const [message, setMessage] = useState('')
  const decide = async (vehicle, decision) => {
    setMessage('')
    try {
      await portalRequest(`/admin/vehicles/${encodeURIComponent(vehicle.id)}/decision`, { method: 'POST', body: { decision, remarks: notes[vehicle.id] || '' } })
      setMessage(`${vehicle.plate_number} marked ${decision}.`); await reload()
    } catch (cause) { setMessage(cause.message) }
  }
  const vehicles = data?.vehicles || []
  return <><PageHeading eyebrow="OWNERSHIP REVIEW" title="Vehicle applications" detail="Approve verified ownership or reject an application with a clear reason." action={<button className="portal-button portal-button-outline" onClick={reload}>Refresh</button>} />{error && <p className="portal-error">{error}</p>}{message && <p className={message.includes('marked') ? 'portal-success' : 'portal-error'}>{message}</p>}{loading ? <Empty>Loading applications…</Empty> : vehicles.length ? <div className="portal-card-list">{vehicles.map(vehicle => <article className="portal-panel portal-review-card" key={vehicle.id}><div className="portal-panel-heading"><div><span className="portal-eyebrow">{vehicle.vehicle_type} · {vehicle.id.slice(0, 8)}</span><h2>{vehicle.plate_number}</h2><p>{vehicle.owner_first_name} {vehicle.owner_last_name} · {vehicle.owner_email}{vehicle.owner_phone ? ` · ${vehicle.owner_phone}` : ''}</p></div><Status value={vehicle.verification_status} /></div><div className="portal-detail-grid"><span>Make/model <b>{[vehicle.year, vehicle.make, vehicle.model].filter(Boolean).join(' ') || '—'}</b></span><span>Color <b>{vehicle.color || '—'}</b></span><span>OR number <b>{vehicle.or_number}</b></span><span>CR number <b>{vehicle.cr_number}</b></span><span>Registration expiry <b>{vehicle.registration_expiry || '—'}</b></span></div><label className="portal-label">Rejection note<textarea value={notes[vehicle.id] || ''} onChange={event => setNotes(old => ({ ...old, [vehicle.id]: event.target.value }))} placeholder="Required only when rejecting" rows={2} /></label><div className="portal-actions"><button className="portal-button portal-button-green" onClick={() => decide(vehicle, 'verified')}>Verify ownership</button><button className="portal-button portal-button-danger" onClick={() => decide(vehicle, 'rejected')}>Reject application</button></div></article>)}</div> : <Empty>No vehicle applications are waiting for review.</Empty>}</>
}

function AdminOverviewPage() {
  const vehicles = useRequest('/admin/vehicles?status=pending')
  const violations = useRequest('/admin/unassigned-violations')
  const disputes = useRequest('/admin/disputes')
  const loading = vehicles.loading || violations.loading || disputes.loading
  return <><PageHeading eyebrow="PORTAL ADMINISTRATION" title="Overview" detail="Ownership reviews and traffic records awaiting staff action." /><section className="portal-stat-grid"><article><small>Vehicle applications</small><b>{loading ? '—' : vehicles.data?.vehicles?.length || 0}</b><span>Pending ownership review</span></article><article><small>Unassigned violations</small><b>{loading ? '—' : violations.data?.violations?.length || 0}</b><span>No verified vehicle owner match</span></article><article><small>Driver disputes</small><b>{loading ? '—' : (disputes.data?.disputes || []).filter(item => item.status === 'pending' || item.status === 'under_review').length}</b><span>Need staff review</span></article></section><div className="portal-note"><b>Connected to SQLite</b><p>Portal accounts, vehicle applications, review decisions, and disputes are stored in the server’s veritas.sqlite3 database.</p></div></>
}

function AdminUnassignedPage() {
  const { data, loading, error, reload } = useRequest('/admin/unassigned-violations')
  const items = data?.violations || []
  return <><PageHeading eyebrow="TRAFFIC RECORDS" title="Unassigned violations" detail="Approved Leanbot records without a matching verified driver vehicle." action={<button className="portal-button portal-button-outline" onClick={reload}>Refresh</button>} />{error && <p className="portal-error">{error}</p>}{loading ? <Empty>Loading records…</Empty> : items.length ? <ViolationTable violations={items} /> : <Empty>There are no unassigned violation records.</Empty>}</>
}

function AdminDisputesPage() {
  const { data, loading, error, reload } = useRequest('/admin/disputes')
  const [notes, setNotes] = useState({})
  const [message, setMessage] = useState('')
  const update = async (dispute, status) => {
    setMessage('')
    try { await portalRequest(`/admin/disputes/${encodeURIComponent(dispute.id)}`, { method: 'PATCH', body: { status, staff_note: notes[dispute.id] || '' } }); setMessage('Dispute updated.'); await reload() }
    catch (cause) { setMessage(cause.message) }
  }
  const disputes = data?.disputes || []
  return <><PageHeading eyebrow="DRIVER APPEALS" title="Disputes" detail="Review disputes submitted against records linked to verified vehicles." action={<button className="portal-button portal-button-outline" onClick={reload}>Refresh</button>} />{(error || message) && <p className={message === 'Dispute updated.' ? 'portal-success' : 'portal-error'}>{message || error}</p>}{loading ? <Empty>Loading disputes…</Empty> : disputes.length ? <div className="portal-card-list">{disputes.map(dispute => <article className="portal-panel" key={dispute.id}><div className="portal-panel-heading"><div><span className="portal-eyebrow">{dispute.plate_number || 'Plate unavailable'} · {dispute.violation_type}</span><h2>{dispute.first_name} {dispute.last_name}</h2><p>{dispute.user_email} · {new Date(dispute.created_at).toLocaleString()}</p></div><Status value={dispute.status} /></div><p className="portal-dispute-reason">{dispute.reason}</p><label className="portal-label">Staff note<textarea rows={2} value={notes[dispute.id] ?? dispute.staff_note ?? ''} onChange={event => setNotes(old => ({ ...old, [dispute.id]: event.target.value }))} /></label><div className="portal-actions"><button className="portal-button portal-button-outline" onClick={() => update(dispute, 'under_review')}>Under review</button><button className="portal-button portal-button-green" onClick={() => update(dispute, 'dismissed')}>Dismiss record</button><button className="portal-button portal-button-danger" onClick={() => update(dispute, 'upheld')}>Uphold record</button></div></article>)}</div> : <Empty>No driver disputes are waiting for review.</Empty>}</>
}

function AdminFinesPage() {
  const { data, loading, error, reload } = useRequest('/admin/fines')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [drafts, setDrafts] = useState({})
  const save = async event => {
    event.preventDefault(); setBusy(true); setMessage('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    try { await portalRequest('/admin/fines', { method: 'PUT', body: { violation_type: form.get('violation_type'), amount: form.get('amount'), currency: 'PHP' } }); formElement.reset(); setMessage('Penalty amount saved.'); await reload() }
    catch (cause) { setMessage(cause.message) }
    finally { setBusy(false) }
  }
  const setAmount = async type => {
    try { await portalRequest('/admin/fines', { method: 'PUT', body: { violation_type: type, amount: drafts[type], currency: 'PHP' } }); setMessage('Penalty amount saved.'); await reload() }
    catch (cause) { setMessage(cause.message) }
  }
  return <><PageHeading eyebrow="PENALTY CONFIGURATION" title="Penalty amounts" detail="Amounts are informational; this portal does not collect payments." />{(error || message) && <p className={message.includes('saved') ? 'portal-success' : 'portal-error'}>{message || error}</p>}<section className="portal-panel"><h2>Add a violation amount</h2><form className="portal-form portal-inline-form" onSubmit={save}><label>Violation type<input name="violation_type" placeholder="SPEEDING" required /></label><label>Amount (PHP)<input name="amount" type="number" min="0" step="0.01" required /></label><button className="portal-button portal-button-green" disabled={busy}>Save amount</button></form></section><section className="portal-panel"><div className="portal-panel-heading"><h2>Configured amounts</h2><button className="portal-button portal-button-outline" onClick={reload}>Refresh</button></div>{loading ? <Empty>Loading penalty amounts…</Empty> : data?.fines?.length ? <div className="portal-table-wrap"><table className="portal-table"><thead><tr><th>Violation</th><th>Amount</th><th>Updated</th><th /></tr></thead><tbody>{data.fines.map(fine => <tr key={fine.violation_type}><td>{displayStatus(fine.violation_type)}</td><td><input aria-label={`Penalty for ${fine.violation_type}`} type="number" min="0" step="0.01" value={drafts[fine.violation_type] ?? fine.amount} onChange={event => setDrafts(old => ({ ...old, [fine.violation_type]: event.target.value }))} /></td><td>{fine.updated_at}</td><td><button className="portal-link-button" onClick={() => setAmount(fine.violation_type)}>Save</button></td></tr>)}</tbody></table></div> : <Empty>No amounts configured. Violations remain visible without a penalty amount.</Empty>}</section></>
}

function AdminPaymentsPage() {
  return <><PageHeading eyebrow="PAYMENT ADMINISTRATION" title="Payments" detail="Online payment processing is not configured." /><div className="portal-note portal-note-large"><b>No payment service is connected</b><p>This page does not take payments or create payment records. Connect a payment provider before enabling checkout.</p></div></>
}

export default function PortalApp() {
  return <PortalProvider><div className="driver-portal"><Routes>
    <Route element={<PublicLayout />}>
      <Route index element={<HomePage />} />
      <Route path="login" element={<LoginPage />} />
      <Route path="signup" element={<SignupPage />} />
      <Route path="forgot" element={<ForgotPage />} />
      <Route path="terms" element={<LegalPage title="Terms of use" kind="terms" />} />
      <Route path="privacy" element={<LegalPage title="Privacy information" kind="privacy" />} />
    </Route>
    <Route element={<RequirePortalUser />}><Route element={<DriverLayout />}>
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="vehicles" element={<VehiclesPage />} />
      <Route path="register" element={<RegisterVehiclePage />} />
      <Route path="track" element={<TrackPage />} />
      <Route path="violations" element={<ViolationsPage />} />
      <Route path="payments" element={<PaymentsPage />} />
      <Route path="profile" element={<ProfilePage />} />
    </Route></Route>
    <Route element={<RequirePortalAdmin />}><Route element={<AdminLayout />}>
      <Route path="admin/overview" element={<AdminOverviewPage />} />
      <Route path="admin/vehicles" element={<AdminVehiclesPage />} />
      <Route path="admin/unassigned" element={<AdminUnassignedPage />} />
      <Route path="admin/disputes" element={<AdminDisputesPage />} />
      <Route path="admin/fines" element={<AdminFinesPage />} />
      <Route path="admin/payments" element={<AdminPaymentsPage />} />
    </Route></Route>
    <Route path="*" element={<Navigate to={path} replace />} />
  </Routes></div></PortalProvider>
}
