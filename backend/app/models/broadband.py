from datetime import datetime, date
from typing import Optional
from sqlmodel import Field, SQLModel


class BroadbandContractBase(SQLModel):
    provider: str = Field(..., max_length=100)
    circuit_id: Optional[str] = Field(default=None, max_length=100)
    bandwidth_mbps: int = Field(...)
    location: Optional[str] = Field(default=None, max_length=200)
    monthly_cost: Optional[float] = Field(default=None)
    annual_cost: Optional[float] = Field(default=None)
    contract_start: date = Field(...)
    contract_end: date = Field(...)
    auto_renew: bool = Field(default=False)
    contact_name: Optional[str] = Field(default=None, max_length=50)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    reminder_days: str = Field(default='30,15,7', max_length=100)
    status: str = Field(default='active', max_length=20)
    notes: Optional[str] = Field(default=None, max_length=2000)


class BroadbandContract(BroadbandContractBase, table=True):
    __tablename__ = 'broadband_contracts'
    id: Optional[int] = Field(default=None, primary_key=True)
    notified_dates: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BroadbandContractCreate(BroadbandContractBase):
    pass


class BroadbandContractUpdate(SQLModel):
    provider: Optional[str] = None
    circuit_id: Optional[str] = None
    bandwidth_mbps: Optional[int] = None
    location: Optional[str] = None
    monthly_cost: Optional[float] = None
    annual_cost: Optional[float] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    auto_renew: Optional[bool] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    reminder_days: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class BroadbandContractRead(BroadbandContractBase):
    id: int
    created_at: datetime
    updated_at: datetime
