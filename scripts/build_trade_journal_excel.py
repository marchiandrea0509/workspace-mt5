#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

WORKSPACE = Path(__file__).resolve().parents[1]
REPORTS = WORKSPACE / 'reports' / 'mt5_autotrade_phase1'
BACKFILL = REPORTS / 'trade_journal_backfill.json'
EXCEL_DIR = REPORTS / 'excel'
LATEST_XLSX = EXCEL_DIR / 'MT5_trade_journal_latest.xlsx'
LATEST_META = EXCEL_DIR / 'MT5_trade_journal_latest.json'
BACKFILL_SCRIPT = WORKSPACE / 'scripts' / 'build_trade_journal_backfill.py'


@dataclass(frozen=True)
class Formula:
    text: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def ensure_backfill(refresh: bool) -> None:
    if not refresh and BACKFILL.exists():
        return
    subprocess.run([sys.executable, str(BACKFILL_SCRIPT)], check=True, cwd=str(WORKSPACE))


def excel_timestamp() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def col_name(index_1_based: int) -> str:
    out = ''
    n = index_1_based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def cell_ref(row_idx: int, col_idx: int) -> str:
    return f'{col_name(col_idx)}{row_idx}'


def xml_header() -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def inline_string_cell(ref: str, value: str) -> str:
    text = str(value)
    preserve = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() or '\n' in text else ''
    return f'<c r="{ref}" t="inlineStr"><is><t{preserve}>{escape(text)}</t></is></c>'


def number_cell(ref: str, value: int | float) -> str:
    return f'<c r="{ref}"><v>{value}</v></c>'


def bool_cell(ref: str, value: bool) -> str:
    return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'


def formula_cell(ref: str, value: Formula) -> str:
    formula = value.text[1:] if value.text.startswith('=') else value.text
    return f'<c r="{ref}"><f>{escape(formula)}</f></c>'


def serialize_cell(ref: str, value: Any) -> str:
    if isinstance(value, Formula):
        return formula_cell(ref, value)
    if value is None:
        return inline_string_cell(ref, '')
    if isinstance(value, bool):
        return bool_cell(ref, value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return number_cell(ref, value)
    return inline_string_cell(ref, str(value))


def sheet_xml(rows: list[list[Any]]) -> str:
    if not rows:
        rows = [[]]
    max_cols = max((len(r) for r in rows), default=1)
    last_ref = cell_ref(max(len(rows), 1), max(max_cols, 1))
    parts = [
        xml_header(),
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        f'<dimension ref="A1:{last_ref}"/>',
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>',
        '<sheetFormatPr defaultRowHeight="15"/>',
        '<sheetData>',
    ]
    for r_idx, row in enumerate(rows, start=1):
        parts.append(f'<row r="{r_idx}">')
        for c_idx, value in enumerate(row, start=1):
            ref = cell_ref(r_idx, c_idx)
            parts.append(serialize_cell(ref, value))
        parts.append('</row>')
    parts.extend([
        '</sheetData>',
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>',
        '</worksheet>',
    ])
    return ''.join(parts)


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = []
    for idx, name in enumerate(sheet_names, start=1):
        sheets.append(
            f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        )
    return ''.join([
        xml_header(),
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        '<workbookViews><workbookView/></workbookViews>',
        '<sheets>',
        ''.join(sheets),
        '</sheets>',
        '</workbook>',
    ])


def workbook_rels_xml(sheet_count: int) -> str:
    rels = []
    for idx in range(1, sheet_count + 1):
        rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    base = sheet_count
    rels.append(
        f'<Relationship Id="rId{base + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return ''.join([
        xml_header(),
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        ''.join(rels),
        '</Relationships>',
    ])


def content_types_xml(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for idx in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return ''.join([
        xml_header(),
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        ''.join(overrides),
        '</Types>',
    ])


def root_rels_xml() -> str:
    return ''.join([
        xml_header(),
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>',
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>',
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>',
        '</Relationships>',
    ])


def styles_xml() -> str:
    return ''.join([
        xml_header(),
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>',
        '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>',
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>',
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>',
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>',
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>',
        '</styleSheet>',
    ])


def app_xml(sheet_names: list[str]) -> str:
    titles = ''.join(f'<vt:lpstr>{escape(name)}</vt:lpstr>' for name in sheet_names)
    return ''.join([
        xml_header(),
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">',
        '<Application>Gray</Application>',
        f'<TitlesOfParts><vt:vector size="{len(sheet_names)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts>',
        f'<HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>{len(sheet_names)}</vt:i4></vt:variant></vt:vector></HeadingPairs>',
        '</Properties>',
    ])


def core_xml(created_at_utc: str) -> str:
    return ''.join([
        xml_header(),
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '<dc:creator>Gray</dc:creator>',
        '<cp:lastModifiedBy>Gray</cp:lastModifiedBy>',
        '<dc:title>MT5 trade journal</dc:title>',
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{escape(created_at_utc)}</dcterms:created>',
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{escape(created_at_utc)}</dcterms:modified>',
        '</cp:coreProperties>',
    ])


def dashboard_rows(generated_at_utc: str, bundle_rel: str) -> list[list[Any]]:
    return [
        ['Metric', 'Value'],
        ['Generated At UTC', generated_at_utc],
        ['Source Bundle', bundle_rel],
        ['Realized PnL', Formula('=IFERROR(SUM(Trade_Groups!W2:W),0)')],
        ['Unrealized PnL', ''],
        ['Total Trade Groups', Formula('=COUNTA(Trade_Groups!A2:A1048576)')],
        ['Total Filled Legs', Formula('=COUNTA(Legs!A2:A1048576)')],
        ['Win Rate', Formula('=IFERROR(COUNTIF(Trade_Groups!AE2:AE1048576,"win")/COUNTIF(Trade_Groups!AF2:AF1048576,"<>"),0)')],
        ['Profit Factor', Formula('=IFERROR(SUMIF(Trade_Groups!AE2:AE1048576,"win",Trade_Groups!W2:W1048576)/ABS(SUMIF(Trade_Groups!AE2:AE1048576,"loss",Trade_Groups!W2:W1048576)),0)')],
        ['Expectancy Per Trade', Formula('=IFERROR(AVERAGE(Trade_Groups!W2:W1048576),0)')],
        ['Expectancy in R', Formula('=IFERROR(AVERAGE(Trade_Groups!X2:X1048576),0)')],
        ['Average Win', Formula('=IFERROR(AVERAGEIF(Trade_Groups!W2:W1048576,">0"),0)')],
        ['Average Loss', Formula('=IFERROR(AVERAGEIF(Trade_Groups!W2:W1048576,"<0"),0)')],
        ['Max Drawdown', ''],
        ['Recovery Factor', ''],
        ['Average Planned Risk', Formula('=IFERROR(AVERAGE(Trade_Groups!U2:U1048576),0)')],
        ['Average Hold Time', ''],
        ['Average Margin Used', Formula('=IFERROR(AVERAGE(Trade_Groups!V2:V1048576),0)')],
        ['Rejection Rate', Formula('=IFERROR(COUNTIF(Legs!X2:X1048576,"rejected")/COUNTA(Legs!A2:A1048576),0)')],
        ['Cancel Rate', Formula('=IFERROR(COUNTIF(Legs!X2:X1048576,"cancelled")/COUNTA(Legs!A2:A1048576),0)')],
    ]


def make_sheet_rows(backfill: dict[str, Any], generated_at_utc: str) -> dict[str, list[list[Any]]]:
    bundle_rel = BACKFILL.relative_to(WORKSPACE).as_posix()
    return {
        'Dashboard': dashboard_rows(generated_at_utc, bundle_rel),
        'Trade_Groups': backfill.get('Trade_Groups') or [[]],
        'Legs': backfill.get('Legs') or [[]],
        'Screener_Snapshot': backfill.get('Screener_Snapshot') or [[]],
        'LLM_Review': backfill.get('LLM_Review') or [[]],
        'Daily_Equity': backfill.get('Daily_Equity') or [[]],
    }


def write_workbook(path: Path, sheets: dict[str, list[list[Any]]], created_at_utc: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_names = list(sheets.keys())
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types_xml(len(sheet_names)))
        zf.writestr('_rels/.rels', root_rels_xml())
        zf.writestr('docProps/app.xml', app_xml(sheet_names))
        zf.writestr('docProps/core.xml', core_xml(created_at_utc))
        zf.writestr('xl/workbook.xml', workbook_xml(sheet_names))
        zf.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml(len(sheet_names)))
        zf.writestr('xl/styles.xml', styles_xml())
        for idx, name in enumerate(sheet_names, start=1):
            zf.writestr(f'xl/worksheets/sheet{idx}.xml', sheet_xml(sheets[name]))


def save_metadata(path: Path, generated_at_utc: str, sheets: dict[str, list[list[Any]]]) -> dict[str, Any]:
    meta = {
        'ok': True,
        'generatedAtUtc': generated_at_utc,
        'workbookPath': str(path),
        'latestPath': str(LATEST_XLSX),
        'rowCounts': {name: max(len(rows) - 1, 0) for name, rows in sheets.items() if name != 'Dashboard'},
        'sheetNames': list(sheets.keys()),
    }
    LATEST_META.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description='Build versioned MT5 trade journal Excel workbook without external Excel libraries.')
    ap.add_argument('--skip-refresh-backfill', action='store_true', help='Reuse existing trade_journal_backfill.json if present.')
    ap.add_argument('--out-dir', default=str(EXCEL_DIR), help='Directory for versioned workbook outputs.')
    args = ap.parse_args()

    ensure_backfill(refresh=not args.skip_refresh_backfill)
    backfill = load_json(BACKFILL)
    generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    sheets = make_sheet_rows(backfill, generated_at_utc)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    versioned = out_dir / f'MT5_trade_journal_{excel_timestamp()}.xlsx'
    write_workbook(versioned, sheets, generated_at_utc)
    shutil.copyfile(versioned, LATEST_XLSX)

    meta = save_metadata(versioned, generated_at_utc, sheets)
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
