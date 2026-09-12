# Walk-Forward Validation

## Purpose

Walk-forward validation evaluates a strategy on future out-of-sample data after a preceding training/optimization interval. It is designed to expose parameter overfitting and regime-specific research artifacts.

## Window contract

For each window:

```text
TRAIN [start ........ train_end)
                         TEST [train_end .... test_end)
```

The test interval begins exactly where training ends. A configurable `step_size` controls the rolling advance.

## No-leakage rules

1. Strategy construction receives only the training slice.
2. Test bars are not available to the strategy factory.
3. The backtest engine itself exposes only the chronological prefix of the test interval at each decision point.
4. Test results are not used to construct a later strategy within the same window.
5. Empty/incomplete windows are omitted rather than padded with synthetic data.

## V1 scope

The validator supplies the rolling data partition and executes the resulting strategy. It does **not** perform parameter optimization, feature selection, model training, or statistical significance testing. Those responsibilities belong to later research layers.

## Acceptance criteria

- deterministic window generation
- chronological train/test separation
- configurable rolling step
- no train/test overlap within a window
- strategy factory cannot receive future test data through the validator contract
- out-of-sample results are retained per window

## Production research boundary

Walk-forward results must be evaluated with realistic execution costs, multiple market regimes, stability metrics and statistical robustness. A positive aggregate return alone is insufficient evidence for live deployment.
