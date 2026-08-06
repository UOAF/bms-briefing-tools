$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = "python"

function Write-Step($Message) {
  Write-Host ""
  Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Test-Command($Name) {
  $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Step "Checking Python"
if (-not (Test-Command python)) {
  if (Test-Command winget) {
    Write-Host "Python not found. Installing Python 3.12 with winget..."
    winget install --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
  } else {
    throw "Python is not installed and winget is unavailable. Install Python 3.11+ from python.org, then rerun this installer."
  }
}

Write-Step "Creating virtual environment"
Set-Location $RepoRoot
if (-not (Test-Path $VenvPython)) {
  & $Python -m venv .venv
}

Write-Step "Installing Python dependencies"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

Write-Step "Checking FFmpeg"
if (-not (Test-Command ffmpeg)) {
  if (Test-Command winget) {
    Write-Host "FFmpeg not found. Installing with winget..."
    winget install --id Gyan.FFmpeg --source winget --accept-package-agreements --accept-source-agreements
  } else {
    Write-Warning "FFmpeg was not found. Video/audio export will not work until FFmpeg is installed."
  }
}

Write-Step "Checking pyopencam"
$ToolsDir = Join-Path $RepoRoot ".tools"
$PyOpenCamRoot = Join-Path $ToolsDir "pyopencam"
$PyOpenCamOk = (Test-Path (Join-Path $PyOpenCamRoot "cam_to_json.py")) -and (Test-Path (Join-Path $PyOpenCamRoot "lib\cam_container.py"))
if (-not $PyOpenCamOk) {
  New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
  if (Test-Command git) {
    if (Test-Path $PyOpenCamRoot) {
      Remove-Item -LiteralPath $PyOpenCamRoot -Recurse -Force
    }
    Write-Host "Installing pyopencam into $PyOpenCamRoot..."
    git clone --depth 1 https://github.com/UOAF/pyopencam.git $PyOpenCamRoot
  } else {
    Write-Warning "Git is not installed. Install Git or set PYOPENCAM_ROOT to a pyopencam checkout before running pyopencam decode."
  }
}
if ((Test-Path (Join-Path $PyOpenCamRoot "cam_to_json.py")) -and (Test-Path (Join-Path $PyOpenCamRoot "lib\cam_container.py"))) {
  [Environment]::SetEnvironmentVariable("PYOPENCAM_ROOT", $PyOpenCamRoot, "User")
  $env:PYOPENCAM_ROOT = $PyOpenCamRoot
  Write-Host "pyopencam ready: $PyOpenCamRoot" -ForegroundColor Green
}

Write-Step "Checking Ollama optional local LLM"
if (-not (Test-Command ollama)) {
  if (Test-Command winget) {
    $answer = Read-Host "Install Ollama for offline/local LLM fallback? [Y/n]"
    if ($answer -notmatch "^[Nn]") {
      winget install --id Ollama.Ollama --source winget --accept-package-agreements --accept-source-agreements
    }
  } else {
    Write-Warning "Ollama is not installed. OpenAI/LM Studio/offline-template modes can still be used."
  }
}

if (Test-Command ollama) {
  $answer = Read-Host "Pull default local model llama3.1:8b now? This can take a while. [Y/n]"
  if ($answer -notmatch "^[Nn]") {
    ollama pull llama3.1:8b
  }
}

Write-Step "Creating desktop shortcut"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "UOAF BMS Briefing Tool.lnk"
$Target = Join-Path $RepoRoot "Start-UOAF-BriefingTool.bat"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Target
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
$Shortcut.Save()

Write-Step "Ready"
Write-Host "Launch with:"
Write-Host "  $Target" -ForegroundColor Green
Write-Host "or use the desktop shortcut."
