from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
import numpy as np

# Sample data
X = np.array([3, 1, 4, 2]).reshape(-1, 1)
y = np.array([9, 1, 16, 4])

# Create the model
degree = 2
alpha = 1.0
model = make_pipeline(PolynomialFeatures(degree=degree), Ridge(alpha=alpha))

# Fit the model
model.fit(X, y)

# New data for prediction
#X_new = np.array([5, 6]).reshape(-1, 1)
X_new = np.array([1, 2, 3, 4, 5, 6]).reshape(-1, 1)

# Predicting new values
predictions = model.predict(X_new)

print("Predicted values:", predictions)