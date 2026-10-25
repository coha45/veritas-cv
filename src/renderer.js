const trackBtn = document.getElementById("track-btn")
const trainBtn = document.getElementById("train-btn")

trackBtn.addEventListener("click", e => {
    console.log("clicked")
    window.electronAPI.onTrack()
})


trainBtn.addEventListener("click", e => {
    console.log("clicked2")
    window.electronAPI.onTrain()
})