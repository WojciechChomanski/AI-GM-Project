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

# ---------------- Helpers ----------------
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

function Has-Prop {
  param($obj, [string]$name)
  if (-not $obj) { return $false }
  return ($obj.PSObject.Properties.Name -contains $name)
}

function Ensure-State {
  param([string]$Path)
  $state = Load-Json $Path
  if (-not $state) {
    $state = [ordered]@{
      version            = "0.6e"
      started_utc        = (Get-Date).ToUniversalTime().ToString("s") + "Z"
      flags              = @{}      # id -> { scope, value, updated_utc }
      vendor_adjustments = @{}      # vendor_id -> { discount_pct, bench_time_credit_min, expires, notes[] }
      history            = @()      # [{ event_id, outcome, bonus[], timestamp_utc }]
      journal            = @()      # GM notes
    }
  }
  return $state
}

function Find-EventFile {
  param([string]$EventId)
  $dir = "rules/events"
  $candidates = Get-ChildItem -Path $dir -Filter "*.json" -File -ErrorAction SilentlyContinue

  # 1) filename contains id
  $byName = $candidates | Where-Object { $_.Name -like "*$EventId*.json" }
  if ($byName) { return $byName[0].FullName }

  # 2) open json and check .id
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
  foreach ($f in ($arr | Where-Object { $_ })) {
    if (-not (Has-Prop $f 'id')) { continue }
    $scope = if (Has-Prop $f 'scope' -and $f.scope) { $f.scope } else { "session" }
    $state.flags[$f.id] = @{
      scope       = $scope
      value       = (if (Has-Prop $f 'value') { $f.value } else { $true })
      updated_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    }
  }
}

function Ensure-VendorSlot {
  param($state, [string]$VendorId)
  if (-not $VendorId) { return $null }
  if (-not ($state.vendor_adjustments.ContainsKey($VendorId))) {
    $state.vendor_adjustments[$VendorId] = @{
      discount_pct           = $null
      bench_time_credit_min  = 0
      expires                = $null
      notes                  = @()
    }
  }
  return $state.vendor_adjustments[$VendorId]
}

function Apply-VendorAdjustments {
  param($state, $arr)
  foreach ($adj in ($arr | Where-Object { $_ })) {
    $vid = if (Has-Prop $adj 'vendor_id') { $adj.vendor_id } else { $null }
    if (-not $vid) { continue }
    $slot = Ensure-VendorSlot -state $state -VendorId $vid

    $mode = if (Has-Prop $adj 'mode') { $adj.mode } else { $null }
    $val  = if (Has-Prop $adj 'value') { $adj.value } else { $null }
    $stack = if (Has-Prop $adj 'stacking' -and $adj.stacking) { $adj.stacking } else { "max" }

    switch ($mode) {
      "discount_pct" {
        if ($null -eq $val) { break }
        $new = [double]$val
        $cur = $slot.discount_pct

        if ($stack -eq "add") {
          if ($null -eq $cur) { $cur = 0 }
          $slot.discount_pct = $cur + $new
        } else {
          if ($null -eq $cur) { $slot.discount_pct = $new }
          else {
            if ($new -lt 0 -and $cur -lt 0) {
              $slot.discount_pct = [math]::Min($cur, $new)
            } elseif ($new -ge 0 -and $cur -ge 0) {
              $slot.discount_pct = [math]::Max($cur, $new)
            } else {
              if ([math]::Abs($new) -gt [math]::Abs($cur)) { $slot.discount_pct = $new }
            }
          }
        }
      }
      "bench_time_credit_min" {
        if ($null -ne $val) {
          $slot.bench_time_credit_min = [int]$slot.bench_time_credit_min + [int]$val
        }
      }
      default {
        # ignore unknown modes, but keep a note if present
      }
    }

    if (Has-Prop $adj 'expires' -and $adj.expires) { $slot.expires = $adj.expires }
    if (Has-Prop $adj 'reason'  -and $adj.reason)  { $slot.notes  += $adj.reason }
  }
}

function Apply-Aftermath {
  param($state, $event, [string]$Outcome, [string[]]$BonusObjectives)

  if (-not (Has-Prop $event 'aftermath')) { return }

  if ($Outcome -eq "success" -and (Has-Prop $event.aftermath 'on_success')) {
    $os = $event.aftermath.on_success
    if (Has-Prop $os 'set_flags')           { Apply-SetFlags -state $state -arr $os.set_flags }
    if (Has-Prop $os 'vendor_adjustments')  { Apply-VendorAdjustments -state $state -arr $os.vendor_adjustments }
    if (Has-Prop $os 'journal')             { $state.journal += $os.journal }
  }
  elseif ($Outcome -eq "failure" -and (Has-Prop $event.aftermath 'on_failure')) {
    $of = $event.aftermath.on_failure
    if (Has-Prop $of 'set_flags')           { Apply-SetFlags -state $state -arr $of.set_flags }
    if (Has-Prop $of 'vendor_adjustments')  { Apply-VendorAdjustments -state $state -arr $of.vendor_adjustments }
    if (Has-Prop $of 'journal')             { $state.journal += $of.journal }
  }

  if ($Outcome -eq "success" -and (Has-Prop $event.aftermath 'on_bonus_success')) {
    $bs = $event.aftermath.on_bonus_success
    $req = if (Has-Prop $bs 'if_objective') { $bs.if_objective } else { $null }
    $met = ($req -and $BonusObjectives -and ($BonusObjectives -contains $req))
    if ($met) {
      if (Has-Prop $bs 'set_flags')          { Apply-SetFlags -state $state -arr $bs.set_flags }
      if (Has-Prop $bs 'vendor_adjustments') { Apply-VendorAdjustments -state $state -arr $bs.vendor_adjustments }
    }
  }
}

# ---------------- Entry points ----------------
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
