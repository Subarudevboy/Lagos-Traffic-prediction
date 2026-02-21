from __future__ import annotations

import asyncio

from app.core.feature_engineering import build_feature_row


class SimulationScheduler:
    def __init__(self, simulation_engine, prediction_engine, state_cache) -> None:
        self.simulation_engine = simulation_engine
        self.prediction_engine = prediction_engine
        self.state_cache = state_cache
        self._task = None
        self._retrain_task = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._retrain_task and not self._retrain_task.done():
            self._retrain_task.cancel()
            try:
                await self._retrain_task
            except asyncio.CancelledError:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while self._running:
            await asyncio.sleep(0)
            self.simulation_engine.tick()
            live_segments = self.simulation_engine.get_live_segments()

            feature_rows = []
            for idx, row in enumerate(live_segments, start=1):
                history = list(self.simulation_engine.congestion_history[row["segment_id"]])
                features = build_feature_row(
                    segment_id=row["segment_id"],
                    timestamp=self.simulation_engine.current_time,
                    congestion_history=history,
                    capacity=row["capacity"],
                    vehicle_count=row["vehicle_count"],
                    incident_flag=row["incident_flag"],
                )
                feature_rows.append(features)
                self.prediction_engine.add_observation(
                    features=features,
                    target=row["congestion_index"],
                    tick=self.simulation_engine.tick_count,
                )
                if idx % 200 == 0:
                    await asyncio.sleep(0)

            if (
                len(self.prediction_engine.rows) >= 500
                and self.simulation_engine.tick_count % self.prediction_engine.retrain_interval_ticks == 0
                and (self._retrain_task is None or self._retrain_task.done())
            ):
                self._retrain_task = asyncio.create_task(asyncio.to_thread(self.prediction_engine.train))

            heatmap_rows = []
            for idx, (row, features) in enumerate(zip(live_segments, feature_rows), start=1):
                predicted, lower, upper = self.prediction_engine.predict(features)
                predicted_speed = max(float(row["free_flow_speed"]) * (1 - predicted), 5.0)
                estimated_travel_time_min = (float(row["length"]) / max(float(row["avg_speed"]), 5.0)) * 60.0
                predicted_travel_time_min = (float(row["length"]) / predicted_speed) * 60.0
                heatmap_rows.append(
                    {
                        **row,
                        "predicted_congestion": round(predicted, 4),
                        "confidence_lower": round(lower, 4),
                        "confidence_upper": round(upper, 4),
                        "estimated_segment_travel_time_min": round(estimated_travel_time_min, 3),
                        "predicted_segment_travel_time_min": round(predicted_travel_time_min, 3),
                    }
                )
                if idx % 200 == 0:
                    await asyncio.sleep(0)

            self.state_cache.set_json("live_segments", heatmap_rows)
            self.state_cache.set_json("live_heatmap", heatmap_rows)
            self.state_cache.set_json("model_metrics", self.prediction_engine.metrics)
            self.state_cache.set_json(
                "sim_status",
                {
                    **self.simulation_engine.get_status(),
                    "model": self.prediction_engine.model_name,
                },
            )

            await asyncio.sleep(self.simulation_engine.tick_interval_seconds)
