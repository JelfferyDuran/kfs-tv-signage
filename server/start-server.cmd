@echo off
rem KFS Display Server launcher - reads token from .api_token and starts the server
setlocal
cd /d C:\Users\Jayto\tvctl\server
set /p KFS_API_TOKEN=<.api_token
"C:\Users\Jayto\AppData\Local\hermes\tools\python-3.14.7+20260901-win32-x64\python.exe" kfs-display-server.py
