[#]
# Quick Capture - PowerShell wrapper
# Usage: .\invoke.ps1 [arguments...]
#

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "src\quick_capture\main.py"

# Check if we're in a virtual environment
if ($env:VIRTUAL_ENV) {
    $pythonCmd = "python"
} else {
    # Try to find Python
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $pythonCmd) {
        Write-Error "Python not found. Please install Python 3.10 or later."
        exit 1
    }
    $pythonCmd = $pythonCmd.Source
}

# Run Quick Capture
& $pythonCmd $pythonScript @Arguments
