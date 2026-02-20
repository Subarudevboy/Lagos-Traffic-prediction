from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "lag_1",
    "lag_3",
    "lag_6",
    "rolling_mean_15",
    "rolling_mean_60",
    "rolling_std_15",
    "capacity_ratio",
    "incident_flag",
    "rush_hour",
]


class PredictionEngine:
    def __init__(self) -> None:
        self.max_rows = 20000
        self.max_segment_history = 720
        self.rows = deque(maxlen=self.max_rows)
        self.model = None
        self.model_name = "untrained"
        self.metrics: dict[str, float] = {}
        self.residual_std = 0.07
        self.last_retrained_at: datetime | None = None
        self.retrain_interval_ticks = 900
        self.segment_series = defaultdict(lambda: deque(maxlen=self.max_segment_history))

    def add_observation(self, features: dict[str, Any], target: float, tick: int) -> None:
        row = {k: features[k] for k in FEATURE_COLUMNS if k in features}
        row["target"] = float(target)
        row["tick"] = int(tick)
        row["segment_id"] = int(features["segment_id"])
        self.rows.append(row)
        self.segment_series[row["segment_id"]].append(float(target))

    def _build_dataset(self) -> pd.DataFrame:
        if not self.rows:
            return pd.DataFrame(columns=[*FEATURE_COLUMNS, "target", "tick", "segment_id"])
        return pd.DataFrame(list(self.rows))

    def maybe_retrain(self, tick: int) -> None:
        if len(self.rows) < 500:
            return
        if self.last_retrained_at and tick % self.retrain_interval_ticks != 0:
            return
        self.train()

    def train(self) -> None:
        data = self._build_dataset().sort_values("tick")
        if len(data) < 500:
            return

        split_index = int(len(data) * 0.8)
        train = data.iloc[:split_index]
        test = data.iloc[split_index:]
        if test.empty:
            return

        x_train = train[FEATURE_COLUMNS]
        y_train = train["target"]
        x_test = test[FEATURE_COLUMNS]
        y_test = test["target"]

        candidates = {
            "linear_regression": LinearRegression(),
            "random_forest": RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=1),
            "gradient_boosting": GradientBoostingRegressor(random_state=42),
        }

        best_name = "baseline_last"
        best_rmse = float("inf")
        best_model = None

        for name, model in candidates.items():
            model.fit(x_train, y_train)
            pred = model.predict(x_test)
            rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_name = name
                best_model = model

        baseline_last = float(np.sqrt(mean_squared_error(y_test, x_test["lag_1"])))
        baseline_roll = float(np.sqrt(mean_squared_error(y_test, x_test["rolling_mean_15"])))

        if baseline_last <= best_rmse:
            self.model = None
            self.model_name = "baseline_last"
            predictions = x_test["lag_1"].to_numpy()
        elif baseline_roll <= best_rmse:
            self.model = None
            self.model_name = "baseline_rolling_mean_15"
            predictions = x_test["rolling_mean_15"].to_numpy()
        else:
            if best_model is None:
                return
            self.model = best_model
            self.model_name = best_name
            predictions = best_model.predict(x_test)

        self.metrics = {
            "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
            "mae": float(mean_absolute_error(y_test, predictions)),
            "r2": float(r2_score(y_test, predictions)),
            "baseline_last_rmse": baseline_last,
            "baseline_rolling_rmse": baseline_roll,
            "rows": int(len(data)),
        }
        residuals = y_test.to_numpy() - np.array(predictions)
        self.residual_std = float(np.std(residuals)) if len(residuals) > 1 else 0.07
        self.last_retrained_at = datetime.now(UTC)

    def predict(self, features: dict[str, Any]) -> tuple[float, float, float]:
        x = pd.DataFrame([{k: features.get(k, 0.0) for k in FEATURE_COLUMNS}])

        if self.model_name == "baseline_last":
            pred = float(x.iloc[0]["lag_1"])
        elif self.model_name == "baseline_rolling_mean_15":
            pred = float(x.iloc[0]["rolling_mean_15"])
        elif self.model is not None:
            pred = float(self.model.predict(x)[0])
        else:
            pred = float(x.iloc[0]["rolling_mean_15"])

        pred = min(max(pred, 0.0), 1.0)
        ci = 1.96 * max(self.residual_std, 0.03)
        lower = min(max(pred - ci, 0.0), 1.0)
        upper = min(max(pred + ci, 0.0), 1.0)
        return pred, lower, upper

    def get_segment_history(self, segment_id: int, limit: int = 120) -> list[float]:
        history = self.segment_series.get(segment_id)
        if history is None:
            return []
        return list(history)[-limit:]
