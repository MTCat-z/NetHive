from fastapi import APIRouter
from app.api.v1 import assets, scan, iperf, diagnostics, broadband, topology, zabbix

api_router = APIRouter()
api_router.include_router(assets.router, prefix='/assets', tags=['资产管理'])
api_router.include_router(scan.router, prefix='/scan', tags=['Nmap扫描'])
api_router.include_router(iperf.router, prefix='/iperf', tags=['Iperf3测速'])
api_router.include_router(diagnostics.router, prefix='/diagnostics', tags=['网络诊断'])
api_router.include_router(broadband.router, prefix='/broadband', tags=['宽带管理'])
api_router.include_router(topology.router, prefix='/topology', tags=['网络拓扑'])
api_router.include_router(zabbix.router, prefix='/zabbix', tags=['Zabbix监控'])
