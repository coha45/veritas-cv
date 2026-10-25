const { app, BrowserWindow, ipcMain : ipc } = require("electron")
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
