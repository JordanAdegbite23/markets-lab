from implied_volatility import option_price as surface_price
from implied_volatility import implied_volatility
import dash
import math
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import norm
from dash import Dash, Input, Output, dcc, html
from greeks import calculate_greeks
NAVY = '#091321'
PANEL = '#142238'
TEAL = '#45dfc0'
ORANGE = '#ffbb73'
TEXT = '#edf3fc'

def option_prices(spot, strike, volatility, rate, years):
    d1 = (math.log(spot / strike) + (rate + 0.5 * volatility ** 2) * years) / (volatility * math.sqrt(years))
    d2 = d1 - volatility * math.sqrt(years)
    discounted_strike = strike * math.exp(-rate * years)
    call = spot * norm.cdf(d1) - discounted_strike * norm.cdf(d2)
    put = discounted_strike * norm.cdf(-d2) - spot * norm.cdf(-d1)
    return (call, put)

def slider(label, slider_id, minimum, maximum, step, value, marks):
    return html.Div([html.H3(label), dcc.Slider(id=slider_id, min=minimum, max=maximum, step=step, value=value, marks=marks, tooltip={'placement': 'bottom', 'always_visible': True}, updatemode='mouseup')], style={'marginBottom': '42px'})
layout = html.Div([html.Div('JORDAN / MARKETS & ANALYTICS', style={'color': TEAL, 'letterSpacing': '3px'}), html.H1('Options Lab', style={'fontSize': '42px'}), html.P('Black–Scholes Options Pricer & Greeks Visualiser', style={'color': '#a4b4ca'}), html.Div([html.Div([html.Div('CALL / SHARE'), html.H2(id='call-price')], className='panel price'), html.Div([html.Div('PUT / SHARE'), html.H2(id='put-price')], className='panel price')], className='prices'), html.Div([html.H3('Implied Volatility Calculator'), html.P("Enter an option's market price per share. This uses the spot, strike, interest rate and expiry sliders below. The volatility slider does not affect this calculation."), html.Label('Option type'), dcc.Dropdown(id='iv-option-type', options=['Call', 'Put'], value='Call', clearable=False, searchable=False, style={'color': '#091321', 'maxWidth': '300px', 'marginBottom': '20px'}), html.Label('Market price ($ per share)'), html.Br(), dcc.Input(id='iv-market-price', type='number', min=0, step=0.01, value=10.45, debounce=True, style={'padding': '12px', 'marginTop': '10px', 'fontSize': '18px', 'maxWidth': '100%'}), html.Div(id='iv-result', style={'marginTop': '20px', 'color': '#45dfc0', 'lineHeight': '1.7'}), html.P('Press Enter or click outside the price box to calculate. Uses safeguarded Newton iteration under the same European, no-dividend assumptions as the pricer.')], className='panel'), html.Div([slider('Spot price ($)', 'spot', 10, 300, 1, 100, {10: '$10', 100: '$100', 200: '$200', 300: '$300'}), slider('Strike price ($)', 'strike', 10, 300, 1, 100, {10: '$10', 100: '$100', 200: '$200', 300: '$300'}), slider('Annual volatility (%)', 'volatility', 1, 100, 1, 20, {1: '1%', 25: '25%', 50: '50%', 100: '100%'}), slider('Annual interest rate (%)', 'rate', -5, 15, 0.25, 5, {-5: '-5%', 0: '0%', 5: '5%', 10: '10%', 15: '15%'}), slider('Time to expiry (days)', 'days', 1, 730, 1, 365, {1: '1', 180: '180', 365: '365', 730: '730'})], className='panel'), html.Div([html.H3('Greeks at selected inputs'), html.Div(id='greeks-table')], className='panel'), dcc.Graph(id='price-chart', config={'displaylogo': False}), dcc.Graph(id='greeks-chart', config={'displaylogo': False}), html.Div([html.H3('Model assumptions & units'), html.P('European options with no dividends. Constant volatility and continuously compounded interest rate. Time uses calendar days / 365.'), html.P('Prices and Greeks refer to one underlying share. Delta: price sensitivity per $1 spot move. Gamma: delta sensitivity per $1 spot move. Vega: price sensitivity per 1 percentage-point volatility increase. Theta: price sensitivity per calendar day passing. Rho: price sensitivity per 1 percentage-point interest-rate increase.'), html.P('Curves vary spot while holding the other inputs fixed. Sliders recalculate on release. Model estimates only; no live market feed.')], className='panel', style={'color': '#a4b4ca', 'lineHeight': '1.7'}), html.Div([html.H3('3D Option P&L Surface'), html.P('A hypothetical long option bought at the model price from the main sliders. The surface varies future spot and volatility, holding strike and interest rate fixed.'), dcc.Dropdown(id='pnl-kind', options=['Call', 'Put'], value='Call', clearable=False, searchable=False, style={'color': '#091321', 'maxWidth': '300px', 'marginBottom': '25px'}), html.H4('Percentage of original time elapsed'), dcc.Slider(id='pnl-elapsed', min=0, max=100, step=5, value=50, marks={0: 'Today', 25: '25%', 50: '50%', 75: '75%', 100: 'Expiry'}, tooltip={'placement': 'bottom', 'always_visible': True}, updatemode='mouseup'), html.P(id='pnl-summary', style={'marginTop': '30px'}), dcc.Graph(id='pnl-surface', config={'displaylogo': False}), html.P('P&L per share = scenario option value minus initial model premium. Excludes financing costs, fees and taxes. Changing a main slider resets the hypothetical entry assumptions. Drag the chart to rotate it.')], className='panel'), html.Div([html.H3('Multi-Leg Strategies'), html.P('Compare combined expiry payoffs and profit or loss. Entry premiums use the main pricing sliders. All legs share the same expiry and volatility.'), dcc.Dropdown(id='strategy-choice', options=[{'label': 'Bull call spread', 'value': 'spread'}, {'label': 'Long straddle', 'value': 'straddle'}, {'label': 'Long call butterfly', 'value': 'butterfly'}], value='spread', clearable=False, searchable=False, style={'color': '#091321', 'maxWidth': '400px', 'marginBottom': '25px'}), html.H4('Strike spacing (% of main strike)'), dcc.Slider(id='strategy-width', min=1, max=50, step=1, value=10, marks={1: '1%', 10: '10%', 25: '25%', 50: '50%'}, tooltip={'placement': 'bottom', 'always_visible': True}, updatemode='mouseup'), html.P('Spacing applies to the spread and butterfly. The straddle uses the main strike for both legs.', style={'marginTop': '30px'}), html.Div(id='strategy-summary'), dcc.Graph(id='strategy-chart', config={'displaylogo': False}), html.P('Values are per share-equivalent strategy unit: quantities are shown in the leg description. Contract multipliers are not applied. Excludes fees, financing and taxes. Changing main sliders reprices the hypothetical entry.')], className='panel'), html.Div([html.H3('Monte Carlo Exotic Options'), html.P('Uses the main spot, strike, volatility, interest rate and expiry sliders. Choose an option and click Run.'), dcc.Dropdown(id='mc-kind', options=['Digital call', 'Down-and-out call'], value='Digital call', clearable=False, searchable=False, style={'color': '#091321', 'maxWidth': '400px', 'marginBottom': '20px'}), html.Label('Barrier level ($) — barrier call only'), html.Br(), dcc.Input(id='mc-barrier', type='number', min=0.01, value=80, step=1, style={'padding': '10px', 'margin': '10px 0 20px'}), html.Br(), html.Label('Cash payout ($) — digital call only'), html.Br(), dcc.Input(id='mc-cash', type='number', min=0.01, value=10, step=1, style={'padding': '10px', 'margin': '10px 0 20px'}), html.Br(), html.Label('Number of simulated paths'), dcc.Dropdown(id='mc-paths', options=[{'label': '5,000 — quick', 'value': 5000}, {'label': '20,000 — standard', 'value': 20000}, {'label': '50,000 — more precise', 'value': 50000}], value=20000, clearable=False, searchable=False, style={'color': '#091321', 'maxWidth': '400px', 'margin': '10px 0 20px'}), html.Button('Run simulation', id='mc-run', n_clicks=0, style={'background': '#45dfc0', 'color': '#091321', 'padding': '14px 22px', 'border': '0', 'borderRadius': '8px', 'fontWeight': 'bold', 'cursor': 'pointer'}), dcc.Loading(html.Div(id='mc-result', children='Click Run simulation to calculate a price.', style={'marginTop': '25px', 'lineHeight': '1.8'})), html.P('Results describe the last run. After changing any inputs, click Run again. A fixed random seed makes runs reproducible.'), html.P('European exercise, no dividends and constant model inputs. Digital pays the specified cash amount only if terminal spot exceeds strike. Down-and-out call has no rebate and is monitored initially and approximately daily; barrier crossings between observations are not detected.'), html.P('The approximate 95% interval measures Monte Carlo sampling uncertainty, not model risk or barrier-monitoring error.')], className='panel')], style={'maxWidth': '1200px', 'margin': 'auto', 'padding': '30px'})

def style_chart(fig, title, height):
    fig.update_layout(title=title, template='plotly_dark', paper_bgcolor=NAVY, plot_bgcolor=PANEL, font=dict(family='Arial', color=TEXT), height=height, hovermode='x unified', margin=dict(l=70, r=35, t=80, b=65), legend=dict(orientation='h', y=1.08))
    return fig

@dash.callback(Output('call-price', 'children'), Output('put-price', 'children'), Output('greeks-table', 'children'), Output('price-chart', 'figure'), Output('greeks-chart', 'figure'), Input('spot', 'value'), Input('strike', 'value'), Input('volatility', 'value'), Input('rate', 'value'), Input('days', 'value'))
def update_dashboard(spot, strike, volatility, rate, days):
    sigma = volatility / 100
    interest = rate / 100
    years = days / 365
    call, put = option_prices(spot, strike, sigma, interest, years)
    selected = calculate_greeks(spot, strike, sigma, interest, years)
    names = ['Delta', 'Gamma', 'Vega', 'Theta', 'Rho']
    table = html.Table([html.Thead(html.Tr([html.Th('Greek'), html.Th('Call'), html.Th('Put')])), html.Tbody([html.Tr([html.Td(name), html.Td(f"{selected['Call'][name]:.4f}"), html.Td(f"{selected['Put'][name]:.4f}")]) for name in names])])
    spot_range = np.linspace(spot * 0.5, spot * 1.5, 200)
    prices = [option_prices(float(s), strike, sigma, interest, years) for s in spot_range]
    greeks = [calculate_greeks(float(s), strike, sigma, interest, years) for s in spot_range]
    price_fig = go.Figure()
    for index, option_type, color in [(0, 'Call', TEAL), (1, 'Put', ORANGE)]:
        price_fig.add_scatter(x=spot_range, y=[p[index] for p in prices], name=option_type, line=dict(color=color, width=3))
    price_fig.add_vline(x=spot, line_dash='dot', line_color=TEXT, annotation_text='Selected spot')
    style_chart(price_fig, 'Option prices across spot prices', 450)
    price_fig.update_xaxes(title_text='Spot price ($)')
    price_fig.update_yaxes(title_text='Option price ($ per share)')
    greek_fig = make_subplots(rows=5, cols=1, shared_xaxes=True, subplot_titles=names, vertical_spacing=0.07)
    units = ['Delta', 'Gamma', '$ / 1pp volatility', '$ / calendar day', '$ / 1pp interest rate']
    for row, (name, unit) in enumerate(zip(names, units), start=1):
        for option_type, color in [('Call', TEAL), ('Put', ORANGE)]:
            greek_fig.add_trace(go.Scatter(x=spot_range, y=[g[option_type][name] for g in greeks], name=option_type, legendgroup=option_type, showlegend=row == 1, line=dict(color=color, width=2)), row=row, col=1)
        greek_fig.add_vline(x=spot, line_dash='dot', line_color='#a4b4ca', row=row, col=1)
        greek_fig.update_yaxes(title_text=unit, row=row, col=1)
    greek_fig.update_xaxes(title_text='Spot price ($)', row=5, col=1)
    style_chart(greek_fig, 'Greeks across spot prices', 1400)
    return (f'${call:.2f}', f'${put:.2f}', table, price_fig, greek_fig)
dash.register_page(__name__, path='/options', name='Options & Greeks', layout=layout)

@dash.callback(Output('iv-result', 'children'), Input('iv-market-price', 'value'), Input('iv-option-type', 'value'), Input('spot', 'value'), Input('strike', 'value'), Input('rate', 'value'), Input('days', 'value'))
def update_implied_volatility(market_price, kind, spot, strike, rate, days):
    if market_price is None:
        return 'Enter a market price to calculate implied volatility.'
    try:
        volatility, iterations = implied_volatility(market_price=float(market_price), spot=spot, strike=strike, years=days / 365, rate=rate / 100, kind=kind)
        return f'Implied volatility: {volatility:.2%} | Solver iterations: {iterations}'
    except (ValueError, OverflowError, ZeroDivisionError) as error:
        return f'Cannot calculate: {error}'

@dash.callback(Output('pnl-surface', 'figure'), Output('pnl-summary', 'children'), Input('spot', 'value'), Input('strike', 'value'), Input('volatility', 'value'), Input('rate', 'value'), Input('days', 'value'), Input('pnl-kind', 'value'), Input('pnl-elapsed', 'value'))
def update_pnl_surface(spot, strike, volatility, rate, days, kind, elapsed):
    sigma = volatility / 100
    interest = rate / 100
    original_time = days / 365
    remaining_time = original_time * (1 - elapsed / 100)
    premium, _ = surface_price(spot, strike, original_time, interest, sigma, kind)
    spots = np.linspace(spot * 0.5, spot * 1.5, 45)
    volatilities = np.linspace(sigma * 0.5, sigma * 1.5, 35)
    values = []
    for scenario_vol in volatilities:
        row = []
        for scenario_spot in spots:
            if remaining_time <= 0:
                scenario_value = max(scenario_spot - strike, 0) if kind == 'Call' else max(strike - scenario_spot, 0)
            else:
                scenario_value, _ = surface_price(float(scenario_spot), strike, remaining_time, interest, float(scenario_vol), kind)
            row.append(float(scenario_value - premium))
        values.append(row)
    fig = go.Figure(go.Surface(x=spots.tolist(), y=(volatilities * 100).tolist(), z=values, colorscale='RdBu', cmid=0, colorbar=dict(title='P&L ($)'), hovertemplate='Spot: $%{x:.2f}<br>Volatility: %{y:.1f}%<br>P&L: $%{z:.2f}<extra></extra>'))
    fig.update_layout(title=f'Long {kind.lower()} — scenario P&L per share', template='plotly_dark', paper_bgcolor='#142238', height=650, margin=dict(l=10, r=10, t=65, b=10), scene=dict(xaxis_title='Scenario spot ($)', yaxis_title='Scenario volatility (%)', zaxis_title='P&L ($ per share)'))
    summary = f'Initial model premium: ${premium:.2f} per share | Time remaining: {days * (1 - elapsed / 100):.1f} days'
    return (fig, summary)

@dash.callback(Output('strategy-chart', 'figure'), Output('strategy-summary', 'children'), Input('strategy-choice', 'value'), Input('strategy-width', 'value'), Input('spot', 'value'), Input('strike', 'value'), Input('volatility', 'value'), Input('rate', 'value'), Input('days', 'value'))
def update_strategy(strategy, width_percent, spot, strike, vol, rate, days):
    width = strike * width_percent / 100
    if strategy == 'spread':
        title = 'Bull call spread'
        legs = [(1, 'Call', strike), (-1, 'Call', strike + width)]
    elif strategy == 'straddle':
        title = 'Long straddle'
        legs = [(1, 'Call', strike), (1, 'Put', strike)]
    else:
        title = 'Long call butterfly'
        legs = [(1, 'Call', strike - width), (-2, 'Call', strike), (1, 'Call', strike + width)]
    strikes = [leg[2] for leg in legs]
    start = max(0, min(spot, min(strikes)) * 0.4)
    end = max(spot, max(strikes)) * 1.6
    expiry_spots = np.unique(np.concatenate([np.linspace(start, end, 350), np.array(strikes)]))
    total_payoff = np.zeros_like(expiry_spots)
    net_premium = 0.0
    descriptions = []
    for quantity, kind, leg_strike in legs:
        call, put = option_prices(spot, leg_strike, vol / 100, rate / 100, days / 365)
        premium = call if kind == 'Call' else put
        net_premium += quantity * premium
        payoff = np.maximum(expiry_spots - leg_strike, 0) if kind == 'Call' else np.maximum(leg_strike - expiry_spots, 0)
        total_payoff += quantity * payoff
        action = 'Buy' if quantity > 0 else 'Sell'
        descriptions.append(f'{action} {abs(quantity)} {kind.lower()} at strike ${leg_strike:.2f}')
    pnl = total_payoff - net_premium
    fig = go.Figure()
    fig.add_scatter(x=expiry_spots.tolist(), y=total_payoff.tolist(), name='Combined payoff before premium', line=dict(color='#a4b4ca', dash='dot', width=2))
    fig.add_scatter(x=expiry_spots.tolist(), y=pnl.tolist(), name='P&L after premium', line=dict(color='#45dfc0', width=3))
    fig.add_hline(y=0, line_color='#a4b4ca', line_dash='dash')
    for leg_strike in sorted(set(strikes)):
        fig.add_vline(x=leg_strike, line_dash='dot', line_color='#50627b')
    fig.update_layout(title=f'{title} — expiry payoff and P&L', template='plotly_dark', paper_bgcolor='#142238', plot_bgcolor='#142238', height=480, xaxis_title='Underlying price at expiry ($)', yaxis_title='$ per share-equivalent strategy unit', hovermode='x unified', legend=dict(orientation='h', y=-0.2), margin=dict(l=65, r=25, t=65, b=100))
    premium_label = 'paid' if net_premium >= 0 else 'received'
    summary = html.Div([html.P(' | '.join(descriptions)), html.P(f'Net model premium {premium_label}: ${abs(net_premium):.2f} per strategy unit', style={'color': '#45dfc0', 'fontWeight': 'bold'})])
    return (fig, summary)

@dash.callback(dash.Output('mc-result', 'children'), dash.Input('mc-run', 'n_clicks'), dash.State('mc-kind', 'value'), dash.State('mc-barrier', 'value'), dash.State('mc-cash', 'value'), dash.State('mc-paths', 'value'), dash.State('spot', 'value'), dash.State('strike', 'value'), dash.State('volatility', 'value'), dash.State('rate', 'value'), dash.State('days', 'value'), prevent_initial_call=True, running=[(dash.Output('mc-run', 'disabled'), True, False)])
def run_exotic_simulation(clicks, kind, barrier, cash, paths, spot, strike, vol, rate, days):
    from monte_carlo import price_exotic
    if kind == 'Down-and-out call':
        if barrier is None or barrier <= 0:
            return 'Enter a positive barrier level.'
        cash = 10
    else:
        if cash is None or cash <= 0:
            return 'Enter a positive cash payout.'
        barrier = 80
    try:
        result = price_exotic(spot=spot, strike=strike, volatility=vol / 100, rate=rate / 100, years=days / 365, kind=kind, barrier=barrier, cash_payout=cash, paths=int(paths))
    except (ValueError, TypeError, OverflowError) as error:
        return f'Cannot calculate: {error}'
    detail = f'Barrier: ${barrier:.2f}' if kind == 'Down-and-out call' else f'Cash payout: ${cash:.2f}'
    return html.Div([html.H4(f'Last run: {kind}'), html.H2(f"Estimated price: ${result['price']:.4f}", style={'color': '#45dfc0'}), html.P(f"Standard error: ${result['standard_error']:.4f}"), html.P(f"Approximate 95% simulation interval: ${result['ci_low']:.4f} to ${result['ci_high']:.4f}"), html.P(f"Spot ${spot:.2f} | Strike ${strike:.2f} | Volatility {vol:.2f}% | Rate {rate:.2f}% | Expiry {days} days | {result['paths']:,} paths"), html.P(detail)])
