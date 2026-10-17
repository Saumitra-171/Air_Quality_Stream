"""Stand-out feature #1: short-term PM2.5 forecast with ARIMA (statsmodels)."""
import warnings
import numpy as np
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")   # ARIMA convergence chatter would flood the processor log


def forecast(values, steps=7, order=(2, 1, 1), alpha=0.2):
    """Fit ARIMA on recent values; return (yhat, lower, upper) arrays for the next `steps` points.
    alpha=0.2 gives an 80% prediction interval. Returns None if there is too little data or the fit fails."""
    y = np.asarray(values, dtype=float)
    if len(y) < 20:
        return None
    try:
        res = ARIMA(y, order=order).fit()
        fc = res.get_forecast(steps)
        ci = np.asarray(fc.conf_int(alpha=alpha))
        yhat = np.clip(np.asarray(fc.predicted_mean), 0, None)
        return yhat, np.clip(ci[:, 0], 0, None), np.clip(ci[:, 1], 0, None)
    except Exception:
        return None
