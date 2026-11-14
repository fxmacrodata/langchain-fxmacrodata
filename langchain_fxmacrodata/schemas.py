"""Public research-panel request types for LangChain tool calling."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Annotated[str, Field(pattern=r"^[A-Za-z]{3}$")]
    indicator: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    max_age_days: Annotated[int, Field(ge=0, le=36500)] | None = None
    period_aggregation: Literal["monthly", "quarterly", "annual", "quarterly_average", "annual_average"] | None = None


class ResearchPanelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series: Annotated[list[ResearchSeries], Field(min_length=1, max_length=6)]
    decision_times: Annotated[list[str], Field(min_length=1, max_length=10000)]
    start_date: date
    end_date: date
    availability: Literal["public", "captured"] = "public"
    dataset_version: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
