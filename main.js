const { app, BrowserWindow, ipcMain : ipc, dialog } = require("electron")
const { spawn } = require("child_process")
const path = require("path")

const createWindow = () => {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences : {
            preload : path.join(__dirname, "preload.js")
        }
    })

    win.loadFile("./src/index.html")
}

app.whenReady().then(() => {
    createWindow()
    app.on("activate", () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
})

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit()
})

ipc.on("train", (event, arg) => {
    
})

ipc.on("track", (event, arg) => {
    console.log("trakcing")
})

ipc.handle("gather", async (event, config) => {
    console.log(config)
    const { outDir, captureDevice, captureTime, interval } = config
    spawn("veritascli", ["gather", "-o", outDir, "-cd", captureDevice, "-t", captureTime, "-i", interval])
})

ipc.handle("dialog:openFile", async () => {
    const result = await dialog.showOpenDialog({
        title : "Select A Folder",
        properties : ["openDirectory"]
    })

    if (result.canceled) {
        return null
    } else {
        console.log(result.filePaths)
        return result.filePaths
    }
})
