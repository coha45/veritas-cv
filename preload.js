const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("electronAPI", {
    onTrain : () => ipcRenderer.send("train"),
    onTrack : () => ipcRenderer.send("track")
})