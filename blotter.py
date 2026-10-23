import dash
import dash_ag_grid as dag
import pandas as pd
from dash import dcc, html
dash.register_page(__name__, path='/blotter', name='Trade Blotter')
sample_trades = pd.DataFrame([('T001', '2026-10-23 09:05:00', 'AAPL', 'Buy', 100, 100.0, 102.0, 'Momentum', 'Information Technology'), ('T002', '2026-10-23 09:12:00', 'JPM', 'Buy', 80, 150.0, 148.0, 'Value', 'Financials'), ('T003', '2026-10-23 09:20:00', 'XOM', 'Sell', 120, 110.0, 108.0, 'Macro', 'Energy'), ('T004', '2026-10-23 10:00:00', 'MSFT', 'Buy', 50, 300.0, 304.0, 'Momentum', 'Information Technology'), ('T005', '2026-10-23 10:15:00', 'KO', 'Buy', 200, 60.0, 59.5, 'Value', 'Consumer Staples'), ('T006', '2026-10-23 11:10:00', 'GS', 'Sell', 30, 400.0, 405.0, 'Macro', 'Financials'), ('T007', '2026-10-23 09:20:00', 'XOM', 'Sell', 120, 110.0, 108.0, 'Macro', 'Energy'), ('T008', '2026-10-23 13:30:00', 'AMZN', 'Buy', 60, 180.0, 183.0, 'Momentum', 'Consumer Discretionary')], columns=['TradeID', 'Timestamp', 'Ticker', 'Side', 'Quantity', 'ExecutionPrice', 'MarkPrice', 'Strategy', 'Sector'])
columns = [{'field': 'TradeID', 'headerName': 'Trade ID', 'pinned': 'left', 'minWidth': 120}, {'field': 'Timestamp', 'minWidth': 210}, {'field': 'Ticker', 'minWidth': 110}, {'field': 'Side', 'minWidth': 100}, {'field': 'Quantity', 'filter': 'agNumberColumnFilter', 'minWidth': 130}, {'field': 'ExecutionPrice', 'headerName': 'Execution ($)', 'filter': 'agNumberColumnFilter', 'valueFormatter': {'function': "d3.format(',.2f')(params.value)"}, 'minWidth': 160}, {'field': 'MarkPrice', 'headerName': 'Reference mark ($)', 'filter': 'agNumberColumnFilter', 'valueFormatter': {'function': "d3.format(',.2f')(params.value)"}, 'minWidth': 190}, {'field': 'Strategy', 'minWidth': 150}, {'field': 'Sector', 'minWidth': 240}, {'field': 'PnL', 'headerName': 'Mark P&L ($)', 'filter': 'agNumberColumnFilter', 'valueFormatter': {'function': "d3.format('+.2f')(params.value)"}, 'cellStyle': {'styleConditions': [{'condition': 'params.value > 0', 'style': {'color': '#45dfc0'}}, {'condition': 'params.value < 0', 'style': {'color': '#ff8b8b'}}]}, 'minWidth': 160}, {'field': 'ReviewFlag', 'headerName': 'Booking review', 'minWidth': 280}]
layout = html.Div([html.Div('PROJECT 04 / TRADE OPERATIONS', className='eyebrow'), html.H1('Trade Blotter & Risk Report'), html.P('Review daily bookings, investigate exceptions and prepare a trade-level risk report.', className='intro'), html.Div([html.H3('Load Daily Trades'), html.P('Upload a UTF-8 CSV containing one UTC trade date, up to 5,000 bookings and 2 MB. USD equities only.'), html.P('Required columns: TradeID, Timestamp, Ticker, Side, Quantity, ExecutionPrice, MarkPrice, Strategy, Sector. Use ISO timestamps such as 2026-10-23 09:05:00. Timestamps without an offset are treated as UTC.'), dcc.Upload(id='blotter-upload', children=html.Button('Choose trade CSV', className='button'), accept='.csv', multiple=False), html.Button('Restore demo trades', id='blotter-reset', n_clicks=0, className='button', style={'marginLeft': '15px'}), html.Button('Download sample CSV', id='blotter-sample-button', n_clicks=0, className='button', style={'marginLeft': '15px'}), dcc.Download(id='blotter-sample-download'), html.P('Current source: DEMO — synthetic bookings and prices.', id='blotter-source')], className='panel'), html.Div([html.H3('Booking Summary'), html.Div(id='blotter-stats'), html.P('Mark P&L = signed quantity × (reference mark − execution price). Buys are positive quantity; sells are negative. Excludes opening positions, fees, financing and FX. It does not separate realised and unrealised account P&L.'), html.P('Potential duplicates are flagged for review, never automatically removed. Totals and charts include every booking, including flagged rows. Grid filters do not change these full-dataset summaries.')], className='panel'), html.Div([html.H3('Trade Bookings'), html.P('All quantities are positive; Side determines buy or sell. Reference marks must use a consistent valuation time. USD only.'), dcc.Store(id='blotter-data', data=sample_trades.to_dict('records')), dag.AgGrid(id='blotter-grid', rowData=sample_trades.to_dict('records'), columnDefs=columns, defaultColDef={'sortable': True, 'filter': 'agTextColumnFilter', 'floatingFilter': True, 'resizable': True}, dashGridOptions={'pagination': True, 'paginationPageSize': 25, 'paginationPageSizeSelector': False, 'animateRows': False, 'theme': {'function': "themeQuartz.withParams({backgroundColor: '#142238',foregroundColor: '#edf3fc',headerBackgroundColor: '#091321',accentColor: '#45dfc0',browserColorScheme: 'dark'})"}}, style={'height': '550px', 'width': '100%'}), html.P('Scroll horizontally inside the grid to see strategy and sector. Click headings to sort or use the filter boxes below them.')], className='panel'), html.Div([dcc.Graph(id='blotter-strategy-chart', config={'displaylogo': False}), dcc.Graph(id='blotter-sector-chart', config={'displaylogo': False})], className='panel'), html.Div([html.H3('Download Risk Report'), html.P('Generate a standalone HTML report for all loaded bookings. Includes flagged rows; grid filters do not affect the report.'), html.Button('Download HTML risk report', id='blotter-report-button', n_clicks=0, className='button'), dcc.Download(id='blotter-report-download')], className='panel')])

def analyse_bookings(records):
    frame = pd.DataFrame(records).copy()
    signed_quantity = frame['Quantity'].where(frame['Side'] == 'Buy', -frame['Quantity'])
    frame['PnL'] = signed_quantity * (frame['MarkPrice'] - frame['ExecutionPrice'])
    repeated_id = frame.duplicated('TradeID', keep=False)
    matching_booking = frame.duplicated(['Timestamp', 'Ticker', 'Side', 'Quantity', 'ExecutionPrice', 'Strategy', 'Sector'], keep=False)
    frame['ReviewFlag'] = ['Repeated ID + matching booking' if id_flag and match_flag else 'Repeated trade ID' if id_flag else 'Matching booking — review' if match_flag else 'No match detected' for id_flag, match_flag in zip(repeated_id, matching_booking)]
    frame['PotentialDuplicate'] = repeated_id | matching_booking
    return frame

@dash.callback(dash.Output('blotter-grid', 'rowData'), dash.Output('blotter-stats', 'children'), dash.Output('blotter-strategy-chart', 'figure'), dash.Output('blotter-sector-chart', 'figure'), dash.Input('blotter-data', 'data'))
def update_blotter_analysis(records):
    import plotly.graph_objects as go
    frame = analyse_bookings(records)
    total_pnl = frame['PnL'].sum()
    flagged = int(frame['PotentialDuplicate'].sum())
    stats = html.Div([html.H2(f'Mark P&L: ${total_pnl:+,.2f}', style={'color': '#45dfc0' if total_pnl >= 0 else '#ff8b8b'}), html.P(f'{len(frame)} bookings | {flagged} rows flagged for duplicate review'), html.P('Flags identify exact matches on booking fields or repeated trade IDs. Legitimate separate fills can match, and duplicates with changed fields may escape detection.')])
    figures = []
    for column in ['Strategy', 'Sector']:
        grouped = frame.groupby(column)['PnL'].sum().sort_values()
        fig = go.Figure(go.Bar(x=grouped.values.tolist(), y=grouped.index.tolist(), orientation='h', marker_color=['#45dfc0' if value >= 0 else '#ff8b8b' for value in grouped.values], hovertemplate='%{y}: $%{x:,.2f}<extra></extra>'))
        fig.update_layout(title=f'Mark P&L by {column.lower()} — all bookings', template='plotly_dark', paper_bgcolor='#142238', plot_bgcolor='#142238', height=400, xaxis_title='Mark P&L ($)', margin=dict(l=180, r=30, t=65, b=55))
        figures.append(fig)
    return (frame.to_dict('records'), stats, figures[0], figures[1])

@dash.callback(dash.Output('blotter-data', 'data'), dash.Output('blotter-source', 'children'), dash.Input('blotter-upload', 'contents'), dash.Input('blotter-reset', 'n_clicks'), prevent_initial_call=True)
def load_daily_trades(contents, reset_clicks):
    import base64
    import io
    import numpy as np
    if dash.ctx.triggered_id == 'blotter-reset':
        return (sample_trades.to_dict('records'), 'Current source: DEMO — synthetic bookings and prices.')
    if not contents:
        return (dash.no_update, dash.no_update)
    try:
        encoded = contents.split(',', 1)[1]
        if len(encoded) > 2800000:
            raise ValueError('File exceeds the 2 MB limit.')
        decoded = base64.b64decode(encoded, validate=True)
        if len(decoded) > 2000000:
            raise ValueError('File exceeds the 2 MB limit.')
        frame = pd.read_csv(io.StringIO(decoded.decode('utf-8-sig')), dtype=str, keep_default_na=False)
        required = sample_trades.columns.tolist()
        missing = [name for name in required if name not in frame.columns]
        if missing:
            raise ValueError('Missing columns: ' + ', '.join(missing))
        if not 1 <= len(frame) <= 5000:
            raise ValueError('Upload between 1 and 5,000 bookings.')
        frame = frame[required].copy()
        for name in required:
            frame[name] = frame[name].str.strip()
        if (frame == '').any().any():
            raise ValueError('Required fields cannot be empty.')
        frame['Side'] = frame['Side'].str.title()
        if not frame['Side'].isin(['Buy', 'Sell']).all():
            raise ValueError('Side must be Buy or Sell.')
        frame['Ticker'] = frame['Ticker'].str.upper()
        for name in ['Quantity', 'ExecutionPrice', 'MarkPrice']:
            frame[name] = pd.to_numeric(frame[name], errors='coerce')
            if not np.isfinite(frame[name].to_numpy()).all():
                raise ValueError(f'{name} must contain finite numbers.')
        if (frame['Quantity'] <= 0).any():
            raise ValueError('Quantities must be positive.')
        if (frame[['ExecutionPrice', 'MarkPrice']] <= 0).any().any():
            raise ValueError('Execution prices and marks must be positive.')
        timestamps = pd.to_datetime(frame['Timestamp'], format='mixed', errors='coerce', utc=True)
        if timestamps.isna().any():
            raise ValueError('Invalid timestamp. Use ISO date and time.')
        if timestamps.dt.date.nunique() != 1:
            raise ValueError('All trades must share one UTC trade date.')
        frame['Timestamp'] = timestamps.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        if (frame.groupby('Ticker')['MarkPrice'].nunique() > 1).any():
            raise ValueError('Use one reference mark per ticker.')
        if (frame.groupby('Ticker')['Sector'].nunique() > 1).any():
            raise ValueError('Use one sector label per ticker.')
        trade_date = timestamps.iloc[0].strftime('%d %b %Y')
        return (frame.to_dict('records'), f'Current source: UPLOADED CSV | {len(frame)} bookings | Trade date: {trade_date} UTC | Currency: USD')
    except Exception as error:
        return (dash.no_update, f'Upload rejected: {error} Previously loaded data remains active.')

@dash.callback(dash.Output('blotter-sample-download', 'data'), dash.Input('blotter-sample-button', 'n_clicks'), prevent_initial_call=True)
def download_sample_trades(clicks):
    if not clicks:
        return dash.no_update
    return dcc.send_data_frame(sample_trades.to_csv, 'sample_trade_bookings.csv', index=False)

@dash.callback(dash.Output('blotter-report-download', 'data'), dash.Input('blotter-report-button', 'n_clicks'), dash.State('blotter-data', 'data'), prevent_initial_call=True)
def download_blotter_report(clicks, records):
    from datetime import datetime, timezone
    from html import escape
    if not clicks or not records:
        return dash.no_update
    frame = analyse_bookings(records)
    frame['BookedNotional'] = frame['Quantity'] * frame['ExecutionPrice']
    frame['SignedBookedNotional'] = frame['BookedNotional'].where(frame['Side'] == 'Buy', -frame['BookedNotional'])
    flagged = frame.loc[frame['PotentialDuplicate']].copy()
    total_pnl = float(frame['PnL'].sum())
    gross_notional = float(frame['BookedNotional'].sum())
    net_notional = float(frame['SignedBookedNotional'].sum())
    by_strategy = frame.groupby('Strategy', as_index=False).agg(Bookings=('TradeID', 'size'), MarkPnL=('PnL', 'sum'), GrossBookedNotional=('BookedNotional', 'sum'))
    by_sector = frame.groupby('Sector', as_index=False).agg(Bookings=('TradeID', 'size'), MarkPnL=('PnL', 'sum'), GrossBookedNotional=('BookedNotional', 'sum'))
    by_ticker = frame.groupby('Ticker', as_index=False).agg(Bookings=('TradeID', 'size'), GrossBookedNotional=('BookedNotional', 'sum'), SignedBookedNotional=('SignedBookedNotional', 'sum'))
    by_ticker['ShareOfGrossBookedNotionalPct'] = by_ticker['GrossBookedNotional'] / gross_notional * 100
    by_ticker = by_ticker.sort_values('GrossBookedNotional', ascending=False)
    generated = datetime.now(timezone.utc)
    trade_dates = sorted(pd.to_datetime(frame['Timestamp'], format='mixed', utc=True).dt.strftime('%Y-%m-%d').unique().tolist())
    original_columns = sample_trades.columns.tolist()

    def normalised_demo(data):
        copy = data[original_columns].copy()
        copy['Timestamp'] = pd.to_datetime(copy['Timestamp'], format='mixed', utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        return copy.sort_values('TradeID').reset_index(drop=True)
    matches_demo = normalised_demo(frame).equals(normalised_demo(sample_trades))
    provenance = 'Matches the supplied synthetic demo dataset.' if matches_demo else 'User-supplied dataset; not independently verified.'

    def table(data):
        return data.to_html(index=False, border=0, escape=True, float_format=lambda value: f'{value:,.2f}')
    flag_table = table(flagged[['TradeID', 'Timestamp', 'Ticker', 'Side', 'Quantity', 'ExecutionPrice', 'PnL', 'ReviewFlag']]) if not flagged.empty else '<p>No potential duplicates detected by these rules.</p>'
    css = '\n    body {\n        font-family: Arial, sans-serif;\n        background: #091321;\n        color: #edf3fc;\n        max-width: 1300px;\n        margin: auto;\n        padding: 35px;\n        line-height: 1.6;\n    }\n    h1, h2 { color: #45dfc0; }\n    section {\n        background: #142238;\n        padding: 22px;\n        margin: 22px 0;\n        border-radius: 12px;\n        overflow-x: auto;\n    }\n    table { border-collapse: collapse; width: 100%; }\n    th, td {\n        padding: 10px;\n        border-bottom: 1px solid #30415a;\n        text-align: left;\n        white-space: nowrap;\n    }\n    .warning { color: #ffbb73; }\n    @media print {\n        body { background: white; color: black; padding: 0; }\n        section { background: white; border: 1px solid #ccc; }\n        h1, h2 { color: #123f46; }\n        .warning { color: #754300; }\n    }\n    '
    document = f"""<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Markets Lab — Trade Risk Report</title>\n<style>{css}</style>\n</head>\n<body>\n<h1>Trade Blotter &amp; Risk Report</h1>\n<p>Jordan's Markets Lab</p>\n<p>Generated: {generated:%Y-%m-%d %H:%M:%S UTC}</p>\n<p>Trade date(s): {escape(', '.join(trade_dates))} | Currency: USD</p>\n<p>{escape(provenance)}</p>\n\n<section>\n<h2>Booking Summary</h2>\n<p>Bookings: <strong>{len(frame)}</strong></p>\n<p>Mark P&amp;L: <strong>${total_pnl:+,.2f}</strong></p>\n<p>Rows flagged for review: <strong>{len(flagged)}</strong></p>\n<p>Gross booked execution notional: ${gross_notional:,.2f}</p>\n<p>Net signed booked execution notional: ${net_notional:+,.2f}</p>\n<p class="warning">\nAll totals include potential duplicate bookings. Flags require\ninvestigation; no bookings have been removed.\n</p>\n</section>\n\n<section>\n<h2>P&amp;L by Strategy</h2>\n{table(by_strategy)}\n</section>\n\n<section>\n<h2>P&amp;L by Sector</h2>\n{table(by_sector)}\n</section>\n\n<section>\n<h2>Booking Concentration by Ticker</h2>\n{table(by_ticker)}\n<p>Concentration uses gross execution notionals.\nThese figures describe bookings, not full portfolio positions.</p>\n</section>\n\n<section>\n<h2>Potential Duplicate Bookings</h2>\n{flag_table}\n<p>Checks repeated trade IDs and exact matches on timestamp, ticker,\nside, quantity, execution price, strategy and sector.\nEvery member of a matching group is flagged.\nLegitimate separate fills may match; altered duplicates may not.</p>\n</section>\n\n<section>\n<h2>All Bookings</h2>\n{table(frame)}\n</section>\n\n<section>\n<h2>Methodology &amp; Limitations</h2>\n<p>Mark P&amp;L = signed quantity ×\n(reference mark − execution price).\nBuys have positive signed quantity; sells have negative signed quantity.</p>\n<p>This is trade-level mark contribution, not a full account P&amp;L\nreconciliation. Opening positions, fees, financing, taxes and FX\nare excluded. Realised and unrealised account P&amp;L are not separated.</p>\n<p>Gross booked notional sums quantity × execution price.\nNet signed booked notional applies the trade side.\nNeither is a measure of current portfolio exposure.</p>\n<p>Reference marks are user-supplied and must share a consistent\nvaluation time. The report does not verify their market accuracy.</p>\n<p>This report contains all loaded bookings, regardless of grid filters.\nIt does not calculate VaR, liquidity risk or counterparty exposure.</p>\n</section>\n</body>\n</html>"""
    return {'content': document, 'filename': f'markets_lab_risk_report_{generated:%Y%m%d_%H%M%S}.html', 'type': 'text/html', 'base64': False}
