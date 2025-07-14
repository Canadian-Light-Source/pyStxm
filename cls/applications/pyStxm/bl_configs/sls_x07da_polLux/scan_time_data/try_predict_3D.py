from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
import numpy as np

# Sample data with 3 features
# X = np.array([
#     [3, 1, 2],
#     [1, 2, 1],
#     [4, 3, 3],
#     [2, 1, 2]
# ])
# y = np.array([9, 1, 16, 4])


detector_scan_data = [
        (5, 5, 5, 1),  # (actual_time_sec, num_points_x, num_points_y, dwell_time_per_point_ms)
        (5, 5, 5, 10),
        (8, 5, 5, 100),
        (36, 15, 15, 1),
        (37, 15, 15, 10),
        (59, 15, 15, 100),
        (60, 30, 30, 1),
        (71, 30, 30, 10),
        (154, 30, 30, 100),
        (124, 40, 40, 10),
        (201, 50, 50, 10),
        (300, 50, 50, 50),
        (420, 50, 50, 100),
    ]

X = np.array([[points_x, points_y, dwell_time] for _, points_x, points_y, dwell_time in detector_scan_data])
y = np.array([actual_time for actual_time, _, _, _ in detector_scan_data])

degree = 2
alpha = 0.1
model = make_pipeline(PolynomialFeatures(degree=degree), Ridge(alpha=alpha))

# Fit the model
model.fit(X, y)

# New data for prediction with 3 features
X_new = np.array([
    [20, 20, 10],
    [30, 30, 10]
])

# Predicting new values
predictions = model.predict(X_new)

print("Predicted values:", predictions)