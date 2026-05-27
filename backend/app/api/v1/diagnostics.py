from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.diagnostics import (
    run_ping,
    run_traceroute,
    run_dns_lookup,
    run_port_check,
    run_mtr,
)

router = APIRouter()


# ---------- Request Schemas ----------

class PingRequest(BaseModel):
    host: str = Field(..., max_length=253, description='目标主机 (IP 或域名)')
    count: int = Field(default=4, ge=1, le=100, description='发送次数')
    timeout: int = Field(default=5, ge=1, le=30, description='超时(秒)')


class TracerouteRequest(BaseModel):
    host: str = Field(..., max_length=253, description='目标主机')
    max_hops: int = Field(default=30, ge=1, le=64, description='最大跳数')
    timeout: int = Field(default=5, ge=1, le=30, description='每跳超时(秒)')


class DnsRequest(BaseModel):
    domain: str = Field(..., max_length=253, description='域名')
    record_type: str = Field(default='A', description='记录类型: A/AAAA/MX/NS/CNAME/TXT/SOA/PTR/SRV/CAA')
    dns_server: Optional[str] = Field(default=None, max_length=253, description='指定 DNS 服务器 (可选)')


class PortRequest(BaseModel):
    host: str = Field(..., max_length=253, description='目标主机')
    port: int = Field(..., ge=1, le=65535, description='端口号')
    protocol: str = Field(default='tcp', description='协议: tcp/udp')
    timeout: int = Field(default=5, ge=1, le=30, description='超时(秒)')


class MtrRequest(BaseModel):
    host: str = Field(..., max_length=253, description='目标主机')
    count: int = Field(default=10, ge=1, le=100, description='测试轮数')


# ---------- Endpoints ----------

@router.post('/ping', summary='Ping 测试')
def ping(req: PingRequest):
    return run_ping(req.host, req.count, req.timeout)


@router.post('/traceroute', summary='路由追踪')
def traceroute(req: TracerouteRequest):
    return run_traceroute(req.host, req.max_hops, req.timeout)


@router.post('/dns', summary='DNS 查询')
def dns_lookup(req: DnsRequest):
    return run_dns_lookup(req.domain, req.record_type, req.dns_server)


@router.post('/port', summary='端口检测')
def port_check(req: PortRequest):
    return run_port_check(req.host, req.port, req.protocol, req.timeout)


@router.post('/mtr', summary='MTR 综合追踪')
def mtr(req: MtrRequest):
    return run_mtr(req.host, req.count)
