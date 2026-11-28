import { useEffect, useRef, useState } from 'react'

const apiOrigin = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${window.location.hostname || '127.0.0.1'}:8000`

function waitForIce(pc) {
  if (pc.iceGatheringState === 'complete') return Promise.resolve()
  return new Promise(resolve => {
    const timeout = window.setTimeout(done, 8000)
    function done() {
      window.clearTimeout(timeout)
      pc.removeEventListener('icegatheringstatechange', check)
      resolve()
    }
    function check() {
      if (pc.iceGatheringState === 'complete') done()
    }
    pc.addEventListener('icegatheringstatechange', check)
  })
}

const Camera = ({ cameraId }) => {
  const videoRef = useRef(null)
  const [status, setStatus] = useState('Connecting')

  useEffect(() => {
    const pc = new RTCPeerConnection({ iceServers: [] })
    const videoElement = videoRef.current
    let active = true
    pc.addTransceiver('video', { direction: 'recvonly' })
    pc.ontrack = event => {
      if (!active || !videoElement) return
      videoElement.srcObject = event.streams[0]
      setStatus('Receiving WebRTC video')
    }
    pc.onconnectionstatechange = () => {
      if (!active) return
      if (pc.connectionState === 'failed') setStatus('WebRTC connection failed')
      else if (pc.connectionState === 'disconnected') setStatus('Video disconnected')
    }

    const connect = async () => {
      try {
        const offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await waitForIce(pc)
        const response = await fetch(`${apiOrigin}/api/webrtc/offer`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ camera_id: cameraId, sdp: pc.localDescription.sdp, type: pc.localDescription.type }),
        })
        const answer = await response.json()
        if (!response.ok) throw new Error(answer.detail || `HTTP ${response.status}`)
        await pc.setRemoteDescription(answer)
      } catch (error) {
        if (active) setStatus(`WebRTC unavailable: ${error.message}`)
      }
    }

    connect()
    return () => {
      active = false
      pc.close()
      if (videoElement) videoElement.srcObject = null
    }
  }, [cameraId])

  const receiving = status === 'Receiving WebRTC video'
  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 shadow-sm">
      <header className="flex items-center justify-between px-4 py-3 text-white">
        <h3 className="text-sm font-bold tracking-wide">{cameraId} CAMERA</h3>
        <span className={`inline-flex items-center gap-2 text-xs font-medium ${receiving ? 'text-emerald-300' : 'text-slate-400'}`}>
          <span className={`h-2 w-2 rounded-full ${receiving ? 'bg-emerald-400' : 'bg-slate-500'}`} />
          {status}
        </span>
      </header>
      <div className="flex aspect-video items-center justify-center bg-slate-900">
        <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-contain" />
      </div>
    </article>
  )
}

export default Camera
