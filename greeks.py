import math
from scipy.stats import norm


def calculate_greeks(spot, strike, volatility, rate, years):
    root_time = math.sqrt(years)

    d1 = (
        math.log(spot / strike)
        + (rate + 0.5 * volatility ** 2) * years
    ) / (volatility * root_time)

    d2 = d1 - volatility * root_time

    density = norm.pdf(d1)
    discount = math.exp(-rate * years)

    gamma = density / (spot * volatility * root_time)

    # Vega per one percentage-point increase in volatility.
    vega = spot * density * root_time / 100

    common_theta = -spot * density * volatility / (2 * root_time)

    # Theta per calendar day.
    call_theta = (
        common_theta
        - rate * strike * discount * norm.cdf(d2)
    ) / 365

    put_theta = (
        common_theta
        + rate * strike * discount * norm.cdf(-d2)
    ) / 365

    # Rho per one percentage-point increase in interest rate.
    call_rho = strike * years * discount * norm.cdf(d2) / 100
    put_rho = -strike * years * discount * norm.cdf(-d2) / 100

    return {
        "Call": {
            "Delta": norm.cdf(d1),
            "Gamma": gamma,
            "Vega": vega,
            "Theta": call_theta,
            "Rho": call_rho,
        },
        "Put": {
            "Delta": norm.cdf(d1) - 1,
            "Gamma": gamma,
            "Vega": vega,
            "Theta": put_theta,
            "Rho": put_rho,
        },
    }


if __name__ == "__main__":
    result = calculate_greeks(
        spot=100,
        strike=100,
        volatility=0.20,
        rate=0.05,
        years=1,
    )

    for option_type, values in result.items():
        print(f"\n{option_type} Greeks")
        for name, value in values.items():
            print(f"{name}: {value:.4f}")
