# Local Prompt Forge runner (Windows PowerShell)
param(
  [Parameter(Position = 0)]
  [ValidateSet("eval", "io", "run", "test")]
  [string]$Command = "eval",
  [string]$Request = "",
  [string]$File = "",
  [switch]$ShowPrompt
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $Root "src"
Set-Location $Root

switch ($Command) {
  "eval" { python -m prompt_forge eval --verbose; break }
  "io" { python -m prompt_forge io; break }
  "test" { python -m unittest discover -s tests -v; break }
  "run" {
    if ($File) {
      $argsList = @("-m", "prompt_forge", "run", "--file", $File)
    } elseif ($Request) {
      $argsList = @("-m", "prompt_forge", "run", "--request", $Request)
    } else {
      throw "run requires -Request or -File"
    }
    if ($ShowPrompt) { $argsList += "--show-prompt" }
    python @argsList
    break
  }
}
