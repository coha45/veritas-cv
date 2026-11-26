const Camera = ({ cameraId, frames = {} }) => {
  const frame = frames[cameraId]

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 shadow-sm">
      <header className="flex items-center justify-between px-4 py-3 text-white">
        <h3 className="text-sm font-bold tracking-wide">{cameraId} CAMERA</h3>
        <span className={`inline-flex items-center gap-2 text-xs font-medium ${frame ? 'text-emerald-300' : 'text-slate-400'}`}>
          <span className={`h-2 w-2 rounded-full ${frame ? 'bg-emerald-400' : 'bg-slate-500'}`} />
          {frame ? 'Receiving video' : 'Waiting for video'}
        </span>
      </header>
      <div className="flex aspect-video items-center justify-center bg-slate-900">
        {frame ? (
          <img
            src={frame}
            alt={`${cameraId} camera with detection overlays`}
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="px-5 text-center text-sm text-slate-400">
            <div className="mb-2 text-2xl">◉</div>
            Waiting for {cameraId.toLowerCase()} camera frames…
          </div>
        )}
      </div>
    </article>
  )
}

export default Camera
