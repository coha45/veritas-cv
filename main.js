const { app, BrowserWindow, ipcMain : ipc, dialog } = require("electron")
const { spawn } = require("child_process")
const path = require("path")

let status = "idle"

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

ipc.on("train", (event) => {
        
})

ipc.on("track", (event) => {
    console.log("trakcing")
})

ipc.handle("status:get", (event, arg) => {
    return status
})

ipc.handle("gather", async (event, config) => {
    const { outDir, captureDevice, captureTime, interval } = config
    let progName = null
    let args = []

    if(app.isPackaged) {
        progName = "veritascli.exe"
        args = ["gather", "-o", outDir, "-cd", captureDevice, "-t", captureTime, "-i", interval]
    } else {
        progName = "python"
        args = ["veritascli.py", "gather", "-o", outDir, "-cd", captureDevice, "-t", captureTime, "-i", interval]
    }
    const child = spawn(progName, args)
    child.stdout.on("data", (data) => {
        status = data.toString().trim()
    })
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
