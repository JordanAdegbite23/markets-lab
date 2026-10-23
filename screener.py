import dash_ag_grid as dag
import dash
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone
from dash import Input, Output, dcc, html
dash.register_page(__name__, path='/screener', name='Market Screener')
SECTORS = {'AAPL': 'Information Technology', 'MSFT': 'Information Technology', 'GOOGL': 'Communication Services', 'META': 'Communication Services', 'AMZN': 'Consumer Discretionary', 'HD': 'Consumer Discretionary', 'PG': 'Consumer Staples', 'KO': 'Consumer Staples', 'JPM': 'Financials', 'GS': 'Financials', 'JNJ': 'Health Care', 'MRK': 'Health Care', 'CAT': 'Industrials', 'HON': 'Industrials', 'XOM': 'Energy', 'CVX': 'Energy', 'NEE': 'Utilities', 'DUK': 'Utilities', 'LIN': 'Materials', 'APD': 'Materials', 'PLD': 'Real Estate', 'AMT': 'Real Estate'}
CONTROL = {'color': '#091321', 'minWidth': '220px', 'flex': '1'}
layout = html.Div([html.Div('PROJECT 03 / MARKET MONITORING', className='eyebrow'), html.H1('Market Screener'), html.P('Scan a curated US stock universe by sector and historical performance. Prices are in USD.', className='intro'), dcc.Store(id='screen-data'), html.Div([html.Button('Refresh Yahoo data', id='screen-refresh', n_clicks=0, className='button'), html.P(id='screen-status'), html.Div([html.Div([html.Label('Sector'), dcc.Dropdown(id='screen-sector', options=['All sectors'] + sorted(set(SECTORS.values())), value='All sectors', clearable=False, style=CONTROL)], style={'flex': '1'}), html.Div([html.Label('Sort by'), dcc.Dropdown(id='screen-sort', options=[{'label': 'Ticker', 'value': 'Ticker'}, {'label': 'Price', 'value': 'Price'}, {'label': '1-day return', 'value': '1D'}, {'label': '1-month return', 'value': '1M'}, {'label': '3-month return', 'value': '3M'}, {'label': 'YTD return', 'value': 'YTD'}, {'label': 'Momentum score', 'value': 'Momentum'}, {'label': 'Universe rank', 'value': 'Rank'}], value='Momentum', clearable=False, style=CONTROL)], style={'flex': '1'}), html.Div([html.Label('Order'), dcc.Dropdown(id='screen-order', options=['Highest first', 'Lowest first'], value='Highest first', clearable=False, style=CONTROL)], style={'flex': '1'})], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px', 'marginTop': '25px'})], className='panel'), dcc.Loading(html.Div(id='screen-table', className='panel', style={'overflowX': 'auto'})), html.Div([html.H3('Sector Groups & Averages'), html.P("Expandable groups based on the stocks matching your current grid filters, across all pages. Each sector's figures are simple averages of its included stocks."), html.Div(id='screen-sector-groups'), html.P('These are sample averages, not sector-index returns. Momentum averages are scores, not investment returns.')], className='panel'), html.Div([html.H3('Sector Performance Heatmap'), html.P('Equal-weight average return of the available stocks in each sector of this curated universe. Click a sector to filter the stock table.'), dcc.Dropdown(id='screen-heat-period', options=[{'label': '1 trading session', 'value': '1D'}, {'label': '21 trading sessions', 'value': '1M'}, {'label': '63 trading sessions', 'value': '3M'}], value='1D', clearable=False, style={'color': '#091321', 'maxWidth': '350px', 'marginBottom': '20px'}), dcc.Graph(id='screen-heatmap', config={'displaylogo': False}), html.P('Green indicates positive returns; red indicates negative returns. Colour intensity scales within the selected period. Stock counts are shown beside each sector. This is not a market-cap-weighted sector index.')], className='panel'), html.Div([html.H3('Data & methodology'), html.P('Yahoo Finance adjusted daily closes. Returns use 1, 21 and 63 trading-session intervals. The latest daily bar may include an unfinished session. Prices can differ from unadjusted quoted closes.'), html.P("Sector labels are assigned in this project's curated universe. Two stocks per sector do not represent a complete sector or a sector index.")], className='panel', style={'color': '#a4b4ca', 'lineHeight': '1.7'})])

@dash.callback(Output('screen-data', 'data'), Output('screen-status', 'children'), Input('screen-refresh', 'n_clicks'))
def fetch_screener_data(clicks):
    try:
        raw = yf.download(list(SECTORS), period='2y', interval='1d', auto_adjust=True, progress=False, threads=False, timeout=15)
        if raw is None or raw.empty:
            raise ValueError('Yahoo returned no data.')
        close = raw['Close'].reindex(columns=list(SECTORS))
        records = []
        skipped = []
        today_us = pd.Timestamp.now(tz='America/New_York').date()
        close = close.loc[[date.date() < today_us for date in close.index]]
        if close.empty:
            raise ValueError('No previous-session data available.')
        latest_date = close.dropna(how='all').index[-1]
        for ticker, sector in SECTORS.items():
            prices = close[ticker].dropna()
            if len(prices) < 64 or prices.index[-1] != latest_date or (not np.isfinite(prices.to_numpy()).all()) or (prices <= 0).any():
                skipped.append(ticker)
                continue
            previous_year = prices.loc[prices.index.year < latest_date.year]
            if previous_year.empty:
                skipped.append(ticker)
                continue
            ytd_return = (float(prices.iloc[-1]) / float(previous_year.iloc[-1]) - 1) * 100
            latest = float(prices.iloc[-1])
            records.append({'Ticker': ticker, 'Sector': sector, 'Price': latest, '1D': (latest / float(prices.iloc[-2]) - 1) * 100, '1M': (latest / float(prices.iloc[-22]) - 1) * 100, '3M': (latest / float(prices.iloc[-64]) - 1) * 100, 'Date': str(latest_date.date()), 'YTD': ytd_return})
        if not records:
            raise ValueError('No stocks had sufficient current data.')
        fetched = datetime.now(timezone.utc).strftime('%H:%M UTC')
        message = f'{len(records)} of {len(SECTORS)} stocks loaded | Latest included session: {latest_date:%d %b %Y} | Fetched {fetched}'
        if skipped:
            message += ' | Excluded: ' + ', '.join(skipped)
        return (add_momentum(records), message)
    except Exception as error:
        return ([], f'Data unavailable: {error}. Try Refresh Yahoo data.')

@dash.callback(Output('screen-table', 'children'), Input('screen-data', 'data'), Input('screen-sector', 'value'), Input('screen-sort', 'value'), Input('screen-order', 'value'))
def show_screener_table(records, sector, sort_by, order):
    import dash_ag_grid as dag
    if not records:
        return html.P('No data to display. Check the data status above.')
    frame = pd.DataFrame(records)
    if sector != 'All sectors':
        frame = frame.loc[frame['Sector'] == sector]
    frame = frame.sort_values(sort_by, ascending=order == 'Lowest first')
    return_style = {'styleConditions': [{'condition': 'params.value > 0', 'style': {'color': '#45dfc0'}}, {'condition': 'params.value < 0', 'style': {'color': '#ff8b8b'}}]}
    columns = [{'field': 'Ticker', 'pinned': 'left', 'filter': 'agTextColumnFilter', 'minWidth': 110}, {'field': 'Sector', 'filter': 'agTextColumnFilter', 'minWidth': 230}, {'field': 'Price', 'headerName': 'Adjusted close ($)', 'filter': 'agNumberColumnFilter', 'valueFormatter': {'function': "d3.format(',.2f')(params.value)"}, 'minWidth': 175}]
    for period in ['1D', '1M', '3M']:
        columns.append({'field': period, 'headerName': f'{period} (%)', 'filter': 'agNumberColumnFilter', 'valueFormatter': {'function': "d3.format('+.2f')(params.value)"}, 'cellStyle': return_style, 'minWidth': 125})
    columns.append({'field': 'Date', 'headerName': 'Data date', 'filter': 'agTextColumnFilter', 'minWidth': 150})
    columns.extend([{'field': 'YTD', 'headerName': 'YTD (%)', 'filter': 'agNumberColumnFilter', 'valueFormatter': {'function': "d3.format('+.2f')(params.value)"}, 'cellStyle': return_style, 'minWidth': 130}, {'field': 'Momentum', 'headerName': 'Momentum score', 'filter': 'agNumberColumnFilter', 'valueFormatter': {'function': "d3.format('+.2f')(params.value)"}, 'cellStyle': return_style, 'minWidth': 180}, {'field': 'Rank', 'headerName': 'Universe rank', 'filter': 'agNumberColumnFilter', 'minWidth': 150}])
    return html.Div([html.Button('Download filtered CSV', id='screen-export-button', n_clicks=0, className='button', style={'marginBottom': '20px'}), html.P('Click a heading to sort. Use the boxes below headings to filter. Number filters accept percentage-point values: enter 5 for 5%. Changing the top dropdowns resets grid filters.'), dag.AgGrid(className='ag-theme-alpine-dark', id='screen-grid', rowData=frame.to_dict('records'), columnDefs=columns, defaultColDef={'sortable': True, 'resizable': True, 'filter': True, 'floatingFilter': True, 'useValueFormatterForExport': False}, dashGridOptions={'pagination': True, 'paginationPageSize': 25, 'paginationPageSizeSelector': False, 'animateRows': False}, style={'height': '620px', 'width': '100%'}, csvExportParams={'fileName': 'markets_lab_filtered_stocks.csv'})])

@dash.callback(Output('screen-heatmap', 'figure'), Input('screen-data', 'data'), Input('screen-heat-period', 'value'))
def draw_sector_heatmap(records, period):
    import plotly.graph_objects as go
    fig = go.Figure()
    if records:
        frame = pd.DataFrame(records)
        grouped = frame.groupby('Sector')[period].agg(['mean', 'count']).sort_values('mean', ascending=False)
        sectors = grouped.index.tolist()
        averages = grouped['mean'].tolist()
        counts = grouped['count'].tolist()
        scale = max(max((abs(value) for value in averages)), 0.01)
        fig.add_trace(go.Heatmap(x=[period], y=sectors, z=[[value] for value in averages], text=[[f'{value:+.2f}% | {count} stocks'] for value, count in zip(averages, counts)], texttemplate='%{text}', zmin=-scale, zmax=scale, colorscale=[[0, '#b84256'], [0.5, '#142238'], [1, '#239d84']], colorbar=dict(title='Return (%)'), hovertemplate='%{y}<br>%{text}<extra></extra>'))
    fig.update_layout(title=f'Sector sample performance — {period}', template='plotly_dark', paper_bgcolor='#142238', plot_bgcolor='#142238', height=650, margin=dict(l=185, r=35, t=70, b=40))
    fig.update_yaxes(autorange='reversed')
    return fig

@dash.callback(Output('screen-sector', 'value'), Input('screen-heatmap', 'clickData'), prevent_initial_call=True)
def filter_from_heatmap(click):
    if not click or not click.get('points'):
        return dash.no_update
    sector = click['points'][0].get('y')
    return sector if sector in SECTORS.values() else dash.no_update

def add_momentum(records):
    frame = pd.DataFrame(records)
    frame['Momentum'] = frame['1M'] + frame['3M'] + frame['YTD']
    frame['Rank'] = frame['Momentum'].rank(method='min', ascending=False).astype(int)
    return frame.to_dict('records')

@dash.callback(Output('screen-grid', 'exportDataAsCsv'), Input('screen-export-button', 'n_clicks'), prevent_initial_call=True)
def export_filtered_stocks(clicks):
    return True if clicks else dash.no_update

@dash.callback(Output('screen-sector-groups', 'children'), Input('screen-grid', 'virtualRowData'))
def display_sector_groups(rows):
    if rows is None:
        return html.P('Sector groups will appear after the grid loads.')
    if not rows:
        return html.P('No stocks match the current filters.')
    frame = pd.DataFrame(rows)
    metrics = [name for name in ['1D', '1M', '3M', 'YTD', 'Momentum'] if name in frame.columns]
    groups = []

    def format_value(name, value):
        suffix = ' points' if name == 'Momentum' else '%'
        return f'{value:+.2f}{suffix}'
    for sector, stocks in frame.groupby('Sector', sort=True):
        averages = stocks[metrics].mean()
        summary_text = ' | '.join((f'{name}: {format_value(name, averages[name])}' for name in metrics))
        stock_rows = []
        for _, stock in stocks.sort_values('Ticker').iterrows():
            stock_rows.append(html.Tr([html.Td(stock['Ticker'])] + [html.Td(format_value(name, stock[name])) for name in metrics]))
        groups.append(html.Details([html.Summary(f'{sector} — {len(stocks)} stocks', style={'cursor': 'pointer', 'fontWeight': 'bold', 'color': '#45dfc0'}), html.P('Sector averages: ' + summary_text), html.Div(html.Table([html.Thead(html.Tr([html.Th('Ticker')] + [html.Th(name) for name in metrics])), html.Tbody(stock_rows)]), style={'overflowX': 'auto'})], style={'padding': '18px', 'borderBottom': '1px solid #30415a'}))
    return groups
