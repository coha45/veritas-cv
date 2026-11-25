
import React, { useEffect } from 'react'

const Camera = ({ cameraId, frames={} }) => {
  useEffect(() => {
    console.log(frames)
  }, [frames])
  return (
        <div
          key={cameraId}
          className="bg-black text-white p-3.75 rounded-sm"
        >
          <h3 className="mb-3 font-semibold">
            {cameraId} CAMERA
          </h3>

          { frames[cameraId] ? (
            <img
              src={frames[cameraId]}
              alt={`${cameraId} camera`}
              className="w-full block rounded-lg"
            />
          ) : (
            <div className="bg-white h-60 flex justify-center items-center rounded-lg text-black">
              Waiting for camera...
            </div>
          )}
        </div>
  )
}

export default Camera
