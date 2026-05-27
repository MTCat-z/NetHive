from typing import Optional
from fastapi import APIRouter, Query
from app.services import zabbix_service
from app.services.zabbix_cache import clear_cache

router = APIRouter()


@router.get('/status', summary='Zabbix 连接状态')
def status():
    return zabbix_service.get_status()


@router.get('/hosts', summary='主机列表')
def hosts():
    return zabbix_service.get_monitored_hosts()


@router.get('/hosts/{host_id}', summary='主机详情')
def host_detail(host_id: str):
    return zabbix_service.get_host_detail(host_id)


@router.get('/hosts/{host_id}/metrics', summary='主机指标')
def host_metrics(host_id: str, period: str = Query('1h', description='时间段: 1h/6h/24h/7d')):
    return zabbix_service.get_host_metrics(host_id, period)


@router.get('/problems', summary='活跃问题')
def problems():
    return zabbix_service.get_active_problems()


@router.get('/events', summary='近期事件')
def events(host_id: Optional[str] = None, limit: int = Query(50, ge=1, le=200)):
    return zabbix_service.get_events(host_id=host_id, limit=limit)


@router.get('/triggers', summary='活跃触发器')
def triggers(host_id: Optional[str] = None):
    return zabbix_service.get_triggers(host_id=host_id)


@router.get('/dashboard', summary='仪表盘汇总')
def dashboard():
    return zabbix_service.get_dashboard_summary()


@router.post('/cache/clear', summary='清除缓存')
def cache_clear():
    clear_cache()
    return {'cleared': True}
