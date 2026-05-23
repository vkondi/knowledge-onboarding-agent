# Introduction to Machine Learning

Machine learning (ML) is a branch of artificial intelligence that allows systems to learn patterns from data without being explicitly programmed for each task.

## Core Concepts

### Supervised Learning

The model learns from labelled training data - each input has a corresponding correct output.

- **Classification**: Predict a category (e.g., spam vs. not spam, image recognition)
- **Regression**: Predict a continuous value (e.g., house prices, stock forecasts)

Common algorithms: Linear Regression, Logistic Regression, Decision Trees, Random Forests, Support Vector Machines (SVM), Neural Networks.

### Unsupervised Learning

No labels are provided. The model discovers patterns, clusters, or structure in the data.

- **Clustering**: Group similar data points (e.g., K-Means, DBSCAN)
- **Dimensionality Reduction**: Compress features while preserving information (e.g., PCA, t-SNE)

### Reinforcement Learning

An agent learns by interacting with an environment and receiving rewards or penalties for actions. Used in robotics, game playing (AlphaGo), and autonomous systems.

## The ML Workflow

1. **Define the problem** - what are you predicting? What counts as success?
2. **Collect and clean data** - quality data is more important than algorithm choice.
3. **Exploratory Data Analysis (EDA)** - understand distributions, correlations, and outliers.
4. **Feature engineering** - transform raw data into informative input features.
5. **Choose a model** - start simple (linear models), then increase complexity if needed.
6. **Train the model** - fit the model on training data.
7. **Evaluate** - measure performance on a held-out test set.
8. **Tune hyperparameters** - adjust settings to improve generalisation.
9. **Deploy and monitor** - watch for data drift and model degradation over time.

## Key Metrics

| Task | Metric |
|---|---|
| Binary classification | Accuracy, Precision, Recall, F1, AUC-ROC |
| Multi-class classification | Macro/Micro F1, Confusion Matrix |
| Regression | MAE, RMSE, R² |
| Ranking / retrieval | NDCG, MRR, Precision@K |

## Overfitting vs Underfitting

- **Overfitting**: Model memorises training data but performs poorly on new data. Fix with more data, regularisation (L1/L2), dropout, or simpler models.
- **Underfitting**: Model is too simple to capture the patterns. Fix with more features, a more complex model, or better feature engineering.

## Popular Libraries

| Library | Purpose |
|---|---|
| scikit-learn | Classical ML algorithms, preprocessing, model selection |
| pandas | Data manipulation and analysis |
| NumPy | Numerical computation |
| Matplotlib / Seaborn | Data visualisation |
| TensorFlow / PyTorch | Deep learning |
| XGBoost / LightGBM | Gradient boosting (often top performers on tabular data) |
