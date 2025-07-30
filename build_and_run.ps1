# ATeam Development Server
# This script sets up dependencies and runs a single development server

Write-Host "🚀 Starting ATeam Multi-Agent System..." -ForegroundColor Green

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -InformationLevel Quiet
        return $connection.TcpTestSucceeded
    } catch {
        return $false
    }
}

# Check if port is available
$backendPort = 8000

if (Test-Port -Port $backendPort) {
    Write-Host "⚠️  Port $backendPort is already in use. Server may already be running." -ForegroundColor Yellow
}

# Check Python dependencies
Write-Host "🐍 Checking Python dependencies..." -ForegroundColor Yellow
try {
    $pythonResult = python -c "import fastapi, uvicorn, websockets, pydantic, jinja2, markdown, httpx, yaml, llm, psutil; print('All Python dependencies available')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Missing Python dependencies. Installing..." -ForegroundColor Red
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to install Python dependencies" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✅ Python dependencies OK" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Failed to check Python dependencies" -ForegroundColor Red
    exit 1
}

# Check Node.js dependencies and build frontend
Write-Host "📦 Checking Node.js dependencies..." -ForegroundColor Yellow
Set-Location frontend
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "📦 Installing Node.js dependencies..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to install Node.js dependencies" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✅ Node.js dependencies OK" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Failed to check Node.js dependencies" -ForegroundColor Red
    exit 1
}

# Check TypeScript compilation
Write-Host "🔍 Checking TypeScript compilation..." -ForegroundColor Yellow
try {
    $tscResult = npx tsc --noEmit 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ TypeScript compilation failed" -ForegroundColor Red
        Write-Host $tscResult -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ TypeScript compilation OK" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to check TypeScript compilation" -ForegroundColor Red
    exit 1
}

# Build frontend for production
Write-Host "🔨 Building frontend..." -ForegroundColor Yellow
try {
    $buildResult = npm run build 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to build frontend" -ForegroundColor Red
        Write-Host $buildResult -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Frontend built successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to build frontend" -ForegroundColor Red
    exit 1
}

# Copy frontend build to backend for serving
Write-Host "📁 Copying frontend build to backend..." -ForegroundColor Yellow
try {
    $backendStaticDir = "..\backend\static"
    if (Test-Path $backendStaticDir) {
        Remove-Item $backendStaticDir -Recurse -Force
    }
    Copy-Item "dist" $backendStaticDir -Recurse
    Write-Host "✅ Frontend build copied to backend" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to copy frontend build to backend" -ForegroundColor Red
    exit 1
}

# Return to root directory
Set-Location ..

# Start the single development server
Write-Host "🔧 Starting single development server on port $backendPort..." -ForegroundColor Yellow
Write-Host "🌐 The server will serve both API and frontend from http://localhost:$backendPort" -ForegroundColor Cyan

try {
    # Start the backend server (which will also serve frontend)
    python backend/main.py
} catch {
    Write-Host "❌ Failed to start server" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
} 