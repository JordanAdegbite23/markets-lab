import math
from scipy.stats import norm


def option_price(spot, strike, years, rate, volatility, kind):
    root_time = math.sqrt(years)

    d1 = (
        math.log(spot / strike)
        + (rate + volatility ** 2 / 2) * years
    ) / (volatility * root_time)

    d2 = d1 - volatility * root_time
    discounted_strike = strike * math.exp(-rate * years)

    if kind == "Call":
        price = (
            spot * norm.cdf(d1)
            - discounted_strike * norm.cdf(d2)
        )
    else:
        price = (
            discounted_strike * norm.cdf(-d2)
            - spot * norm.cdf(-d1)
        )

    # Unscaled vega: derivative with respect to decimal volatility.
    vega = spot * norm.pdf(d1) * root_time
    return float(price), float(vega)


def implied_volatility(
    market_price, spot, strike, years, rate, kind="Call"
):
    inputs = [market_price, spot, strike, years, rate]

    if not all(math.isfinite(value) for value in inputs):
        raise ValueError("All inputs must be finite numbers.")

    if spot <= 0 or strike <= 0 or years <= 0:
        raise ValueError("Spot, strike and time must be positive.")

    if kind not in ("Call", "Put"):
        raise ValueError("Choose Call or Put.")

    discounted_strike = strike * math.exp(-rate * years)

    if kind == "Call":
        lower = max(0.0, spot - discounted_strike)
        upper = spot
    else:
        lower = max(0.0, discounted_strike - spot)
        upper = discounted_strike

    if not lower < market_price < upper:
        raise ValueError(
            f"For a positive, finite implied volatility, the price "
            f"must be strictly between ${lower:.6f} and ${upper:.6f}."
        )

    low_vol = 0.0
    high_vol = 1.0

    # Find an upper volatility that brackets the market price.
    while True:
        high_price, _ = option_price(
            spot, strike, years, rate, high_vol, kind
        )
        if high_price >= market_price:
            break

        high_vol *= 2
        if high_vol > 128:
            raise ValueError("Could not bracket implied volatility.")

    volatility = min(0.20, high_vol / 2)
    tolerance = 1e-8 * max(1.0, market_price)

    for iteration in range(1, 101):
        price, vega = option_price(
            spot, strike, years, rate, volatility, kind
        )
        error = price - market_price

        if abs(error) < tolerance:
            return volatility, iteration

        if error > 0:
            high_vol = volatility
        else:
            low_vol = volatility

        # Newton's method, with bisection as a safeguard.
        candidate = (
            volatility - error / vega
            if vega > 1e-12 else float("nan")
        )

        if not low_vol < candidate < high_vol:
            candidate = (low_vol + high_vol) / 2

        volatility = candidate

    raise ValueError("Solver did not converge. Check the inputs.")


if __name__ == "__main__":
    volatility, iterations = implied_volatility(
        market_price=10.45,
        spot=100,
        strike=100,
        years=1,
        rate=0.05,
        kind="Call",
    )

    print(f"Implied volatility: {volatility:.2%}")
    print(f"Solver iterations: {iterations}")
