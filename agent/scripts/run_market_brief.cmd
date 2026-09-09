@echo off
REM ===================================================================
REM Ban tin thi truong VN - chay tu Windows Task Scheduler.
REM
REM   run_market_brief.cmd morning   -> chay sau 11h30
REM   run_market_brief.cmd close     -> chay sau 15h00
REM
REM Hai buoc, va thu tu nay la co chu y:
REM   1. market_datapack.py keo so that. Neu hom nay khong phai ngay
REM      giao dich, script tra exit 1 va batch DUNG - khong goi Claude,
REM      khong tieu token vao mot ngay nghi.
REM   2. claude -p chay preset vn_market_daily_brief bang 4 subagent
REM      Sonnet, roi dung dashboard.
REM ===================================================================

setlocal
set SESSION=%~1
if "%SESSION%"=="" set SESSION=close

set REPO=C:\Users\VVVZV\MatthewTrading
set PY=%USERPROFILE%\.venv\Scripts\python.exe
set CLAUDE=%APPDATA%\npm\claude.cmd

cd /d "%REPO%"
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%d
set PACK=_market_%TODAY%
set LOG=%REPO%\_market_logs\%TODAY%_%SESSION%.log
if not exist "%REPO%\_market_logs" mkdir "%REPO%\_market_logs"

echo [%date% %time%] === Bat dau %SESSION% === >> "%LOG%"

set PYTHONPATH=%REPO%\agent
"%PY%" agent\scripts\market_datapack.py --session %SESSION% --outdir "%PACK%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] Data pack that bai - co the la ngay nghi. Dung. >> "%LOG%"
  exit /b 1
)

REM So khuyen nghi khong phu thuoc phien giao dich, nhung neu no hong thi
REM the "Tin hieu giao dich" trong - canh bao chu khong dung ca ban tin.
"%PY%" agent\scripts\signal_tracker.py --outdir "%PACK%" >> "%LOG%" 2>&1
if errorlevel 1 echo [%date% %time%] CANH BAO: signal_tracker that bai, the tin hieu se trong. >> "%LOG%"

echo [%date% %time%] Data pack xong, goi Claude... >> "%LOG%"

"%CLAUDE%" -p "Chay preset agent/src/swarm/presets/vn_market_daily_brief.yaml cho data pack %PACK%, session=%SESSION%. Data pack DA DUNG XONG, dung chay lai market_datapack.py. Spawn 4 subagent Sonnet song song (market_action, flow_desk, sector_desk, news_desk) voi dung system_prompt trong preset, doi ca 4 xong, roi tu dong vai editor: kiem mau thuan cheo, ghi %PACK%/narrative.json, chay agent/scripts/market_dashboard.py %PACK% --session %SESSION%, va ghi %PACK%/BRIEF_%SESSION%.md. Bao cao ngan gon ket qua." --permission-mode acceptEdits >> "%LOG%" 2>&1

if errorlevel 1 (
  echo [%date% %time%] Claude tra loi. Xem log tren. >> "%LOG%"
  exit /b 1
)

echo [%date% %time%] === XONG %SESSION% -> %PACK%\BRIEF_%SESSION%.html === >> "%LOG%"
endlocal
