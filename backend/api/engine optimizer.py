import numpy as np

def optimize_portfolio(returns, cov_matrix, risk_level):

    if risk_level == "Low":
        weights = np.array([0.4, 0.3, 0.15, 0.1, 0.05])
    elif risk_level == "Medium":
        weights = np.array([0.2, 0.25, 0.2, 0.2, 0.15])
    else:
        weights = np.array([0.1, 0.2, 0.25, 0.3, 0.15])

    weights = weights / np.sum(weights)

    expected_return = np.dot(weights, returns)
    risk = np.dot(weights.T, np.dot(cov_matrix, weights))

    return weights, expected_return, risk