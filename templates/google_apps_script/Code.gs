const SECRET_PROPERTY = 'MT5_JOURNAL_SHARED_SECRET';
const FALLBACK_SHARED_SECRET = '';
const EXPECTED_TABS = ['Dashboard', 'Trade_Groups', 'Legs', 'Screener_Snapshot', 'LLM_Review', 'Daily_Equity'];

function doPost(e) {
  try {
    const secret = PropertiesService.getScriptProperties().getProperty(SECRET_PROPERTY) || FALLBACK_SHARED_SECRET;
    if (!secret) return jsonResponse({ ok: false, error: 'Missing script property MT5_JOURNAL_SHARED_SECRET' }, 500);
    const payload = JSON.parse(e.postData.contents || '{}');
    if ((payload.secret || '') !== secret) return jsonResponse({ ok: false, error: 'Unauthorized' }, 401);

    const ss = SpreadsheetApp.openById(payload.spreadsheetId);
    ensureTabs_(ss, payload.spreadsheetTabsExpected || EXPECTED_TABS);

    clearRanges_(ss, payload.clearRanges || []);
    writeBatch_(ss, payload.writeData || [], false);
    writeBatch_(ss, payload.dashboardFormulas || [], true);

    const counts = {};
    for (const item of (payload.writeData || [])) {
      const rows = Array.isArray(item.values) ? item.values.length : 0;
      const sheetName = String(item.range || '').split('!')[0];
      counts[sheetName] = rows;
    }

    return jsonResponse({ ok: true, counts });
  } catch (err) {
    return jsonResponse({ ok: false, error: String(err && err.stack || err) }, 500);
  }
}

function ensureTabs_(ss, tabNames) {
  const existing = new Map(ss.getSheets().map(s => [s.getName(), s]));
  for (const name of tabNames) {
    if (!existing.has(name)) ss.insertSheet(name);
  }
}

function clearRanges_(ss, ranges) {
  for (const rangeA1 of ranges) {
    if (!rangeA1) continue;
    ss.getRange(rangeA1).clearContent();
  }
}

function writeBatch_(ss, items, userEntered) {
  for (const item of items) {
    if (!item || !item.range) continue;
    const values = item.values || [];
    if (!values.length) continue;
    const range = ss.getRange(item.range);
    const rows = values.length;
    const cols = Math.max(...values.map(r => Array.isArray(r) ? r.length : 0), 0);
    if (!rows || !cols) continue;
    const normalized = values.map(r => {
      const row = Array.isArray(r) ? r.slice() : [r];
      while (row.length < cols) row.push('');
      return row;
    });
    const target = range.offset(0, 0, rows, cols);
    target.setValues(normalized);
    if (userEntered) SpreadsheetApp.flush();
  }
}

function jsonResponse(obj, status) {
  const output = ContentService.createTextOutput(JSON.stringify(obj));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}
