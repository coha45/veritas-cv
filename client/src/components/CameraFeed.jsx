import Camera from './Camera'

const CameraFeed = ({ frames = {} }) => (
  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
    <Camera cameraId="TOPDOWN" frames={frames} />
    <Camera cameraId="FOOT" frames={frames} />
  </div>
)

export default CameraFeed
