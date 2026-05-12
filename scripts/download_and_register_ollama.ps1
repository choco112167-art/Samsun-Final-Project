param(
  [string]$RepoId = "mingyu3939/gemma4-e4b-6ep-samsun-gguf",
  [string]$ModelDir = "C:\samsun_models\gemma4-e4b-6ep-samsun",
  [string]$OllamaModelName = "samsun-gemma4"
)

$ErrorActionPreference = "Stop"

function Fail($Message, $Hint = "") {
  Write-Host ""
  Write-Host "[FAIL] $Message" -ForegroundColor Red
  if ($Hint) {
    Write-Host "[HINT] $Hint" -ForegroundColor Yellow
  }
  exit 1
}

function Info($Message) {
  Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Ok($Message) {
  Write-Host "[OK] $Message" -ForegroundColor Green
}

Info "Repo: $RepoId"
Info "Model dir: $ModelDir"
Info "Ollama model: $OllamaModelName"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  Fail "Python was not found." "Install Python 3.11+ and make sure 'python' is available in PATH."
}
Ok "Python found: $($pythonCmd.Source)"

try {
  Info "Installing/upgrading huggingface_hub..."
  python -m pip install -U huggingface_hub
  if ($LASTEXITCODE -ne 0) {
    Fail "huggingface_hub installation failed." "Check Python/pip installation and network access."
  }
} catch {
  Fail "huggingface_hub installation failed." $_.Exception.Message
}
Ok "huggingface_hub is ready."

try {
  New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
} catch {
  Fail "Could not create model directory: $ModelDir" $_.Exception.Message
}

$downloadScript = @'
import os
from huggingface_hub import snapshot_download

repo_id = os.environ["HF_REPO_ID"]
model_dir = os.environ["HF_MODEL_DIR"]
token = os.environ.get("HF_TOKEN") or None

snapshot_download(
    repo_id=repo_id,
    repo_type="model",
    local_dir=model_dir,
    allow_patterns=['*.gguf'],
    token=token,
)
'@

try {
  Info "Downloading *.gguf from Hugging Face..."
  $env:HF_REPO_ID = $RepoId
  $env:HF_MODEL_DIR = $ModelDir
  $tempDownloadScript = Join-Path $env:TEMP "samsun_download_ollama.py"
  Set-Content -LiteralPath $tempDownloadScript -Value $downloadScript -Encoding utf8
  python $tempDownloadScript
  if ($LASTEXITCODE -ne 0) {
    Fail "Hugging Face download failed." "If the repo is private or gated, set `$env:HF_TOKEN='<token>' and rerun this script."
  }
} catch {
  Fail "Hugging Face download failed." "If the repo is private or gated, set `$env:HF_TOKEN='<token>' and rerun. Detail: $($_.Exception.Message)"
} finally {
  Remove-Item Env:\HF_REPO_ID -ErrorAction SilentlyContinue
  Remove-Item Env:\HF_MODEL_DIR -ErrorAction SilentlyContinue
  if ($tempDownloadScript) {
    Remove-Item -LiteralPath $tempDownloadScript -ErrorAction SilentlyContinue
  }
}

$gguf = Get-ChildItem -Path $ModelDir -Recurse -Filter "*.gguf" -File |
  Sort-Object Length -Descending |
  Select-Object -First 1

if (-not $gguf) {
  Info "No local GGUF file found. Listing files currently published in the Hugging Face repo..."
  $listScript = @'
import os
from huggingface_hub import HfApi

repo_id = os.environ["HF_REPO_ID"]
token = os.environ.get("HF_TOKEN") or None
files = HfApi().list_repo_files(repo_id=repo_id, repo_type="model", token=token)
for name in files:
    print(name)
'@
  $tempListScript = Join-Path $env:TEMP "samsun_list_hf_files.py"
  try {
    $env:HF_REPO_ID = $RepoId
    Set-Content -LiteralPath $tempListScript -Value $listScript -Encoding utf8
    python $tempListScript
  } catch {
    Write-Host "[WARN] Could not list repo files: $($_.Exception.Message)" -ForegroundColor Yellow
  } finally {
    Remove-Item Env:\HF_REPO_ID -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tempListScript -ErrorAction SilentlyContinue
  }
  Fail "No GGUF file was found after download." "Ollama cannot create a model from safetensors directly. Upload a *.gguf file to '$RepoId' or convert the safetensors model to GGUF first."
}
Ok "GGUF found: $($gguf.FullName) ($([math]::Round($gguf.Length / 1GB, 2)) GB)"

if ($gguf.DirectoryName -ne $ModelDir) {
  $targetPath = Join-Path $ModelDir $gguf.Name
  Info "Moving GGUF to model root: $targetPath"
  Move-Item -Force -LiteralPath $gguf.FullName -Destination $targetPath
  $gguf = Get-Item -LiteralPath $targetPath
}

$modelfilePath = Join-Path $ModelDir "Modelfile"
$modelfile = @"
FROM ./$($gguf.Name)

PARAMETER temperature 0.2
PARAMETER num_ctx 4096
"@

try {
  Set-Content -LiteralPath $modelfilePath -Value $modelfile -Encoding utf8
} catch {
  Fail "Could not write Modelfile." $_.Exception.Message
}
Ok "Modelfile written: $modelfilePath"

$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCmd) {
  Fail "Ollama command was not found." "Install Ollama for Windows and make sure 'ollama' is available in PATH."
}
Ok "Ollama found: $($ollamaCmd.Source)"

try {
  Info "Registering Ollama model..."
  Push-Location $ModelDir
  ollama create $OllamaModelName -f "Modelfile"
  if ($LASTEXITCODE -ne 0) {
    Fail "ollama create failed." "Check that Ollama is running and the GGUF file is valid."
  }
} catch {
  Fail "ollama create failed." $_.Exception.Message
} finally {
  Pop-Location
}
Ok "Ollama model created: $OllamaModelName"

Info "ollama list"
ollama list
if ($LASTEXITCODE -ne 0) {
  Fail "ollama list failed." "The model may have been created, but listing failed. Check Ollama installation."
}

Ok "Done. Try: ollama run $OllamaModelName"
