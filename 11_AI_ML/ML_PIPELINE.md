# ML Training & Evaluation Pipeline

## G6-001 V1

The ML layer is a research component. It produces probabilistic predictions for the Decision Engine; it does not create orders and does not bypass Risk.

```text
Historical bars
    ↓
Point-in-time feature snapshots
    ↓
Forward-return labels (future-aware target only)
    ↓
Chronological split + embargo
    ↓
Model training on train only
    ↓
Validation / model selection
    ↓
Locked test evaluation
    ↓
Prediction → Decision Engine → Risk Engine
```

## Leakage controls

1. Features must use only information available at their `event_time`.
2. Label generation is intentionally future-aware, but labels are targets only.
3. The final `horizon_bars` observations cannot receive a label.
4. Dataset splitting never shuffles time-series observations.
5. `embargo_bars` discards boundary observations so overlapping forward labels cannot leak future-period information into the preceding split.
6. Test data must remain untouched until model selection is complete.
7. Model metadata records feature names, training period, dataset hash, version, and optional random seed.

For a forward-return horizon of `H` bars, use an embargo of at least `H` bars when adjacent examples have overlapping outcomes.

## V1 label definition

For observation `t`:

`forward_return = close[t + H] / close[t] - 1`

- `LONG` when return ≥ threshold
- `SHORT` when return ≤ -threshold
- `NEUTRAL` otherwise

Threshold and horizon are explicit configuration, not hidden model behavior.

## Model boundary

`ProbabilisticClassifier` is a provider-neutral interface. The V1 dependency-light `MajorityClassBaseline` establishes a deterministic benchmark. Production model adapters can later target scikit-learn, XGBoost, LightGBM, or PyTorch without changing dataset or decision contracts.

No model is assumed to provide a guaranteed accuracy or trading return. A model must demonstrate out-of-sample robustness before it can influence paper trading.

## Evaluation

V1 records:

- accuracy
- multiclass log loss
- multiclass Brier score
- confusion matrix

Evaluation consumes held-out probabilities and labels only; it does not tune the model.
