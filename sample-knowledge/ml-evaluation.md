# ML Model Evaluation and Validation

Going beyond basic accuracy metrics — this guide covers evaluation strategies, validation techniques, and common pitfalls when assessing model performance.

## Why Accuracy Alone is Misleading

On a dataset where 95% of samples are class A and 5% are class B, a model that always predicts class A achieves 95% accuracy — but is completely useless.

Always look at your class distribution before choosing a metric.

## Classification Metrics

### Confusion Matrix

|  | Predicted Positive | Predicted Negative |
|---|---|---|
| **Actual Positive** | True Positive (TP) | False Negative (FN) |
| **Actual Negative** | False Positive (FP) | True Negative (TN) |

### Derived Metrics

```
Precision  = TP / (TP + FP)    — of all positive predictions, how many were correct?
Recall     = TP / (TP + FN)    — of all actual positives, how many did we catch?
F1         = 2 × (P × R) / (P + R)   — harmonic mean of precision and recall
Accuracy   = (TP + TN) / total
```

- High **precision** matters when false positives are costly (e.g., spam filter — don't block good emails).
- High **recall** matters when false negatives are costly (e.g., cancer screening — don't miss cases).

### AUC-ROC

The Receiver Operating Characteristic curve plots true positive rate vs false positive rate at every classification threshold.

- **AUC = 1.0**: perfect classifier.
- **AUC = 0.5**: random guessing.
- **AUC < 0.5**: worse than random (check for label leakage).

Use AUC-ROC for imbalanced datasets where the positive class is rare.

## Regression Metrics

```
MAE  = mean(|y_true - y_pred|)                — interpretable; same units as target
RMSE = sqrt(mean((y_true - y_pred)²))         — penalises large errors more
R²   = 1 - SS_res / SS_tot                   — proportion of variance explained (1.0 = perfect)
```

## Validation Strategies

### Train/Validation/Test Split

Split data into three sets:
- **Training set** (60–70%): fit the model.
- **Validation set** (15–20%): tune hyperparameters and select models.
- **Test set** (15–20%): evaluate the final model once — never use it to make decisions.

**Critical**: the test set must not influence any modelling decision. Looking at test performance during development causes data leakage.

### k-Fold Cross-Validation

Split data into k equally-sized folds. Train on k−1 folds, evaluate on the held-out fold. Repeat k times and average the scores.

```python
from sklearn.model_selection import cross_val_score
scores = cross_val_score(model, X, y, cv=5, scoring="f1")
print(f"Mean F1: {scores.mean():.3f} ± {scores.std():.3f}")
```

Use CV when data is scarce. Standard k=5 or k=10.

### Stratified Cross-Validation

Ensures each fold has the same class proportion as the full dataset — essential for imbalanced classification.

```python
from sklearn.model_selection import StratifiedKFold
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
```

### Time-Series Cross-Validation

Never shuffle time-series data. Use forward-chaining (expanding window) splits:

```
Fold 1: train=[1..100],  val=[101..120]
Fold 2: train=[1..120],  val=[121..140]
Fold 3: train=[1..140],  val=[141..160]
```

## Overfitting and Underfitting

| Symptom | Likely cause | Fix |
|---|---|---|
| High train score, low val score | Overfitting | More data, regularisation, simpler model, dropout |
| Low train score, low val score | Underfitting | More features, complex model, longer training |
| Train ≈ val, both low | High bias | Better features, larger model |
| Train >> val | High variance | Regularisation, ensemble, more data |

## Learning Curves

Plot training and validation scores as a function of training set size. Diagnose bias vs variance at a glance:

- If both curves plateau low → high bias → need a better model.
- If training score is high but validation score is much lower → high variance → need more data or regularisation.

## Data Leakage

Data leakage occurs when information from outside the training set is used to build the model, leading to over-optimistic evaluation.

**Common leakage sources:**
- Scaling/normalising before splitting (compute stats on train only, then apply to val/test).
- Target encoding using the full dataset.
- Features derived from the target variable.
- Test set contamination during feature selection.

Always fit preprocessors (scalers, encoders) on training data only, then transform validation/test data with the fitted parameters.

## Calibration

A well-calibrated model produces probabilities that match real-world frequencies: a prediction of 0.7 should be correct 70% of the time.

Check calibration with a calibration curve. Calibrate using `CalibratedClassifierCV` (sklearn) with Platt scaling or isotonic regression.
