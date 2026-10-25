const outDir = document.getElementById("outdir")
const captureDevice = document.getElementById("capture-device")
const captureTime = document.getElementById("time")
const interval = document.getElementById("interval")

const gatherConfig = document.getElementById("gather-options")

outDir.addEventListener("click", _ => {
    const dir = window.electronAPI.openFileDialog()
    dir.then(data => outDir.innerText = data).catch(err => console.error(err))
    console.log(dir)
})

gatherConfig.onsubmit = e => {
    e.preventDefault()
}


