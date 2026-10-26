const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("electronAPI", {
    onTrain : () => ipcRenderer.send("train"),
    onTrack : () => ipcRenderer.send("track"),
    onGather : (config) => ipcRenderer.invoke("gather", config),
    openFileDialog : () => ipcRenderer.invoke("dialog:openFile"),
    getStatus : () => ipcRenderer.invoke("status:get")
})