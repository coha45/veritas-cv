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
    trafficState,
    connected,
    frames,
    footSnapshot,
    setTrafficState
  } = useVeritas()
  const [pendingTrafficState, setPendingTrafficState] = useState(null)
  const [trafficError, setTrafficError] = useState('')

  const updateTrafficState = async (state) => {
    setPendingTrafficState(state)
    setTrafficError('')
    try {
      await setTrafficState(state)
    } catch (error) {
      setTrafficError(error.message)
    } finally {
      setPendingTrafficState(null)
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
            <div className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 shadow-sm">
              Traffic: <span className="font-semibold text-slate-900">{trafficState ?? 'Unknown'}</span>
            </div>
            <div className="join" role="group" aria-label="Set traffic state">
              {['RED', 'YELLOW', 'GREEN'].map(state => (
                <button
                  key={state}
                  type="button"
                  className={`join-item btn btn-sm ${trafficState === state ? 'btn-neutral' : 'btn-outline'}`}
                  disabled={!connected || pendingTrafficState !== null}
                  aria-pressed={trafficState === state}
                  onClick={() => updateTrafficState(state)}
                >
                  {pendingTrafficState === state ? 'Setting…' : state}
                </button>
              ))}
            </div>
          </div>
        </header>

        {trafficError && (
          <p role="alert" className="-mt-5 text-sm text-rose-700">Traffic state update failed: {trafficError}</p>
        )}

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
