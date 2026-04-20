$cfg = Get-Content 'C:\Users\anmar\.openclaw\openclaw.json' -Raw | ConvertFrom-Json
$token = $cfg.channels.discord.token
$content = Get-Content 'C:\Users\anmar\.openclaw\workspace-mt5\mt5_frx_content.json' -Raw | ConvertFrom-Json
$form = @{
  payload_json = (@{ content = $content.content } | ConvertTo-Json -Compress)
  'files[0]' = Get-Item 'C:\Users\anmar\.openclaw\workspace-mt5\mt5_frx_report_full.txt'
}
Invoke-RestMethod -Method Post -Uri 'https://discord.com/api/v10/channels/1489501923785572435/messages' -Headers @{ Authorization = ('Bot ' + $token) } -Form $form | ConvertTo-Json -Depth 6
