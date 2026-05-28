from fastapi import APIRouter, Depends
from app.api.v1 import assets, scan, iperf, diagnostics, broadband, topology, zabbix, auth, users, audit
from app.core.auth import get_current_user

api_router = APIRouter()

# 公开路由（无需认证）
api_router.include_router(auth.router, prefix='/auth', tags=['认证'])

# 需要认证的路由
_auth = [Depends(get_current_user)]
api_router.include_router(users.router, prefix='/users', tags=['用户管理'], dependencies=_auth)
api_router.include_router(audit.router, prefix='/audit', tags=['审计日志'], dependencies=_auth)
api_router.include_router(assets.router, prefix='/assets', tags=['资产管理'], dependencies=_auth)
api_router.include_router(scan.router, prefix='/scan', tags=['Nmap扫描'], dependencies=_auth)
api_router.include_router(iperf.router, prefix='/iperf', tags=['Iperf3测速'], dependencies=_auth)
api_router.include_router(diagnostics.router, prefix='/diagnostics', tags=['网络诊断'], dependencies=_auth)
api_router.include_router(broadband.router, prefix='/broadband', tags=['宽带管理'], dependencies=_auth)
api_router.include_router(topology.router, prefix='/topology', tags=['网络拓扑'], dependencies=_auth)
api_router.include_router(zabbix.router, prefix='/zabbix', tags=['Zabbix监控'], dependencies=_auth)
