const fs = require('fs');
const path = require('path');

const cfg = JSON.parse(fs.readFileSync('C:/Users/anmar/.openclaw/openclaw.json', 'utf8'));
const token = cfg.channels.discord.token;
const payload = JSON.parse(fs.readFileSync('C:/Users/anmar/.openclaw/workspace-mt5/mt5_frx_content.json', 'utf8'));
const filePath = 'C:/Users/anmar/.openclaw/workspace-mt5/mt5_frx_report_full.txt';

(async () => {
  const form = new FormData();
  form.append('payload_json', JSON.stringify({ content: payload.content }));
  const blob = new Blob([fs.readFileSync(filePath)], { type: 'text/plain' });
  form.append('files[0]', blob, path.basename(filePath));
  const res = await fetch('https://discord.com/api/v10/channels/1489501923785572435/messages', {
    method: 'POST',
    headers: { Authorization: `Bot ${token}` },
    body: form,
  });
  const text = await res.text();
  console.log(res.status);
  console.log(text);
})();
