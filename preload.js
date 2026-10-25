const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("electronAPI", {
    onTrain : () => ipcRenderer.send("train"),
    onTrack : () => ipcRenderer.send("track"),
    openFileDialog : () => ipcRenderer.invoke("dialog:openFile")
})