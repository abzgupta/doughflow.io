"""
Request models for the DoughFlow API.

Models allow extra fields so clients can send additional data without
breaking validation; defaults mirror what the endpoints assume when a
field is omitted.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra='allow')


# ============= Graph =============

class GraphNode(ApiModel):
    id: str
    type: str  # module type, e.g. "salary", "real_estate"
    config: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(ApiModel):
    source: str
    target: str
    flow_type: str = 'fixed'  # 'fixed', 'percentage', 'remainder'
    amount: float = 0
    frequency: str = 'monthly'  # 'monthly', 'quarterly', 'annually'
    priority: int = 0  # Lower = higher priority
    condition: Optional[Dict[str, Any]] = None


class SimulationConfigModel(ApiModel):
    start_year: int = 2024
    start_month: int = 1
    duration_months: int = 120


class GraphRequest(ApiModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


# ============= Simulation =============

class SimulateRequest(GraphRequest):
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    config: SimulationConfigModel = Field(default_factory=SimulationConfigModel)


class StepRequest(GraphRequest):
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    node_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    current_year: int = 2024
    current_month: int = 1
    month_number: int = 1


class ContinueRequest(SimulateRequest):
    resume_from_month: int = 1
    node_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class TransactionRequest(ApiModel):
    transaction_type: Optional[str] = None  # 'sell_stocks', 'pay_debt', 'transfer'
    nodes: List[GraphNode] = Field(default_factory=list)
    node_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    year: int = 2024
    month: int = 1
    params: Dict[str, Any] = Field(default_factory=dict)


# ============= Tax =============

class TaxCalculateRequest(ApiModel):
    income: Dict[str, Any] = Field(default_factory=dict)
    deductions: Dict[str, Any] = Field(default_factory=dict)
    credits: Dict[str, Any] = Field(default_factory=dict)
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    withholding: float = 0
    estimated_payments: float = 0


class TaxImpactRequest(ApiModel):
    base_scenario: Dict[str, Any] = Field(default_factory=dict)
    change: Dict[str, Any] = Field(default_factory=dict)


# ============= Legacy =============

class PropertyListRequest(ApiModel):
    property_list: List[Dict[str, Any]] = Field(default_factory=list)
