import { useState } from 'react'
import Page from './Page'
import LeanbotTable from '../components/LeanbotTable'
import { useVeritas } from '../context/VeritasContext'
import CameraFeed from '../components/CameraFeed'

function StatusPill({ connected }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm">
      <span className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
      {connected ? 'Live connection' : 'Bridge disconnected'}
    </div>
  )
}

const Dashboard = () => {
  const {
    leanbots,
    trafficStates,
    trafficCheckers,
    intersectionZone,
    connected,
    frames,
    footSnapshot,
    setTrafficState
  } = useVeritas()
  const [pendingTrafficChecker, setPendingTrafficChecker] = useState(null)
  const [trafficError, setTrafficError] = useState('')

  const updateTrafficState = async (checkerId, state) => {
    setPendingTrafficChecker(checkerId)
    setTrafficError('')
    try {
      await setTrafficState(checkerId, state)
    } catch (error) {
      setTrafficError(error.message)
    } finally {
      setPendingTrafficChecker(null)
    }
  }

  const capturedCount = leanbots.filter(bot => bot.license_plate_capture?.image_url).length
  const violationCount = leanbots.reduce(
    (total, bot) => total + (Array.isArray(bot.violations) ? bot.violations.length : 0),
    0
  )
  const matches = footSnapshot?.matches ?? {}

  return (
    <Page>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-7">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-cyan-700">Veritas monitoring</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Live operations dashboard</h1>
            <p className="mt-2 text-sm text-slate-500">Camera feeds, detected Leanbots, and linked plate evidence.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill connected={connected} />
          </div>
        </header>

        {trafficError && (
          <p role="alert" className="-mt-5 text-sm text-rose-700">Traffic state update failed: {trafficError}</p>
        )}

        <section className="space-y-3" aria-label="Traffic signal controls">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Road signal controls</h2>
            <p className="text-sm text-slate-500">
              Each controller covers its two approach lanes and checks entry into {intersectionZone ?? 'the intersection'}.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            {trafficCheckers.map(checker => {
              const activeState = trafficStates[checker.id] ?? 'RED'
              const gpioPins = checker.gpio_pins ?? []
              const ledPattern = { RED: '10', GREEN: '01' }[activeState]
              return (
                <article key={checker.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-bold text-slate-900">{checker.label}</h3>
                      <p className="mt-1 text-xs text-slate-500">
                        {checker.approach_zones?.join(' + ')}
                      </p>
                    </div>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                      {activeState}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-slate-500">
                    LED A / LED B: {ledPattern} · BCM GPIO {gpioPins.join(' / ')}
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2" role="group" aria-label={`${checker.label} signal state`}>
                    {['RED', 'GREEN'].map(state => {
                      const isActive = activeState === state
                      const signalColor = state.toLowerCase()
                      return (
                      <button
                        key={state}
                        type="button"
                        className={`traffic-state traffic-state--${signalColor}${isActive ? ' is-active' : ''}`}
                        disabled={!connected || pendingTrafficChecker === checker.id}
                        aria-pressed={isActive}
                        aria-label={`${state} light for ${checker.label}`}
                        onClick={() => updateTrafficState(checker.id, state)}
                      >
                        <span className="traffic-state__lamp" aria-hidden="true" />
                        <span>{pendingTrafficChecker === checker.id ? 'Updating…' : state}</span>
                      </button>
                      )
                    })}
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <section className="grid grid-cols-1 gap-3 sm:grid-cols-3" aria-label="Live summary">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tracked Leanbots</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{leanbots.length}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Plate evidence</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{capturedCount}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recorded violations</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{violationCount}</p>
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Camera feeds</h2>
              <p className="text-sm text-slate-500">Detection overlays are shown in both live views.</p>
            </div>
            <p className="text-xs text-slate-500">
              Latest FOOT associations: {Object.keys(matches).length}
            </p>
          </div>
          <CameraFeed frames={frames} />
        </section>

        <LeanbotTable data={leanbots} matches={matches} />
      </div>
    </Page>
  )
}

export default Dashboard
