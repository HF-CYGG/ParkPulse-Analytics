from __future__ import annotations

from analytics.services.metrics import mean_absolute_error, mean_squared_error, r2_score

from .base import OptionalDependencyUnavailable
from .linear_regression import LinearRegressionModel


class LSTMForecastModel:
    name = "lstm"

    def __init__(self, epochs: int = 80, lookback: int = 7):
        try:
            import torch
            from torch import nn
        except Exception as exc:  # pragma: no cover - depends on optional packages.
            raise OptionalDependencyUnavailable("torch is not installed") from exc
        self.torch = torch
        self.nn = nn
        self.epochs = epochs
        self.lookback = lookback
        self.visit_model = None
        self.queue_model = None
        self.visit_scale = 1.0
        self.queue_scale = 1.0
        self.visits: list[float] = []
        self.queues: list[float] = []
        self._fallback = LinearRegressionModel(window=21)

    def fit(self, visits: list[float], queues: list[float]) -> None:
        self.visits = [float(value) for value in visits]
        self.queues = [float(value) for value in queues]
        self._fallback.fit(self.visits, self.queues)
        if len(self.visits) <= self.lookback + 2:
            return
        self.visit_scale = max(max(self.visits), 1.0)
        self.queue_scale = max(max(self.queues), 1.0)
        self.visit_model = self._train_single([value / self.visit_scale for value in self.visits])
        self.queue_model = self._train_single([value / self.queue_scale for value in self.queues])

    def predict(self, horizon: int) -> list[tuple[float, float]]:
        if self.visit_model is None or self.queue_model is None:
            return self._fallback.predict(horizon)
        visit_pred = self._predict_single(self.visit_model, [value / self.visit_scale for value in self.visits], horizon)
        queue_pred = self._predict_single(self.queue_model, [value / self.queue_scale for value in self.queues], horizon)
        return [
            (max(0.0, visit_pred[idx] * self.visit_scale), max(0.0, queue_pred[idx] * self.queue_scale))
            for idx in range(horizon)
        ]

    def parameters(self) -> dict:
        return {"epochs": self.epochs, "lookback": self.lookback, "hidden_size": 16}

    def evaluate(self, actual: list[float], predicted: list[float]) -> dict:
        return {
            "mae": mean_absolute_error(actual, predicted),
            "mse": mean_squared_error(actual, predicted),
            "r2": r2_score(actual, predicted),
        }

    def _train_single(self, values: list[float]):
        torch = self.torch
        model = _TinyLSTM(self.nn)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.03)
        loss_fn = self.nn.MSELoss()
        xs, ys = self._windows(values)
        if not xs:
            return None
        x_tensor = torch.tensor(xs, dtype=torch.float32).unsqueeze(-1)
        y_tensor = torch.tensor(ys, dtype=torch.float32).unsqueeze(-1)
        model.train()
        for _ in range(self.epochs):
            optimizer.zero_grad()
            output = model(x_tensor)
            loss = loss_fn(output, y_tensor)
            loss.backward()
            optimizer.step()
        model.eval()
        return model

    def _predict_single(self, model, values: list[float], horizon: int) -> list[float]:
        torch = self.torch
        history = values[:]
        predictions = []
        for _ in range(horizon):
            window = history[-self.lookback :]
            if len(window) < self.lookback:
                window = [0.0] * (self.lookback - len(window)) + window
            x_tensor = torch.tensor([window], dtype=torch.float32).unsqueeze(-1)
            with torch.no_grad():
                value = float(model(x_tensor).squeeze().item())
            value = max(0.0, value)
            predictions.append(value)
            history.append(value)
        return predictions

    def _windows(self, values: list[float]) -> tuple[list[list[float]], list[float]]:
        xs = []
        ys = []
        for idx in range(self.lookback, len(values)):
            xs.append(values[idx - self.lookback : idx])
            ys.append(values[idx])
        return xs, ys


class _TinyLSTM:
    def __init__(self, nn):
        self.nn = nn
        self.module = nn.Module()
        self.lstm = nn.LSTM(input_size=1, hidden_size=16, batch_first=True)
        self.linear = nn.Linear(16, 1)

    def parameters(self):
        return list(self.lstm.parameters()) + list(self.linear.parameters())

    def train(self):
        self.lstm.train()
        self.linear.train()

    def eval(self):
        self.lstm.eval()
        self.linear.eval()

    def __call__(self, x_tensor):
        output, _ = self.lstm(x_tensor)
        return self.linear(output[:, -1, :])
