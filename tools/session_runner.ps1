[CmdletBinding()]
param(
  [switch]$Init,
  [switch]$Show,
  [switch]$Reset,
  [switch]$Resolve,
  [string]$EventId,
  [ValidateSet("success","failure")] [string]$Outcome,
  [string[]]$BonusObjectives
)

function Load-Json {
  param([string]$Path)
  if (!(Test-Path $Path)) { return $null }
  try { Get-Content $Path -Raw | ConvertFrom-Json } catch { return $null }
}
function Save-Json {
  param([Parameter(Mandatory)]$Obj, [Parameter(Mandatory)][string]$Path)
  $dir = Split-Path $Path -Parent
  if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $json = $Obj | ConvertTo-Json -Depth 64
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
}
function Has-Prop { param($obj, [string]$name)
  if (-not $obj) { return $false }
  return ($obj.PSObject.Properties.Name -contains $name)
}
function To-Hashtable { param($obj)
  if ($null -eq $obj) { return @{} }
  if ($obj -is [hashtable]) { return $obj }
  if ($obj -is [System.Management.Automation.PSCustomObject]) {
    $ht = @{}
    foreach ($p in $obj.PSObject.Properties) {
      $v = $p.Value
      if ($v -is [System.Management.Automation.PSCustomObject]) { $v = To-Hashtable $v }
      $ht[$p.Name] = $v
    }
    return $ht
  }
  return @{}
}
function Ensure-State {
  param([string]$Path)
  $state = Load-Json $Path
  if (-not $state) {
    $state = [pscustomobject]@{
      version            = "0.6e"
      started_utc        = (Get-Date).ToUniversalTime().ToString("s") + "Z"
      flags              = @{}
      vendor_adjustments = @{}
      history            = @()
      journal            = @()
    }
  } else {
    if (Has-Prop $state 'flags')              { $state.flags = To-Hashtable $state.flags }
    if (Has-Prop $state 'vendor_adjustments') { $state.vendor_adjustments = To-Hashtable $state.vendor_adjustments }
  }
  return $state
}
function Find-EventFile {
  param([string]$EventId)
  $dir = "rules/events"
  $candidates = Get-ChildItem -Path $dir -Filter "*.json" -File -ErrorAction SilentlyContinue
  $byName = $candidates | Where-Object { $_.Name -like "*$EventId*.json" }
  if ($byName) { return $byName[0].FullName }
  foreach ($f in $candidates) {
    try {
      $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
      if ($j.id -eq $EventId) { return $f.FullName }
    } catch { }
  }
  return $null
}
function Apply-SetFlags {
  param($state, $arr)
  if (-not $arr) { return }
  foreach ($f in ($arr | Where-Object { $_ })) {
    if (-not (Has-Prop $f 'id')) { continue }
    $scope = "session"; if (Has-Prop $f 'scope' -and $f.scope) { $scope = $f.scope }
    $val = $true; if (Has-Prop $f 'value') { $val = $f.value }
    if (-not ($state.flags -is [hashtable])) { $state.flags = To-Hashtable $state.flags }
    $state.flags[$f.id] = @{
      scope       = $scope
      value       = $val
      updated_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    }
  }
}
function Ensure-VendorSlot {
  param($state, [string]$VendorId)
  if (-not $VendorId) { return $null }
  if (-not ($state.vendor_adjustments -is [hashtable])) {
    $state.vendor_adjustments = To-Hashtable $state.vendor_adjustments
  }
  if (-not ($state.vendor_adjustments.ContainsKey($VendorId))) {
    $state.vendor_adjustments[$VendorId] = @{
      discount_pct          = $null
      bench_time_credit_min = 0
      expires               = $null
      notes                 = @()
      updated_utc           = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    }
  }
  return $state.vendor_adjustments[$VendorId]
}
function Apply-VendorAdjustments {
  param($state, $arr)
  if (-not $arr) { return }
  foreach ($adj in ($arr | Where-Object { $_ })) {
    $vid = $null; if (Has-Prop $adj 'vendor_id') { $vid = $adj.vendor_id }
    if (-not $vid) { continue }
    $slot = Ensure-VendorSlot -state $state -VendorId $vid
    $mode = $null; if (Has-Prop $adj 'mode') { $mode = $adj.mode }
    $val  = $null; if (Has-Prop $adj 'value') { $val  = $adj.value }
    $stack = "max"; if (Has-Prop $adj 'stacking' -and $adj.stacking) { $stack = $adj.stacking }
    switch ($mode) {
      "discount_pct" {
        if ($null -ne $val) {
          $new = [double]$val
          $cur = $slot.discount_pct
          if ($stack -eq "add") {
            if ($null -eq $cur) { $cur = 0 }
            $slot.discount_pct = $cur + $new
          } else {
            if ($null -eq $cur) { $slot.discount_pct = $new }
            elseif ($new -lt 0 -and $cur -lt 0) { $slot.discount_pct = [math]::Min($cur, $new) }
            elseif ($new -ge 0 -and $cur -ge 0) { $slot.discount_pct = [math]::Max($cur, $new) }
            else { if ([math]::Abs($new) -gt [math]::Abs($cur)) { $slot.discount_pct = $new } }
          }
        }
      }
      "bench_time_credit_min" {
        if ($null -ne $val) {
          $slot.bench_time_credit_min = [int]$slot.bench_time_credit_min + [int]$val
        }
      }
      default { }
    }
    if (Has-Prop $adj 'expires' -and $adj.expires) { $slot.expires = $adj.expires }
    if (Has-Prop $adj 'reason'  -and $adj.reason)  { $slot.notes  += $adj.reason }
    $slot.updated_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  }
}
function Apply-Aftermath {
  param($state, $event, [string]$Outcome, [string[]]$BonusObjectives)
  if (-not (Has-Prop $event 'aftermath')) { return }
  if ($Outcome -eq "success" -and (Has-Prop $event.aftermath 'on_success')) {
    $os = $event.aftermath.on_success
    if (Has-Prop $os 'set_flags')           { Apply-SetFlags -state $state -arr $os.set_flags }
    if (Has-Prop $os 'vendor_adjustments')  { Apply-VendorAdjustments -state $state -arr $os.vendor_adjustments }
    if (Has-Prop $os 'journal')             {
      if ($os.journal -is [string]) { $state.journal += $os.journal } else { $state.journal += $os.journal }
    }
  }
  elseif ($Outcome -eq "failure" -and (Has-Prop $event.aftermath 'on_failure')) {
    $of = $event.aftermath.on_failure
    if (Has-Prop $of 'set_flags')           { Apply-SetFlags -state $state -arr $of.set_flags }
    if (Has-Prop $of 'vendor_adjustments')  { Apply-VendorAdjustments -state $state -arr $of.vendor_adjustments }
    if (Has-Prop $of 'journal')             {
      if ($of.journal -is [string]) { $state.journal += $of.journal } else { $state.journal += $of.journal }
    }
  }
  if ($Outcome -eq "success" -and (Has-Prop $event.aftermath 'on_bonus_success')) {
    $bs = $event.aftermath.on_bonus_success
    $req = $null; if (Has-Prop $bs 'if_objective') { $req = $bs.if_objective }
    $met = ($req -and $BonusObjectives -and ($BonusObjectives -contains $req))
    if ($met) {
      if (Has-Prop $bs 'set_flags')          { Apply-SetFlags -state $state -arr $bs.set_flags }
      if (Has-Prop $bs 'vendor_adjustments') { Apply-VendorAdjustments -state $state -arr $bs.vendor_adjustments }
    }
  }
}

$statePath = "sessions/session_state.json"
if ($Init) {
  $state = Ensure-State $statePath
  Save-Json -Obj $state -Path $statePath
  Write-Host "Initialized $statePath" -ForegroundColor Green
  exit 0
}
if ($Reset) {
  if (Test-Path $statePath) { Remove-Item $statePath -Force }
  Write-Host "Cleared session state." -ForegroundColor Yellow
  exit 0
}
if ($Show) {
  $state = Ensure-State $statePath
  $state | ConvertTo-Json -Depth 64
  exit 0
}
if ($Resolve) {
  if (-not $EventId) { Write-Error "Missing -EventId"; exit 1 }
  if (-not $Outcome) { Write-Error "Missing -Outcome (success|failure)"; exit 1 }
  $path = Find-EventFile -EventId $EventId
  if (-not $path) { Write-Error "Event not found for id '$EventId'"; exit 1 }
  try { $evt = Get-Content $path -Raw | ConvertFrom-Json } catch {
    Write-Error "Failed to parse event JSON at $path"; exit 1
  }
  $state = Ensure-State $statePath
  Apply-Aftermath -state $state -event $evt -Outcome $Outcome -BonusObjectives $BonusObjectives
  $state.history += [pscustomobject]@{
    event_id      = $EventId
    outcome       = $Outcome
    bonus         = $BonusObjectives
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  }
  Save-Json -Obj $state -Path $statePath
  Write-Host "Applied aftermath for $EventId ($Outcome). State saved to $statePath" -ForegroundColor Green
  exit 0
}
Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File tools/session_runner.ps1 -Init"
Write-Host "  powershell -ExecutionPolicy Bypass -File tools/session_runner.ps1 -Resolve -EventId evt_hold_the_cut_v0_6b -Outcome success -BonusObjectives OBJ_MIN_INJURY"
Write-Host "  powershell -ExecutionPolicy Bypass -File tools/session_runner.ps1 -Show"
Write-Host "  powershell -ExecutionPolicy Bypass -File tools/session_runner.ps1 -Reset"
