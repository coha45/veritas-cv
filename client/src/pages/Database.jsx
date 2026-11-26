import { useMemo, useState } from 'react'
import Page from './Page'
import { useVeritas } from '../context/VeritasContext'

const apiOrigin = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${window.location.hostname || '127.0.0.1'}:8000`

function EvidencePreview({ capture, leanbotId }) {
  const [unavailable, setUnavailable] = useState(false)
  const imageUrl = capture?.image_url
    ? new URL(capture.image_url, apiOrigin).toString()
    : null

  if (!imageUrl || unavailable) {
    return (
      <div className="flex h-16 w-24 items-center justify-center rounded-lg bg-slate-100 text-[10px] text-slate-400">
        {imageUrl ? 'Image unavailable' : 'No image'}
      </div>
    )
  }

  return (
    <a href={imageUrl} target="_blank" rel="noreferrer" title={`Open plate evidence for Leanbot ${leanbotId}`}>
      <img
        src={imageUrl}
        alt={`Plate evidence for Leanbot ${leanbotId}`}
        className="h-16 w-24 rounded-lg bg-slate-950 object-contain"
        loading="lazy"
        onError={() => setUnavailable(true)}
      />
    </a>
  )
}

function DecisionBadge({ decision }) {
  const style = decision === 'approved'
    ? 'bg-emerald-100 text-emerald-800'
    : decision === 'rejected'
      ? 'bg-rose-100 text-rose-800'
      : 'bg-amber-100 text-amber-800'

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${style}`}>
      {decision ?? 'Pending'}
    </span>
  )
}

function ApprovalQueue({ leanbots, decisions, onDecision }) {
  if (!leanbots.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <p className="font-semibold text-slate-800">No current detections to review</p>
        <p className="mt-1 text-sm text-slate-500">TOPDOWN Leanbots will appear here while the camera is sending detections.</p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Leanbot</th>
              <th className="px-4 py-3 font-semibold">Plate evidence</th>
              <th className="px-4 py-3 font-semibold">Zone</th>
              <th className="px-4 py-3 font-semibold">Violations</th>
              <th className="px-4 py-3 font-semibold">Review</th>
              <th className="px-4 py-3 font-semibold">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {leanbots.map(bot => {
              const id = String(bot.id)
              const decision = decisions[id]
              const zone = typeof bot.current_zone === 'string'
                ? bot.current_zone
                : bot.current_zone?.name ?? '—'
              const violations = Array.isArray(bot.violations) ? bot.violations : []

              return (
                <tr key={id} className="align-middle">
                  <td className="whitespace-nowrap px-4 py-4 font-semibold text-slate-900">{id}</td>
                  <td className="px-4 py-3">
                    <EvidencePreview capture={bot.license_plate_capture} leanbotId={id} />
                  </td>
                  <td className="px-4 py-4 text-slate-700">{zone}</td>
                  <td className="px-4 py-4">
                    {violations.length
                      ? violations.map(value => String(value).replaceAll('_', ' ')).join(', ')
                      : <span className="text-slate-400">None</span>}
                  </td>
                  <td className="px-4 py-4"><DecisionBadge decision={decision} /></td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className={`btn btn-xs ${decision === 'approved' ? 'btn-success' : 'btn-outline btn-success'}`}
                        aria-pressed={decision === 'approved'}
                        onClick={() => onDecision(id, decision === 'approved' ? null : 'approved')}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className={`btn btn-xs ${decision === 'rejected' ? 'btn-error' : 'btn-outline btn-error'}`}
                        aria-pressed={decision === 'rejected'}
                        onClick={() => onDecision(id, decision === 'rejected' ? null : 'rejected')}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function DatabaseRecords({ records, loading, error, onRefresh }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-2 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-bold text-slate-900">Stored Leanbot records</h3>
          <p className="mt-1 text-sm text-slate-500">Stored Leanbot records.</p>
        </div>
        <div className="flex items-center gap-3">
          {error && <span className="badge badge-outline">Connection error</span>}
          <button type="button" className="btn btn-sm btn-outline" onClick={onRefresh} disabled={loading}>
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>
      {error && <p role="alert" className="px-5 pt-4 text-sm text-rose-700">{error}</p>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Leanbot ID</th>
              <th className="px-4 py-3 font-semibold">Plate</th>
              <th className="px-4 py-3 font-semibold">Last zone</th>
              <th className="px-4 py-3 font-semibold">Approval</th>
              <th className="px-4 py-3 font-semibold">Last seen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {records.length ? records.map((record, index) => (
              <tr key={record.id ?? record.leanbot_id ?? index}>
                <td className="px-4 py-4 font-semibold">{record.leanbot_id ?? record.id ?? '—'}</td>
                <td className="px-4 py-4">{record.plate ?? record.license_plate ?? '—'}</td>
                <td className="px-4 py-4">{record.last_zone ?? record.zone ?? '—'}</td>
                <td className="px-4 py-4">{record.approval ?? record.status ?? '—'}</td>
                <td className="px-4 py-4">{record.last_seen ?? record.timestamp ?? '—'}</td>
              </tr>
            )) : (
              <tr><td colSpan={5} className="px-4 py-12 text-center text-slate-500">
                {loading ? 'Loading database records…' : 'No database records returned.'}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Database() {
  const { leanbots, connected } = useVeritas()
  const [activeView, setActiveView] = useState('approvals')
  const [decisions, setDecisions] = useState({})
  const [records, setRecords] = useState([])
  const [recordsLoading, setRecordsLoading] = useState(false)
  const [recordsError, setRecordsError] = useState('')

  const loadRecords = async () => {
    setRecordsLoading(true)
    setRecordsError('')
    try {
      const response = await fetch(`${apiOrigin}/api/database/leanbots`)
      if (!response.ok) throw new Error(`Database returned HTTP ${response.status}`)
      const payload = await response.json()
      setRecords(Array.isArray(payload.records) ? payload.records : [])
    } catch (error) {
      setRecordsError(`Could not load SQLite records. ${error.message}`)
    } finally {
      setRecordsLoading(false)
    }
  }

  const decisionCounts = useMemo(() => {
    const values = Object.values(decisions)
    return {
      approved: values.filter(value => value === 'approved').length,
      rejected: values.filter(value => value === 'rejected').length,
      pending: leanbots.filter(bot => !decisions[String(bot.id)]).length,
    }
  }, [decisions, leanbots])

  const setDecision = async (id, decision) => {
    try {
      const response = await fetch(`${apiOrigin}/api/database/leanbots/${encodeURIComponent(id)}/approval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval: decision ?? 'pending' }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Approval update failed')
    setDecisions(previous => {
      const next = { ...previous }
      if (decision) next[id] = decision
      else delete next[id]
      return next
    })
      if (activeView === 'records') await loadRecords()
    } catch (error) {
      setRecordsError(error.message)
    }
  }

  return (
    <Page>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-cyan-700">Veritas data workspace</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Database</h1>
            <p className="mt-2 text-sm text-slate-500">Review live detections or browse persistent records.</p>
          </div>
          <span className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${connected ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-600'}`}>
            <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
            {connected ? 'Live detections connected' : 'Waiting for live detections'}
          </span>
        </header>

        <div role="tablist" aria-label="Database sub-dashboards" className="tabs tabs-boxed w-fit bg-slate-100 p-1">
          <button
            type="button"
            role="tab"
            aria-selected={activeView === 'approvals'}
            className={`tab ${activeView === 'approvals' ? 'tab-active bg-white shadow-sm' : ''}`}
            onClick={() => setActiveView('approvals')}
          >
            Leanbot approvals <span className="ml-2 rounded-full bg-slate-200 px-2 py-0.5 text-xs">{leanbots.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeView === 'records'}
            className={`tab ${activeView === 'records' ? 'tab-active bg-white shadow-sm' : ''}`}
            onClick={() => setActiveView('records')}
          >
            Database records
          </button>
        </div>

        {activeView === 'approvals' ? (
          <section className="space-y-4">
            <div className="flex flex-col gap-3 rounded-2xl border border-cyan-100 bg-cyan-50/70 p-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-cyan-950">
                Approval decisions are saved to the local SQLite database.
              </p>
              <div className="flex gap-3 text-xs font-semibold text-slate-600">
                <span>{decisionCounts.pending} pending</span>
                <span className="text-emerald-700">{decisionCounts.approved} approved</span>
                <span className="text-rose-700">{decisionCounts.rejected} rejected</span>
              </div>
            </div>
            <ApprovalQueue leanbots={leanbots} decisions={decisions} onDecision={setDecision} />
          </section>
        ) : (
          <DatabaseRecords records={records} loading={recordsLoading} error={recordsError} onRefresh={loadRecords} />
        )}
      </div>
    </Page>
  )
}
