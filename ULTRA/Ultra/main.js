// Main process entry point
const PORT=3000
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { app, BrowserWindow, ipcMain, Menu, Tray } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');


const expressApp = express();
const server = http.createServer(expressApp); // HTTP server based on express
const io = require('socket.io')(server);

let win;
let pythonProcess = null;
let configServer;
let configSocketIO;
let tray = null;
let isQuitting = false;

// Create tray and tray menu
function createTray() {
    tray = new Tray(path.join(__dirname, '../ultra_logo.png'));
    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Show App',
            click: () => {
                win.show();
            }
        },
        {
            label: 'Restart Backend',
            click: () => {
                if (pythonProcess) {
                    pythonProcess.kill('SIGTERM');
                    console.log('py killed');
                    // Wait for the process to be properly killed before starting new one
                    pythonProcess.on('close', () => {
                        pythonProcess = null;
                        startServerAndBackend();
                        console.log('py started');
                    });
                } else {
                    startServerAndBackend();
                    console.log('py started');
                }
            }
        },
        { type: 'separator' },
        {
            label: 'Quit',
            click: () => {
                isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('Ultra');
    tray.setContextMenu(contextMenu);

    // Add click handler to show window
    tray.on('click', () => {
        win.show();
    });
}

// Helper function to get the correct Python command based on the platform
function getPythonCommand() {
    return process.platform === 'win32' ? 'python' : 'python3';
}

function createWindow() {
    win = new BrowserWindow({
        width: 1920,
        height: 1080,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        icon: path.join(__dirname, 'ultra_logo.icns')
    });
    win.loadFile('index.html');

    // Modify the close handler
    win.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            win.hide();
            return false;
        }

        // Only execute cleanup if we're actually quitting
        if (pythonProcess !== null) {
            pythonProcess.kill('SIGTERM');
        }
        if (server !== null) {
            server.close(() => {
                console.log('Server stopped');
            });
        }
    });

    // Add handler for minimize to tray
    win.on('minimize', (event) => {
        event.preventDefault();
        win.hide();
    });
}

function checkApiKeys() {
    try {
        const apiKeysContent = fs.readFileSync(path.join(__dirname, 'apikey.py'), 'utf8');
        return apiKeysContent.includes("empty");
    } catch (error) {
        console.error("Error reading apikey.py:", error);
        return true; // Assume setup is needed if there's an error reading the file
    }
}

// Modified startServerAndBackend function
function startServerAndBackend() {
    const io = require('socket.io')(server, {
        cors: {
            origin: '*',
        },
    });

    function startPython() {
        try {
            const python = spawn(getPythonCommand(), ['-u', path.join(__dirname, 'main.py')]);
            pythonProcess = python;

            python.stdout.on('data', (data) => {
                console.log("Python Output:", data.toString("utf-8"));
                io.emit('pythonOutput', data.toString("utf-8"));
            });

        io.on('connection', (socket) => {
            console.log('Client connected');

            socket.on('user_message', async (data) => {
                if (data.type === 'text_input') {
                    pythonProcess.stdin.write(data.content + '\n');

                }
            });
        });

            python.stderr.on('data', (data) => {
                console.error("Python Error:", data.toString("utf-8"));
                io.emit('pythonError', data.toString("utf-8"));
            });

            python.on('close', (code) => {
                console.log(`Python script exited with code: ${code}`);
                pythonProcess = null;
            });

        } catch (error) {
            console.error("Failed to start Python script:", error);
            pythonProcess = null;
        }
    }

    if (!server.listening) {
        server.listen(PORT, () => {
            console.log(`Server started on http://localhost:${PORT}`);
            if (win && !win.isDestroyed()) {
                win.webContents.send('server-ready');
            }
            // Server has started, now start Python backend if API keys are set
            if (!checkApiKeys()) {
                startPython();
            }
        });
    } else {
        // Server is already running, check if we need to start Python backend
        console.log('Server is already running on port ' + PORT);
        if (!checkApiKeys()) {
            startPython();
        }
    }
}

    expressApp.get('/triggerPython', (req, res) => {
        if (pythonProcess === null) {
            console.log("Attempting to trigger Python script...");

            try {
                const python = spawn(getPythonCommand(), ['-u', path.join(__dirname, 'main.py')]);
                pythonProcess = python;

                python.stdout.on('data', (data) => {
                    console.log("Python Output:", data.toString());
                    io.emit('pythonOutput', data.toString());
                });

                python.stderr.on('data', (data) => {
                    console.error("Python Error:", data.toString());
                });

                python.on('close', (code) => {
                    console.log(`Python script exited with code: ${code}`);
                    pythonProcess = null;
                });

                res.send("Python script triggered");
            } catch (error) {
                console.error("Failed to trigger Python script:", error);
                res.status(500).send("Failed to trigger Python script");
            }
        }
    });


// Make sure the server listens on the specified port
server.listen(PORT, () => {
    console.log(`Server started on http://localhost:${PORT}`);
    if (win && !win.isDestroyed() && win.webContents) {
        win.webContents.send('server-ready');
        // Other code that uses win.webContents
      }
  });


ipcMain.on('start-server-backend', (event) => {
    console.log('Configuration is complete, starting server and backend...');
    startServerAndBackend();
});

app.whenReady().then(() => {
    createWindow();
    createTray();

    if (checkApiKeys()) {
        console.log("API keys are empty, initializing setup screen...");
        win.webContents.on('did-finish-load', () => {
            win.webContents.send('initialize-setup');
        });
    } else {
        console.log("API keys are set, starting server and backend...");
        startServerAndBackend();
    }
});

// Modify the window-all-closed handler
app.on('window-all-closed', (e) => {
    if (process.platform !== 'darwin') {
        if (!isQuitting) {
            e.preventDefault();
        } else {
            app.quit();
        }
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});