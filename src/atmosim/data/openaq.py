"""OpenAQ & Ground-Truth Air Quality Ingestion Module for AtmosSim.

Connects to OpenAQ / Open-Meteo Air Quality Historical APIs, normalizes ambient
air quality pollutant observations (PM2.5, PM10, NO2, SO2, CO, O3), manages caching,
and provides ground-truth observation benchmarks for physical dispersion validation.

References
----------
1. OpenAQ Platform API v3 (https://api.openaq.org)
2. Open-Meteo Air Quality API (https://air-quality-api.open-meteo.com)
3. CPCB National Ambient Air Quality Standards (NAAQS), India.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd
import requests

from atmosim.data.cache import DataCache


@dataclass
class AirQualityRecord:
    """Single normalized air quality observation."""
    timestamp: datetime  # UTC
    pm25_ug_m3: float
    pm10_ug_m3: Optional[float] = None
    no2_ug_m3: Optional[float] = None
    so2_ug_m3: Optional[float] = None
    co_mg_m3: Optional[float] = None
    o3_ug_m3: Optional[float] = None


class OpenAQConnector:
    """Connector for ground-station air quality observations."""

    def __init__(
        self,
        cache: Optional[DataCache] = None,
        cache_dir: Union[str, Path] = "cache/openaq",
        api_key: Optional[str] = None,
    ) -> None:
        self.cache = cache or DataCache(cache_dir=cache_dir)
        self.api_key = api_key

    def fetch_delhi_historical(
        self,
        start_date: str = "2022-01-01",
        end_date: str = "2024-12-31",
        latitude: float = 28.6139,
        longitude: float = 77.2090,
    ) -> pd.DataFrame:
        """Fetch daily air quality observations for Delhi NCR.

        Checks local AtmosIQ dataset cache first if available, otherwise queries
        the historical air quality endpoint.
        """
        cache_key = f"openaq_delhi_{start_date}_{end_date}_{latitude}_{longitude}"
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            return pd.DataFrame(cached_data)

        # Check pre-existing AtmosIQ raw ground truth file if on disk
        local_raw = Path("/home/suraj/atmosIQ/ml/data/raw/openaq_delhi_raw.csv")
        if local_raw.is_file():
            df_local = pd.read_csv(local_raw)
            # Filter date range
            mask = (df_local["date"] >= start_date) & (df_local["date"] <= end_date)
            sub_df = df_local[mask].copy().reset_index(drop=True)
            self.cache.set(cache_key, sub_df.to_dict(orient="records"))
            return sub_df

        # Live query
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone",
            "timezone": "UTC",
        }
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Air Quality API request failed: HTTP {resp.status_code} - {resp.text}")

        data = resp.json().get("hourly", {})
        df_hourly = pd.DataFrame(data)
        df_hourly["date"] = pd.to_datetime(df_hourly["time"]).dt.strftime("%Y-%m-%d")
        df_daily = df_hourly.groupby("date").agg({
            "pm2_5": "mean",
            "pm10": "mean",
            "nitrogen_dioxide": "mean",
            "sulphur_dioxide": "mean",
            "carbon_monoxide": "mean",
            "ozone": "mean",
        }).reset_index().rename(columns={
            "pm2_5": "pm25",
            "nitrogen_dioxide": "no2",
            "sulphur_dioxide": "so2",
            "carbon_monoxide": "co",
            "ozone": "o3",
        }).round(2)

        self.cache.set(cache_key, df_daily.to_dict(orient="records"))
        return df_daily

    def get_spot_check_ground_truth(self) -> Dict[str, float]:
        """Returns observed daily mean PM2.5 (ug/m3) for the 5 verified historical spot-check days."""
        df = self.fetch_delhi_historical(start_date="2022-01-01", end_date="2024-12-31")
        spot_dates = ["2022-11-04", "2023-11-03", "2023-11-13", "2024-01-14", "2024-11-18"]
        sub = df[df["date"].isin(spot_dates)]
        return dict(zip(sub["date"], sub["pm25"]))


__all__ = [
    "AirQualityRecord",
    "OpenAQConnector",
]
