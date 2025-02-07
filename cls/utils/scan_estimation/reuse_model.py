import joblib
import numpy as np

from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import numpy as np
import joblib

# # Example data (list of tuples)
# data = [
#     (210, 100, 50, 20),
#     (330, 150, 70, 30),
#     (150, 80, 40, 10),
#     (410, 200, 100, 40),
#     (270, 120, 60, 25)
# ]
#
# # Separate the data into features (X) and targets (y)
# X = np.array([[points_x, points_y, dwell_time] for _, points_x, points_y, dwell_time in data])
# y = np.array([actual_time for actual_time, _, _, _ in data])
#
# # Initialize the Ridge regression model with polynomial features
# model = make_pipeline(PolynomialFeatures(degree=2), Ridge(alpha=0.1))
#
# # Fit the model using the training data
# model.fit(X, y)
#
# # Save the trained model to a file
# joblib.dump(model, 'trained_model.pkl')


##############################################################################
# now reload it


# Load the trained model from file
model = joblib.load('trained_model.pkl')


# Function to predict time based on points X, points Y, and dwell time
def predict_time(points_x, points_y, dwell_time):
    prediction = model.predict([[points_x, points_y, dwell_time]])
    return prediction[0]


# Example usage
test_points_x = 100
test_points_y = 100
test_dwell_time = 40

estimated_time = predict_time(test_points_x, test_points_y, test_dwell_time)
print(
    f"Estimated time for points_x={test_points_x}, points_y={test_points_y}, dwell_time={test_dwell_time}: {estimated_time:.2f} seconds")
