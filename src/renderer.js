const trackBtn = document.getElementById("track-btn")
const trainBtn = document.getElementById("train-btn")

trackBtn.addEventListener("click", _ => {
    console.log("clicked")
    window.electronAPI.onTrack()
})

trainBtn.addEventListener("click", _ => {
    window.electronAPI.openFileDialog()
    //window.location.href = "options.html"
})