from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
import numpy as np
import matplotlib.pyplot as plt


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
actual = y = np.array([actual_time for actual_time, _, _, _ in detector_scan_data])

degree = 3
alpha = 0.1
model = make_pipeline(PolynomialFeatures(degree=degree), Ridge(alpha=alpha))

# Fit the model
model.fit(X, y)

# New data for prediction with 3 features
X_new = np.array([
    [5, 5, 1],  # (actual_time_sec, num_points_x, num_points_y, dwell_time_per_point_ms)
    [5, 5, 10],
    [5, 5, 100],
    [15, 15, 1],
    [15, 15, 10],
    [15, 15, 100],
    [30, 30, 1],
    [30, 30, 10],
    [30, 30, 100],
    [40, 40, 10],
    [50, 50, 10],
    [50, 50, 50],
    [50, 50, 100],
    [45, 45, 100],
])

# Predicting new values
predictions = model.predict(X_new)

print("Predicted values:", predictions)

plt.style.use('_mpl-gallery')
act_arr = np.array(actual)
est_arr = np.array(predictions)
x = np.linspace(0, 10, len(actual))
x2 = np.linspace(0, 10, len(est_arr))

# plot
fig, ax = plt.subplots()

ax.plot(x, act_arr, 'x', markeredgewidth=2)
ax.plot(x2, est_arr, linewidth=2.0)
#ax.plot(x2, y2 - 2.5, 'o-', linewidth=2)

# ax.set(xlim=(0, 8), xticks=np.arange(1, 8),
#        ylim=(0, 8), yticks=np.arange(1, 8))
#
plt.show()
