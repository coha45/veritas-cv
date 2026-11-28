import { useMemo } from 'react'
import Page from './Page'
import Camera from '../components/Camera'
import { useVeritas } from '../context/VeritasContext'

function zoneName(zone) {
  if (!zone) return 'Outside a zone'
  if (typeof zone === 'string') return zone
  return zone.name || zone.type || 'Unknown zone'
}

function StatCard({ label, value, detail }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
      {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </article>
  )
}

export default function TopDown() {
  const { leanbots, connected, intersectionZone } = useVeritas()
  const stats = useMemo(() => {
    const violations = leanbots.flatMap(bot => Array.isArray(bot.violations) ? bot.violations : [])
    const speeds = leanbots.map(bot => bot.speed).filter(speed => Number.isFinite(speed) && speed >= 0)
    const inIntersection = leanbots.filter(bot => zoneName(bot.current_zone) === intersectionZone).length
    const plates = leanbots.filter(bot => bot.license_plate_capture?.image_url).length
    const byType = violations.reduce((counts, violation) => {
      counts[violation] = (counts[violation] || 0) + 1
      return counts
    }, {})

    return {
      violations,
      averageSpeed: speeds.length ? speeds.reduce((sum, speed) => sum + speed, 0) / speeds.length : null,
      inIntersection,
      plates,
      byType,
    }
  }, [leanbots, intersectionZone])

  return (
    <Page>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-cyan-700">Camera analytics</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Top-Down View</h1>
            <p className="mt-2 text-sm text-slate-500">Live TOPDOWN stream and current detection statistics.</p>
          </div>
          <span className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${connected ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-600'}`}>
            <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
            {connected ? 'Detection data connected' : 'Waiting for detection data'}
          </span>
        </header>

        <Camera cameraId="TOPDOWN" />

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Top-down detection statistics">
          <StatCard label="Tracked Leanbots" value={leanbots.length} />
          <StatCard label="In intersection" value={stats.inIntersection} detail={intersectionZone} />
          <StatCard label="Violations" value={stats.violations.length} detail={`${Object.keys(stats.byType).length} violation types`} />
          <StatCard label="Average speed" value={stats.averageSpeed === null ? '—' : `${stats.averageSpeed.toFixed(1)} cm/s`} detail={`${stats.plates} with plate evidence`} />
        </section>

        <section className="space-y-3" aria-label="Current Leanbot detections">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Current detections</h2>
            <p className="text-sm text-slate-500">Live Leanbot tracks, zones, speeds, and triggered violations.</p>
          </div>
          {leanbots.length ? (
            <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
              <table className="w-full min-w-[600px] border-collapse text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Leanbot</th>
                    <th className="px-4 py-3 font-semibold">Current zone</th>
                    <th className="px-4 py-3 font-semibold">Speed</th>
                    <th className="px-4 py-3 font-semibold">Violations</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {leanbots.map(bot => (
                    <tr key={bot.id}>
                      <td className="px-4 py-3 font-semibold text-slate-900">{bot.id}</td>
                      <td className="px-4 py-3 text-slate-700">{zoneName(bot.current_zone)}</td>
                      <td className="px-4 py-3 text-slate-700">{Number.isFinite(bot.speed) ? `${bot.speed.toFixed(1)} cm/s` : '—'}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {bot.violations?.length ? bot.violations.map(value => String(value).replaceAll('_', ' ')).join(', ') : 'None'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
              No Leanbot detections yet. They will appear when the TOPDOWN worker sends a state snapshot.
            </div>
          )}
        </section>

        {Object.keys(stats.byType).length > 0 && (
          <section className="space-y-3" aria-label="Violation statistics">
            <h2 className="text-xl font-bold text-slate-900">Violations by type</h2>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.byType).map(([type, count]) => (
                <span key={type} className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700">
                  {type.replaceAll('_', ' ')} · {count}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>
    </Page>
  )
}
