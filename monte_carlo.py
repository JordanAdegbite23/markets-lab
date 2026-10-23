import math
import numpy as np


def price_exotic(
    spot,
    strike,
    volatility,
    rate,
    years,
    kind="Digital call",
    barrier=80,
    cash_payout=10,
    paths=20000,
    seed=42,
):
    numbers = [
        spot, strike, volatility, rate, years, barrier, cash_payout
    ]

    if not all(math.isfinite(value) for value in numbers):
        raise ValueError("Inputs must be finite numbers.")

    if spot <= 0 or strike <= 0 or years <= 0:
        raise ValueError("Spot, strike and time must be positive.")

    if volatility <= 0 or barrier <= 0 or cash_payout <= 0:
        raise ValueError(
            "Volatility, barrier and cash payout must be positive."
        )

    if not isinstance(paths, int) or not 1000 <= paths <= 100000:
        raise ValueError("Choose between 1,000 and 100,000 paths.")

    if kind not in ("Digital call", "Down-and-out call"):
        raise ValueError("Choose a supported option type.")

    rng = np.random.default_rng(seed)

    if kind == "Digital call":
        # Exact terminal simulation under geometric Brownian motion.
        shocks = rng.standard_normal(paths)
        terminal = spot * np.exp(
            (rate - 0.5 * volatility ** 2) * years
            + volatility * math.sqrt(years) * shocks
        )
        payoff = cash_payout * (terminal > strike)

    else:
        # Discrete monitoring: initial observation, then roughly daily.
        steps = max(1, math.ceil(365 * years))
        dt = years / steps

        current = np.full(paths, float(spot))
        knocked_out = np.full(paths, spot <= barrier, dtype=bool)

        drift = (rate - 0.5 * volatility ** 2) * dt
        diffusion = volatility * math.sqrt(dt)

        for _ in range(steps):
            current *= np.exp(
                drift + diffusion * rng.standard_normal(paths)
            )
            knocked_out |= current <= barrier

        payoff = np.where(
            knocked_out,
            0.0,
            np.maximum(current - strike, 0.0),
        )

    discounted = math.exp(-rate * years) * payoff

    estimate = float(discounted.mean())
    standard_error = float(discounted.std(ddof=1) / math.sqrt(paths))

    return {
        "price": estimate,
        "standard_error": standard_error,
        "ci_low": estimate - 1.96 * standard_error,
        "ci_high": estimate + 1.96 * standard_error,
        "paths": paths,
    }


if __name__ == "__main__":
    for kind in ("Digital call", "Down-and-out call"):
        result = price_exotic(
            spot=100,
            strike=100,
            volatility=0.20,
            rate=0.05,
            years=1,
            kind=kind,
            barrier=80,
            cash_payout=10,
        )

        print(f"\n{kind}")
        print(f"Estimated price: ${result['price']:.4f}")
        print(f"Standard error: ${result['standard_error']:.4f}")
        print(
            "Approximate 95% simulation interval: "
            f"${result['ci_low']:.4f} to ${result['ci_high']:.4f}"
        )
