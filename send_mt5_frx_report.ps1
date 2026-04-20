$report = Get-Content 'C:\Users\anmar\.openclaw\workspace\tradingview\reports\pine_screener\pine_screener_2026-04-20T13-07-53-565Z.json' -Raw | ConvertFrom-Json
$table = Get-Content $report.textPath -Raw
$runBerlin = ([DateTimeOffset]::Parse($report.generatedAt)).ToOffset([TimeSpan]::FromHours(2)).ToString('yyyy-MM-dd HH:mm')
$top5 = ($report.top5 | ForEach-Object { '{0} {1:N1}' -f $_.symbol, [double]$_.bestScore }) -join ' | '
$lines = @(
  'TV Pine Screener 4H - MT5_FRX',
  ('Run: ' + $runBerlin + ' Berlin'),
  'Watchlist: MT5_FRX',
  'Indicator: OC Hybrid Edge Screener v6',
  ('Scanned: ' + $report.rowCount + ' symbols'),
  ('Top 5: ' + $top5),
  '',
  '```',
  $table.TrimEnd(),
  '```'
)
$message = $lines -join [Environment]::NewLine
$cfg = Get-Content 'C:\Users\anmar\.openclaw\openclaw.json' -Raw | ConvertFrom-Json
$token = $cfg.channels.discord.token
$headers = @{ Authorization = ('Bot ' + $token); 'Content-Type' = 'application/json' }
$body = @{ content = $message } | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri 'https://discord.com/api/v10/channels/1489501923785572435/messages' -Headers $headers -Body $body | ConvertTo-Json -Depth 6
