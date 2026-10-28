@echo off
rem Chay mst_crawler tren Windows ma khong can PATH: run.bat discover | crawl | stats | dashboard | export
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=py"
"%PY%" -m mst_crawler %*
