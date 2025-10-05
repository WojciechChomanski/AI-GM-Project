Param(
  [string]$SourceDir = "rules\classes",
  [string]$OutFile = "rules\classes.json"
)

$files = Get-ChildItem -Path $SourceDir -Filter "*.class.json" -ErrorAction SilentlyContinue
if (!$files) {
  Write-Host "No *.class.json files found in $SourceDir." -ForegroundColor Yellow
  exit 0
}

$acc = [ordered]@{}
foreach ($f in $files) {
  try {
    $obj = Get-Content $f.FullName -Raw | ConvertFrom-Json
  } catch {
    Write-Host "ERROR: JSON parse failed for $($f.Name)" -ForegroundColor Red
    throw
  }
  foreach ($k in $obj.PSObject.Properties.Name) {
    if ($acc.Contains($k)) {
      Write-Host "WARN: duplicate class '$k' from $($f.Name) overrides previous." -ForegroundColor Yellow
    }
    $acc[$k] = $obj.$k
  }
}

($acc | ConvertTo-Json -Depth 32) | Set-Content $OutFile -Encoding UTF8
Write-Host "classes.json rebuilt from $($files.Count) files." -ForegroundColor Green
