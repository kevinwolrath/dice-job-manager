# Phase 8 regression suite: proves the cross-user prompt-selection cache
# (services/mcp-server/app/prompt_cache.py) doesn't weaken the isolation
# guarantee it sits in front of.
#
# The cache only ever stores a DECISION ("this exact sentence means: call
# get_my_jobs()"), never a RESULT and never an argument — get_my_jobs() and
# list_stock() are the only two tools it's allowed to cache, and both take
# zero arguments, so there is no user-specific value that could ever end up
# cached. A cache hit still calls the real tool for real, through whichever
# caller is asking right now, using THEIR OWN forwarded token. This script
# proves that mechanically: get john's exact question cached, then ask the
# identical question as jane, and confirm jane gets jane's own jobs back —
# not john's, not a stale copy of john's answer, not an error — even though
# the "which tool to call" decision was served from a cache entry John's
# request created.
#
# Prerequisites: the full stack is up (`docker compose up -d`), dice-ollama
# has llama3.1:8b pulled, and dice-stock-service has at least one material
# type, one production method, and one dice job number colour.
#
# Run from the repo root:
#   .\tests\test-prompt-cache.ps1

$ErrorActionPreference = "Stop"

$UserServiceUrl = "http://localhost:4101"
$StockServiceUrl = "http://localhost:4102"
$JobServiceUrl = "http://localhost:4103"
$McpServiceUrl = "http://localhost:4104"

$script:results = @()

function Assert {
    param([bool]$Condition, [string]$Description)
    if ($Condition) {
        Write-Host "PASS  $Description" -ForegroundColor Green
    } else {
        Write-Host "FAIL  $Description" -ForegroundColor Red
    }
    $script:results += $Condition
}

function Invoke-Login {
    param([string]$Username, [string]$Password)
    $body = @{ username = $Username; password = $Password } | ConvertTo-Json
    $resp = Invoke-RestMethod -Method Post "$UserServiceUrl/login" -Body $body -ContentType "application/json"
    return $resp.access_token
}

function Get-StockDefaults {
    param([string]$Token)

    $materialTypes = Invoke-RestMethod "$StockServiceUrl/material-types" -Headers @{ Authorization = "Bearer $Token" }
    $productionMethods = Invoke-RestMethod "$StockServiceUrl/production-methods" -Headers @{ Authorization = "Bearer $Token" }
    $colours = Invoke-RestMethod "$StockServiceUrl/dice-job-number-colours" -Headers @{ Authorization = "Bearer $Token" }

    if (-not $materialTypes -or -not $productionMethods -or -not $colours) {
        throw ("No reference data in dice-stock-service yet. Log in as admin in dice-test-client " +
               "and add at least one material type, production method, and dice job number colour " +
               "(Phase 1), then re-run this script.")
    }

    $method = $productionMethods[0]
    $colourCount = 1
    if ($method.minimum_colour_count) { $colourCount = $method.minimum_colour_count }

    return @{
        material_type_id          = $materialTypes[0].material_type_id
        production_method_id      = $method.production_method_id
        dice_job_number_colour_id = $colours[0].dice_job_number_colour_id
        colour_count               = $colourCount
    }
}

function New-DiceJob {
    param([string]$Token, [string]$JobName, [hashtable]$Defaults)
    $body = @{
        job_name                   = $JobName
        colour_count                = $Defaults.colour_count
        material_type_id            = $Defaults.material_type_id
        production_method_id        = $Defaults.production_method_id
        dice_job_number_colour_id   = $Defaults.dice_job_number_colour_id
    } | ConvertTo-Json
    return Invoke-RestMethod -Method Post "$JobServiceUrl/dice-jobs" -Body $body -ContentType "application/json" `
        -Headers @{ Authorization = "Bearer $Token" }
}

function Get-OrCreate-NamedJob {
    param([string]$Token, [string]$JobName)
    $jobs = Invoke-RestMethod "$JobServiceUrl/dice-jobs" -Headers @{ Authorization = "Bearer $Token" }
    $existing = $jobs | Where-Object { $_.job_name -eq $JobName }
    if ($existing) { return $existing }
    $defaults = Get-StockDefaults -Token $Token
    return New-DiceJob -Token $Token -JobName $JobName -Defaults $defaults
}

function Send-ChatMessage {
    param([string]$Token, [string]$Message)
    $body = @{ message = $Message; history = @() } | ConvertTo-Json
    return Invoke-RestMethod -Method Post "$McpServiceUrl/chat" -Body $body -ContentType "application/json" `
        -Headers @{ Authorization = "Bearer $Token" }
}

Write-Host "Logging in demo users..."
$johnToken = Invoke-Login -Username "john" -Password "john-demo-pw"
$janeToken = Invoke-Login -Username "jane" -Password "jane-demo-pw"

Write-Host "Ensuring canary jobs exist for both users..."
$johnCanary = Get-OrCreate-NamedJob -Token $johnToken -JobName "John's cache-test canary job (Phase 8)"
$janeCanary = Get-OrCreate-NamedJob -Token $janeToken -JobName "Jane's cache-test canary job (Phase 8)"

# Deliberately plain, ordinary phrasing — close to what Phase 6's own README
# suggests trying ("What dice jobs do I have?"). An earlier version of this
# probe was a more convoluted, artificial-sounding sentence, which risked
# the small local model attaching a stray/hallucinated argument to its
# get_my_jobs() call for an unusual sentence like that. That wouldn't be a
# security problem (a malformed tool call still just errors out via
# _call_tool's TypeError handling) but it WOULD silently block caching,
# since app/prompt_cache.py only ever remembers a call that came back with
# zero arguments — so a flaky model on a weird sentence looks, from this
# test's point of view, identical to "the cache isn't working." Plain,
# ordinary phrasing is more reliable for this specific model, which is what
# actually matters here.
$probe = "Please list all of my dice jobs."

Write-Host "`n--- Priming the cache: john asks a few times ---"
$lastJohnResult = $null
for ($i = 0; $i -lt 3; $i++) {
    $lastJohnResult = Send-ChatMessage -Token $johnToken -Message $probe
    Write-Host ("  call {0}: cached={1}, tookMs={2}" -f ($i + 1), $lastJohnResult.cached, $lastJohnResult.tookMs)
}

Assert -Condition ($lastJohnResult.cached -eq $true) `
    -Description "After a few identical asks, john's request is served from the cache"
Assert -Condition ($lastJohnResult.toolCalls.Count -eq 1 -and $lastJohnResult.toolCalls[0].name -eq "get_my_jobs") `
    -Description "The cached decision is a single get_my_jobs() call"

$johnResultJson = ($lastJohnResult.toolCalls[0].result | ConvertTo-Json -Depth 10 -Compress)
Assert -Condition ($johnResultJson -match [regex]::Escape($johnCanary.job_name)) `
    -Description "John's own (cached) response contains john's own canary job"

Write-Host "`n--- Jane asks the exact same question ---"
$janeResult = Send-ChatMessage -Token $janeToken -Message $probe
Write-Host ("  cached={0}, tookMs={1}" -f $janeResult.cached, $janeResult.tookMs)

Assert -Condition ($janeResult.cached -eq $true) `
    -Description "Jane's identical question also hits the cache john's requests populated"

$janeResultJson = ($janeResult.toolCalls[0].result | ConvertTo-Json -Depth 10 -Compress)
Assert -Condition ($janeResultJson -match [regex]::Escape($janeCanary.job_name)) `
    -Description "Jane's (cached) response contains jane's OWN canary job"
Assert -Condition ($janeResultJson -notmatch [regex]::Escape($johnCanary.job_name)) `
    -Description "Jane's (cached) response does NOT contain john's canary job"
Assert -Condition ($janeResult.reply -notmatch [regex]::Escape($johnCanary.job_name)) `
    -Description "Jane's (cached) reply text does NOT mention john's canary job"

# The point in one line: the cached DECISION (call get_my_jobs) was shared
# across john and jane. The EXECUTION, and therefore the data, was not —
# each call still ran for real against the caller's own token.
Assert -Condition ($janeResultJson -ne $johnResultJson) `
    -Description "John and jane got DIFFERENT results back despite sharing one cached decision"

Write-Host "`n--- /cache-stats is reachable and reflects real activity ---"
$stats = Invoke-RestMethod "$McpServiceUrl/cache-stats" -Headers @{ Authorization = "Bearer $johnToken" }
Write-Host ("  hits={0} misses={1} learned_patterns={2}" -f $stats.hits, $stats.misses, $stats.learned_patterns)
Write-Host ("  avg_cached_ms={0} avg_uncached_ms={1} (server-measured, across every user so far)" `
    -f $stats.avg_cached_ms, $stats.avg_uncached_ms)
Assert -Condition ($stats.hits -ge 2) -Description "/cache-stats shows at least the 2 hits this run just produced"
Assert -Condition ($stats.learned_patterns -ge 1) -Description "/cache-stats shows at least 1 learned prompt->tool pattern"
# Not asserted as a hard pass/fail: a cache hit skipping dice-ollama
# entirely SHOULD be dramatically faster than a turn that has to round-trip
# through a local 8B model (often 10-100x), but timing comparisons are
# inherently a little noisy (first-call cold start, CPU vs GPU inference,
# whatever else is running on the machine) — not worth flaking the suite
# over. The numbers printed above are the real evidence; eyeball them.

$passCount = ($script:results | Where-Object { $_ -eq $true }).Count
$totalCount = $script:results.Count

Write-Host ""
Write-Host "=== $passCount / $totalCount passed ==="

if ($passCount -ne $totalCount) {
    exit 1
}
