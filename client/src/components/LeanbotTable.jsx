import { useState } from 'react'

const apiOrigin = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${window.location.hostname || '127.0.0.1'}:8000`

function formatZone(zone) {
  if (!zone) return 'Outside a zone'
  if (typeof zone === 'string') return zone
  return zone.name || zone.type || 'Zone'
}

function formatSpeed(speed) {
  return typeof speed === 'number' && Number.isFinite(speed)
    ? `${speed.toFixed(1)} cm/s`
    : '—'
}

function formatAngle(angle) {
  // The broker sends Leanbot.angle in radians.
  return typeof angle === 'number' && Number.isFinite(angle)
    ? `${(angle * 180 / Math.PI).toFixed(1)}°`
    : '—'
}

function PlateEvidence({ capture, leanbotId }) {
  const imageUrl = capture?.image_url
    ? new URL(capture.image_url, apiOrigin).toString()
    : null
  const [failedUrl, setFailedUrl] = useState(null)
  const failed = failedUrl === imageUrl

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      {imageUrl && !failed ? (
        <a href={imageUrl} target="_blank" rel="noreferrer" className="block">
          <img
            src={imageUrl}
            alt={`License plate evidence associated with Leanbot ${leanbotId}`}
            className="h-44 w-full object-contain bg-slate-950"
            loading="lazy"
            onError={() => setFailedUrl(imageUrl)}
          />
        </a>
      ) : (
        <div className="flex h-44 flex-col items-center justify-center gap-2 text-center text-sm text-slate-500">
          <span className="text-2xl">▧</span>
          {capture?.image_url ? 'Plate image is unavailable' : 'No plate image linked yet'}
        </div>
      )}
      {capture && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 p-3 text-xs text-slate-600">
          <span>FOOT track</span>
          <span className="text-right font-medium text-slate-800">{capture.plate_track_id ?? '—'}</span>
          <span>Confidence</span>
          <span className="text-right font-medium text-slate-800">
            {typeof capture.confidence === 'number' ? `${(capture.confidence * 100).toFixed(0)}%` : '—'}
          </span>
          <span>Frame</span>
          <span className="text-right font-medium text-slate-800">{capture.frame ?? '—'}</span>
          <span>Capture time</span>
          <span className="text-right font-medium text-slate-800">
            {typeof capture.timestamp === 'number' ? `${capture.timestamp.toFixed(1)} s` : '—'}
          </span>
        </div>
      )}
    </div>
  )
}

function LeanbotCard({ bot, match }) {
  const capture = bot.license_plate_capture
  const hasEvidence = Boolean(capture?.image_url)
  const violations = Array.isArray(bot.violations) ? bot.violations : []

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b border-slate-100 p-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">TOPDOWN track</p>
          <h3 className="mt-1 text-xl font-bold text-slate-900">Leanbot {bot.id}</h3>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${hasEvidence ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}>
          {hasEvidence ? 'Plate evidence linked' : bot.license_plate ? 'Plate detected' : 'No plate evidence'}
        </span>
      </header>

      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-slate-500">Zone</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">{formatZone(bot.current_zone)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Speed</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">{formatSpeed(bot.speed)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Direction</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">{formatAngle(bot.angle)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">FOOT match</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">
            {match ? `Track ${match.foot_track_id}` : 'Not matched'}
          </p>
        </div>
      </div>

      {match && (
        <p className="px-4 pb-3 text-xs text-slate-500">
          FOOT ↔ TOPDOWN distance: {typeof match.distance === 'number' ? `${match.distance.toFixed(1)} px` : '—'}
        </p>
      )}

      <div className="grid gap-4 border-t border-slate-100 p-4 md:grid-cols-[minmax(0,1fr)_minmax(220px,0.85fr)]">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Plate evidence</p>
          <PlateEvidence capture={capture} leanbotId={bot.id} />
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Violations</p>
          {violations.length ? (
            <ul className="flex flex-wrap gap-2">
              {violations.map((violation, index) => (
                <li key={`${violation}-${index}`} className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 ring-1 ring-inset ring-rose-200">
                  {String(violation).replaceAll('_', ' ')}
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500">No violations reported.</p>
          )}
        </div>
      </div>
    </article>
  )
}

export default function LeanbotTable({ data = [], matches = {} }) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Leanbot results</h2>
        <p className="text-sm text-slate-500">Plate captures are linked to the canonical TOPDOWN track when the broker matches both cameras.</p>
      </div>
      {data.length ? (
        <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
          {data.map(bot => (
            <LeanbotCard key={bot.id} bot={bot} match={matches[String(bot.id)]} />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <p className="font-semibold text-slate-700">No Leanbots detected yet</p>
          <p className="mt-1 text-sm text-slate-500">Results will appear here when the TOPDOWN camera sends a state snapshot.</p>
        </div>
      )}
    </section>
  )
}
