import numpy as np
from sklearn.linear_model import LinearRegression

def predict_price_trend(price_history):
    
    # Need at least 3 data points to make a prediction
    if len(price_history) < 3:
        return {
            "trend": "insufficient_data",
            "message": "Not enough data yet",
            "icon": "➡️",
            "color": "#a0aec0"
        }

    X = np.array(range(len(price_history))).reshape(-1, 1)
    y = np.array(price_history)

    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0]

    next_day = np.array([[len(price_history)]])
    predicted_price = model.predict(next_day)[0]

    threshold = 10

    if slope < -threshold:
        return {
            "trend": "dropping",
            "message": "Price trending down — good time to wait",
            "predicted_price": round(predicted_price, 2),
            "icon": "📉",
            "color": "#48bb78"  # green — good news for buyer
        }
    elif slope > threshold:
        return {
            "trend": "rising",
            "message": "Price trending up — consider buying soon",
            "predicted_price": round(predicted_price, 2),
            "icon": "📈",
            "color": "#fc8181"  # red — act fast
        }
    else:
        return {
            "trend": "stable",
            "message": "Price is stable",
            "predicted_price": round(predicted_price, 2),
            "icon": "➡️",
            "color": "#a0aec0"  # grey — neutral
        }