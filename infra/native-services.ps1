#Requires -Version 5.1
<#
.SYNOPSIS
  Downloads (if needed) and manages native portable infrastructure services for MINOVA.
  PostgreSQL 16, MinIO, Temporal CLI, Keycloak 26 — all on D: drive.
.PARAMETER Action
  start | stop | status | health | download
#>
param(
    [ValidateSet("start","stop","status","health","download")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$ROOT         = "D:\games and stuff\Opus - build"
$TOOLS        = "$ROOT\tools"
$DATA         = "$ROOT\data"
$LOGS         = "$ROOT\logs"
$CACHE        = "$ROOT\cache"
$TMP          = "$ROOT\tmp"

# Service directories
$PG_DIR       = "$TOOLS\pgsql"
$PG_DATA      = "$DATA\pgdata"
$PG_LOG       = "$LOGS\postgres.log"
$MINIO_DIR    = "$TOOLS\minio"
$MINIO_DATA   = "$DATA\minio"
$MINIO_LOG    = "$LOGS\minio.log"
$TEMPORAL_DIR = "$TOOLS\temporal"
$TEMPORAL_LOG = "$LOGS\temporal.log"
$KC_DIR       = "$TOOLS\keycloak"
$KC_LOG       = "$LOGS\keycloak.log"
$JDK_DIR      = "$TOOLS\jdk17"

# Credentials (dev only)
$PG_SUPERUSER = "minova_admin"
$PG_PASSWORD  = "minova_dev_2026"
$MINIO_USER   = "minova_minio"
$MINIO_PASS   = "minova_minio_2026"
$KC_ADMIN     = "admin"
$KC_PASS      = "admin"

# Ports
$PG_PORT      = 5432
$MINIO_PORT   = 9000
$MINIO_CONSOLE= 9001
$TEMPORAL_PORT= 7233
$TEMPORAL_UI  = 8233
$KC_PORT      = 8081

# ─── Download URLs ───────────────────────────────────────────────────────────
# PostgreSQL 16 portable (EDB zip - Windows x64)
$PG_URL       = "https://get.enterprisedb.com/postgresql/postgresql-16.9-1-windows-x64-binaries.zip"
# MinIO server (standalone exe)
$MINIO_URL    = "https://dl.min.io/server/minio/release/windows-amd64/minio.exe"
# MinIO client
$MC_URL       = "https://dl.min.io/client/mc/release/windows-amd64/mc.exe"
# Temporal CLI (single binary)
$TEMPORAL_URL = "https://temporal.download/cli/archive/latest?platform=windows&arch=amd64"
# Keycloak 26 (standalone zip)
$KC_URL       = "https://github.com/keycloak/keycloak/releases/download/26.0.7/keycloak-26.0.7.zip"

# ─── Helpers ─────────────────────────────────────────────────────────────────

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null }
}

function Download-File([string]$Url, [string]$Dest) {
    if (Test-Path $Dest) {
        Write-Host "  Already exists: $Dest" -ForegroundColor DarkGray
        return
    }
    Write-Host "  Downloading: $Url" -ForegroundColor Cyan
    Write-Host "  -> $Dest"
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing -MaximumRedirection 10
}

function Test-Port([int]$Port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-ForPort([int]$Port, [int]$TimeoutSec = 60, [string]$Label = "") {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    Write-Host "  Waiting for port $Port ($Label)..." -NoNewline
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $Port) {
            Write-Host " UP" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 2
        Write-Host "." -NoNewline
    }
    Write-Host " TIMEOUT" -ForegroundColor Red
    return $false
}

# ─── DOWNLOAD ────────────────────────────────────────────────────────────────

function Download-All {
    Ensure-Dir $TMP
    Ensure-Dir $TOOLS

    # PostgreSQL
    if (-not (Test-Path "$PG_DIR\bin\pg_ctl.exe")) {
        Write-Host "`n[PostgreSQL 16] Downloading..." -ForegroundColor Yellow
        $pgZip = "$TMP\postgresql-16-win64.zip"
        Download-File $PG_URL $pgZip
        Write-Host "  Extracting..."
        Expand-Archive -Path $pgZip -DestinationPath $TOOLS -Force
        # The zip extracts to pgsql/ already
        if (-not (Test-Path "$PG_DIR\bin\pg_ctl.exe")) {
            $inner = Get-ChildItem "$TOOLS\postgresql-*" -Directory | Select-Object -First 1
            if ($inner) { Rename-Item $inner.FullName $PG_DIR }
        }
        Write-Host "  PostgreSQL extracted to $PG_DIR" -ForegroundColor Green
    } else {
        Write-Host "[PostgreSQL 16] Already installed." -ForegroundColor DarkGray
    }

    # MinIO
    Ensure-Dir $MINIO_DIR
    if (-not (Test-Path "$MINIO_DIR\minio.exe")) {
        Write-Host "`n[MinIO] Downloading server..." -ForegroundColor Yellow
        Download-File $MINIO_URL "$MINIO_DIR\minio.exe"
    } else {
        Write-Host "[MinIO] Server already installed." -ForegroundColor DarkGray
    }
    if (-not (Test-Path "$MINIO_DIR\mc.exe")) {
        Write-Host "[MinIO] Downloading client (mc)..." -ForegroundColor Yellow
        Download-File $MC_URL "$MINIO_DIR\mc.exe"
    }

    # Temporal CLI
    Ensure-Dir $TEMPORAL_DIR
    if (-not (Test-Path "$TEMPORAL_DIR\temporal.exe")) {
        Write-Host "`n[Temporal] Downloading CLI..." -ForegroundColor Yellow
        $tempZip = "$TMP\temporal-cli.zip"
        Download-File $TEMPORAL_URL $tempZip
        try {
            Expand-Archive -Path $tempZip -DestinationPath $TEMPORAL_DIR -Force
        } catch {
            # Might be a tar.gz or direct exe
            Write-Host "  Archive extraction failed, trying as direct binary..." -ForegroundColor Yellow
            Copy-Item $tempZip "$TEMPORAL_DIR\temporal.exe" -Force
        }
        # Flatten if nested
        $exe = Get-ChildItem $TEMPORAL_DIR -Recurse -Filter "temporal.exe" | Select-Object -First 1
        if ($exe -and $exe.DirectoryName -ne $TEMPORAL_DIR) {
            Move-Item $exe.FullName "$TEMPORAL_DIR\temporal.exe" -Force
        }
        Write-Host "  Temporal CLI installed." -ForegroundColor Green
    } else {
        Write-Host "[Temporal] CLI already installed." -ForegroundColor DarkGray
    }

    # Keycloak
    if (-not (Test-Path "$KC_DIR\bin\kc.bat")) {
        Write-Host "`n[Keycloak 26] Downloading..." -ForegroundColor Yellow
        $kcZip = "$TMP\keycloak-26.zip"
        Download-File $KC_URL $kcZip
        Write-Host "  Extracting..."
        Expand-Archive -Path $kcZip -DestinationPath $TOOLS -Force
        $inner = Get-ChildItem "$TOOLS\keycloak-*" -Directory | Select-Object -First 1
        if ($inner -and $inner.Name -ne "keycloak") {
            if (Test-Path $KC_DIR) { Remove-Item $KC_DIR -Recurse -Force }
            Rename-Item $inner.FullName $KC_DIR
        }
        Write-Host "  Keycloak extracted to $KC_DIR" -ForegroundColor Green
    } else {
        Write-Host "[Keycloak 26] Already installed." -ForegroundColor DarkGray
    }

    Write-Host "`nAll downloads complete." -ForegroundColor Green
}

# ─── START ───────────────────────────────────────────────────────────────────

function Start-Postgres {
    Write-Host "`n[PostgreSQL] Starting..." -ForegroundColor Yellow
    $pgctl = "$PG_DIR\bin\pg_ctl.exe"
    $initdb = "$PG_DIR\bin\initdb.exe"
    $psql = "$PG_DIR\bin\psql.exe"

    if (-not (Test-Path $pgctl)) {
        Write-Host "  ERROR: pg_ctl not found at $pgctl" -ForegroundColor Red
        return $false
    }

    # Initialize data directory if needed
    if (-not (Test-Path "$PG_DATA\PG_VERSION")) {
        Write-Host "  Initializing database cluster..."
        Ensure-Dir $PG_DATA
        $env:PGPASSWORD = $PG_PASSWORD
        & $initdb -D $PG_DATA -U $PG_SUPERUSER -E UTF8 --locale=en_US.UTF-8 -A md5 --pwfile=<(echo $PG_PASSWORD) 2>&1
        if ($LASTEXITCODE -ne 0) {
            # pwfile via process substitution not available; write temp file
            $pwFile = "$TMP\pg_pw.tmp"
            Set-Content $pwFile $PG_PASSWORD -NoNewline
            & $initdb -D $PG_DATA -U $PG_SUPERUSER -E UTF8 -A md5 --pwfile=$pwFile 2>&1
            Remove-Item $pwFile -Force -ErrorAction SilentlyContinue
        }
    }

    # Configure for pgvector/postgis if not already
    $pgConf = "$PG_DATA\postgresql.conf"
    if (Test-Path $pgConf) {
        $content = Get-Content $pgConf -Raw
        if ($content -notmatch "port\s*=\s*$PG_PORT") {
            Add-Content $pgConf "`nport = $PG_PORT"
        }
        if ($content -notmatch "listen_addresses") {
            Add-Content $pgConf "`nlisten_addresses = 'localhost'"
        }
    }

    # Start
    if (Test-Port $PG_PORT) {
        Write-Host "  PostgreSQL already running on port $PG_PORT" -ForegroundColor DarkGray
    } else {
        & $pgctl -D $PG_DATA -l $PG_LOG start 2>&1
        Wait-ForPort $PG_PORT 30 "PostgreSQL"
    }

    # Create minova database if needed
    $env:PGPASSWORD = $PG_PASSWORD
    $dbExists = & $psql -h localhost -p $PG_PORT -U $PG_SUPERUSER -tAc "SELECT 1 FROM pg_database WHERE datname='minova'" postgres 2>&1
    if ($dbExists -ne "1") {
        Write-Host "  Creating 'minova' database..."
        & $psql -h localhost -p $PG_PORT -U $PG_SUPERUSER -c "CREATE DATABASE minova" postgres 2>&1
    }

    # Run init SQL
    $initSql = "$ROOT\minova\infra\postgres\init.sql"
    if (Test-Path $initSql) {
        Write-Host "  Running init.sql..."
        & $psql -h localhost -p $PG_PORT -U $PG_SUPERUSER -d minova -f $initSql 2>&1 | Out-Null
    }

    return $true
}

function Start-MinIO {
    Write-Host "`n[MinIO] Starting..." -ForegroundColor Yellow
    Ensure-Dir $MINIO_DATA

    if (Test-Port $MINIO_PORT) {
        Write-Host "  MinIO already running on port $MINIO_PORT" -ForegroundColor DarkGray
        return $true
    }

    $env:MINIO_ROOT_USER = $MINIO_USER
    $env:MINIO_ROOT_PASSWORD = $MINIO_PASS

    Start-Process -FilePath "$MINIO_DIR\minio.exe" `
        -ArgumentList "server", $MINIO_DATA, "--address", ":$MINIO_PORT", "--console-address", ":$MINIO_CONSOLE" `
        -RedirectStandardOutput $MINIO_LOG -RedirectStandardError "$LOGS\minio-err.log" `
        -NoNewWindow:$false -WindowStyle Hidden

    if (Wait-ForPort $MINIO_PORT 30 "MinIO") {
        # Bootstrap buckets
        Start-Sleep -Seconds 2
        $mc = "$MINIO_DIR\mc.exe"
        if (Test-Path $mc) {
            & $mc alias set minova "http://localhost:$MINIO_PORT" $MINIO_USER $MINIO_PASS --api S3v4 2>&1 | Out-Null
            foreach ($bucket in @("documents","attachments","exports","reports")) {
                & $mc mb --ignore-existing "minova/$bucket" 2>&1 | Out-Null
            }
            & $mc version enable "minova/documents" 2>&1 | Out-Null
            & $mc version enable "minova/attachments" 2>&1 | Out-Null
            Write-Host "  Buckets created." -ForegroundColor Green
        }
        return $true
    }
    return $false
}

function Start-Temporal {
    Write-Host "`n[Temporal] Starting dev server..." -ForegroundColor Yellow
    Ensure-Dir "$DATA\temporal"

    if (Test-Port $TEMPORAL_PORT) {
        Write-Host "  Temporal already running on port $TEMPORAL_PORT" -ForegroundColor DarkGray
        return $true
    }

    $temporalExe = "$TEMPORAL_DIR\temporal.exe"
    if (-not (Test-Path $temporalExe)) {
        Write-Host "  ERROR: temporal.exe not found" -ForegroundColor Red
        return $false
    }

    Start-Process -FilePath $temporalExe `
        -ArgumentList "server", "start-dev",
            "--port", "$TEMPORAL_PORT",
            "--ui-port", "$TEMPORAL_UI",
            "--db-filename", "$DATA\temporal\default.db",
            "--namespace", "minova",
            "--log-level", "warn" `
        -RedirectStandardOutput $TEMPORAL_LOG -RedirectStandardError "$LOGS\temporal-err.log" `
        -NoNewWindow:$false -WindowStyle Hidden

    return (Wait-ForPort $TEMPORAL_PORT 30 "Temporal")
}

function Start-Keycloak {
    Write-Host "`n[Keycloak] Starting..." -ForegroundColor Yellow

    if (Test-Port $KC_PORT) {
        Write-Host "  Keycloak already running on port $KC_PORT" -ForegroundColor DarkGray
        return $true
    }

    $kcBat = "$KC_DIR\bin\kc.bat"
    if (-not (Test-Path $kcBat)) {
        Write-Host "  ERROR: kc.bat not found at $kcBat" -ForegroundColor Red
        return $false
    }

    $env:JAVA_HOME = $JDK_DIR
    $env:KEYCLOAK_ADMIN = $KC_ADMIN
    $env:KEYCLOAK_ADMIN_PASSWORD = $KC_PASS

    # Copy realm JSON for import
    $realmSrc = "$ROOT\minova\infra\keycloak\minova-realm.json"
    $realmDst = "$KC_DIR\data\import\minova-realm.json"
    Ensure-Dir (Split-Path $realmDst)
    Copy-Item $realmSrc $realmDst -Force

    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", "set JAVA_HOME=$JDK_DIR && `"$kcBat`" start-dev --http-port=$KC_PORT --import-realm > `"$KC_LOG`" 2>&1" `
        -NoNewWindow:$false -WindowStyle Hidden

    return (Wait-ForPort $KC_PORT 90 "Keycloak")
}

# ─── STOP ────────────────────────────────────────────────────────────────────

function Stop-All {
    Write-Host "Stopping all MINOVA services..." -ForegroundColor Yellow

    # PostgreSQL
    $pgctl = "$PG_DIR\bin\pg_ctl.exe"
    if ((Test-Path $pgctl) -and (Test-Port $PG_PORT)) {
        Write-Host "  Stopping PostgreSQL..."
        & $pgctl -D $PG_DATA stop -m fast 2>&1 | Out-Null
    }

    # MinIO
    Get-Process -Name "minio" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "  MinIO stopped."

    # Temporal
    Get-Process -Name "temporal" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "  Temporal stopped."

    # Keycloak (Java process)
    # Keycloak runs as java.exe; identify by port or command line
    $javaProcs = Get-CimInstance Win32_Process -Filter "Name='java.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $javaProcs) {
        if ($p.CommandLine -match "keycloak|kc\.") {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "  Keycloak stopped (PID $($p.ProcessId))."
        }
    }

    Write-Host "All services stopped." -ForegroundColor Green
}

# ─── STATUS / HEALTH ─────────────────────────────────────────────────────────

function Show-Status {
    Write-Host "`n=== MINOVA Service Status ===" -ForegroundColor Cyan
    $services = @(
        @{Name="PostgreSQL"; Port=$PG_PORT},
        @{Name="MinIO API"; Port=$MINIO_PORT},
        @{Name="MinIO Console"; Port=$MINIO_CONSOLE},
        @{Name="Temporal"; Port=$TEMPORAL_PORT},
        @{Name="Temporal UI"; Port=$TEMPORAL_UI},
        @{Name="Keycloak"; Port=$KC_PORT}
    )
    foreach ($svc in $services) {
        $up = Test-Port $svc.Port
        $icon = if ($up) { "[OK]" } else { "[--]" }
        $color = if ($up) { "Green" } else { "Red" }
        Write-Host ("  {0,-18} port {1,5}  {2}" -f $svc.Name, $svc.Port, $icon) -ForegroundColor $color
    }
}

# ─── MAIN ────────────────────────────────────────────────────────────────────

Ensure-Dir $DATA
Ensure-Dir $LOGS
Ensure-Dir $TMP

switch ($Action) {
    "download" {
        Download-All
    }
    "start" {
        Download-All
        Start-Postgres
        Start-MinIO
        Start-Temporal
        Start-Keycloak
        Show-Status
    }
    "stop" {
        Stop-All
    }
    "status" {
        Show-Status
    }
    "health" {
        Show-Status
        # Deep health checks
        Write-Host "`n=== Deep Health Checks ===" -ForegroundColor Cyan
        $psql = "$PG_DIR\bin\psql.exe"
        if (Test-Path $psql) {
            $env:PGPASSWORD = $PG_PASSWORD
            $ver = & $psql -h localhost -p $PG_PORT -U $PG_SUPERUSER -tAc "SELECT version()" minova 2>&1
            Write-Host "  Postgres: $ver"
            $ext = & $psql -h localhost -p $PG_PORT -U $PG_SUPERUSER -tAc "SELECT extname FROM pg_extension ORDER BY 1" minova 2>&1
            Write-Host "  Extensions: $ext"
        }
    }
}
