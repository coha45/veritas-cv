import React from 'react'
import Camera from './Camera'
import { useVeritas } from '../context/VeritasContext'

const CameraFeed = () => {
  const {
    frames
  } = useVeritas()

  return (
    <div className="grid grid-cols-2 gap-5">
      <Camera cameraId="TOPDOWN" frames={frames} />
      <Camera cameraId="FOOT" frames={frames} />  
    </div>
  )
}

export default CameraFeed