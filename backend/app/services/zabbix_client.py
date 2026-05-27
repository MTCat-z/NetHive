"""
Zabbix JSON-RPC 2.0 API 客户端
"""
import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class ZabbixAPIError(Exception):
    def __init__(self, code: int, message: str, data: str = ''):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f'Zabbix API Error [{code}]: {message} - {data}')


class ZabbixClient:
    def __init__(self):
        self.url = settings.ZABBIX_URL
        self.api_token = settings.ZABBIX_API_TOKEN
        self.user = settings.ZABBIX_USER
        self.password = settings.ZABBIX_PASSWORD
        self.verify_ssl = settings.ZABBIX_VERIFY_SSL
        self.timeout = settings.ZABBIX_TIMEOUT
        self._auth_token: Optional[str] = None
        self._request_id = 0

    def _is_configured(self) -> bool:
        return bool(self.url)

    def _get_client(self) -> httpx.Client:
        return httpx.Client(verify=self.verify_ssl, timeout=self.timeout)

    def _rpc(self, method: str, params: dict = None, no_auth: bool = False) -> dict:
        if not self._is_configured():
            raise ZabbixAPIError(-1, 'Zabbix 未配置', '请设置 ZABBIX_URL')

        self._request_id += 1
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or {},
            'id': self._request_id,
        }

        headers = {'Content-Type': 'application/json-rpc'}

        # 认证方式 (no_auth 模式跳过认证头)
        if not no_auth:
            if self.api_token:
                headers['Authorization'] = f'Bearer {self.api_token}'
            elif self._auth_token:
                payload['auth'] = self._auth_token

        with self._get_client() as client:
            resp = client.post(self.url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if 'error' in data:
            err = data['error']
            raise ZabbixAPIError(err.get('code', -1), err.get('message', ''), err.get('data', ''))

        return data.get('result')

    def _ensure_auth(self):
        """确保已认证（user.login 模式）"""
        if self.api_token or self._auth_token:
            return
        if self.user and self.password:
            self._auth_token = self._rpc('user.login', {
                'username': self.user,
                'password': self.password,
            })

    def test_connection(self) -> dict:
        if not self._is_configured():
            return {'available': False, 'error': 'Zabbix 未配置'}
        try:
            # Zabbix 7.x: apiinfo.version 不允许携带认证头
            version = self._rpc('apiinfo.version', no_auth=True)
            return {'available': True, 'version': version}
        except Exception as e:
            return {'available': False, 'error': str(e)}

    def get_hosts(self) -> list:
        self._ensure_auth()
        return self._rpc('host.get', {
            'output': ['hostid', 'host', 'name', 'status', 'available'],
            'selectInterfaces': ['ip'],
            'selectGroups': ['groupid', 'name'],
            'selectTags': ['tag', 'value'],
            'sortfield': 'name',
        }) or []

    def get_problems(self, recent: bool = False) -> list:
        self._ensure_auth()
        return self._rpc('problem.get', {
            'output': ['eventid', 'objectid', 'name', 'severity', 'clock', 'acknowledged'],
            'selectTags': 'extend',
            'recent': recent,
            'sortfield': ['eventid'],
            'sortorder': 'DESC',
            'limit': 100,
        }) or []

    def get_triggers(self, host_id: str = None) -> list:
        self._ensure_auth()
        params = {
            'output': ['triggerid', 'description', 'priority', 'lastchange', 'status', 'value'],
            'selectHosts': ['host', 'name'],
            'expandDescription': True,
            'filter': {'value': 1},
            'sortfield': 'priority',
            'sortorder': 'DESC',
        }
        if host_id:
            params['hostids'] = [host_id]
        return self._rpc('trigger.get', params) or []

    def get_events(self, host_id: str = None, limit: int = 50) -> list:
        self._ensure_auth()
        params = {
            'output': ['eventid', 'name', 'severity', 'clock', 'r_clock', 'acknowledged', 'value'],
            'selectHosts': ['host', 'name'],
            'sortfield': ['eventid'],
            'sortorder': 'DESC',
            'limit': limit,
        }
        if host_id:
            params['hostids'] = [host_id]
        return self._rpc('event.get', params) or []

    def get_host_metrics(self, host_id: str, period: str = '1h') -> dict:
        self._ensure_auth()
        import time
        now = int(time.time())
        period_map = {'1h': 3600, '6h': 21600, '24h': 86400, '7d': 604800}
        seconds = period_map.get(period, 3600)
        time_from = now - seconds

        metrics = {'cpu': [], 'memory': [], 'disk': {}, 'network': {'in': [], 'out': []}}

        # 获取 CPU 使用率
        items = self._rpc('item.get', {
            'hostids': [host_id],
            'search': {'key_': 'system.cpu.util'},
            'output': ['itemid', 'name'],
            'limit': 1,
        })
        if items:
            history = self._rpc('history.get', {
                'itemids': [items[0]['itemid']],
                'time_from': time_from,
                'time_till': now,
                'sortfield': 'clock',
                'limit': 500,
            })
            metrics['cpu'] = [{'t': h['clock'], 'v': round(float(h['value']), 2)} for h in (history or [])]

        # 获取内存
        mem_items = self._rpc('item.get', {
            'hostids': [host_id],
            'search': {'key_': 'vm.memory.size'},
            'output': ['itemid', 'key_'],
        })
        if mem_items:
            total_item = next((i for i in mem_items if 'total' in i['key_']), None)
            avail_item = next((i for i in mem_items if 'available' in i['key_'] or 'free' in i['key_']), None)
            if total_item and avail_item:
                for key, item in [('total', total_item), ('available', avail_item)]:
                    history = self._rpc('history.get', {
                        'itemids': [item['itemid']],
                        'time_from': time_from,
                        'time_till': now,
                        'sortfield': 'clock',
                        'limit': 500,
                    })
                    metrics['memory'].extend([{'t': h['clock'], 'v': round(float(h['value']) / 1073741824, 2)} for h in (history or [])])

        return metrics


_client: Optional[ZabbixClient] = None

def get_zabbix_client() -> ZabbixClient:
    global _client
    if _client is None:
        _client = ZabbixClient()
    return _client
