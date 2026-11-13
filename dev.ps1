# Starts TailorMade locally: the API (port 7071) and the frontend (port 5173),
# each in its own window, then opens the app in your browser.
#
# Run from anywhere:  .\dev.ps1
# To stop: close the two windows (or press Ctrl+C in each).

$root = $PSScriptRoot

# 1. Close anything left over on our ports so we never get "address already in use"
foreach ($port in 7071, 5173) {
    netstat -ano | Select-String ":$port " | Select-String "LISTENING" | ForEach-Object {
        $procId = [int](($_.Line.Trim() -split '\s+')[-1])
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Stopping old $($proc.ProcessName) on port $port (PID $procId)"
            Stop-Process -Id $procId -Force
        }
    }
}

# 2. API window: runs inside api\ with its virtual environment
$apiCommand = "Set-Location '$root\api'; & '.\.venv\Scripts\Activate.ps1'; func start"
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $apiCommand

# 3. Frontend window: runs inside frontend\
$webCommand = "Set-Location '$root\frontend'; npm run dev"
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $webCommand

# 4. Wait until both answer, then open the browser
Write-Host "Waiting for the API and frontend to start..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        Invoke-WebRequest 'http://localhost:5173/api/health' -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ready) {
    Write-Host "Ready: http://localhost:5173"
    Start-Process 'http://localhost:5173'
} else {
    Write-Host "Not ready after 60 seconds. Check the two server windows for errors."
}
