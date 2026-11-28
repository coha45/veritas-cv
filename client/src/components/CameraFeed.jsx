import Camera from './Camera'

const CameraFeed = () => (
  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
    <Camera cameraId="TOPDOWN" />
    <Camera cameraId="FOOT" />
  </div>
)

export default CameraFeed
