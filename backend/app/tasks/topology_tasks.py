"""
网络拓扑自动发现 — Celery 任务
"""
import json
import ipaddress
import logging
from datetime import datetime
from sqlmodel import Session
from app.tasks.worker import celery_app
from app.core.database import engine
from app.core.config import settings

logger = logging.getLogger(__name__)


def _is_rfc1918(target: str) -> bool:
    allowed = [ipaddress.ip_network(n, strict=False) for n in settings.ALLOWED_SCAN_NETWORKS]
    try:
        net = ipaddress.ip_network(target, strict=False)
        return any(net.subnet_of(a) or net.overlaps(a) for a in allowed)
    except ValueError:
        try:
            addr = ipaddress.ip_address(target.split('/')[0])
            return any(addr in a for a in allowed)
        except ValueError:
            return False


@celery_app.task(bind=True, name='app.tasks.topology_tasks.run_topology_discovery')
def run_topology_discovery(self, task_id: int):
    """执行网络拓扑自动发现"""
    import nmap
    from app.models.topology import TopologyDiscoveryTask, TopologyNode, TopologyEdge

    with Session(engine) as session:
        task = session.get(TopologyDiscoveryTask, task_id)
        if not task:
            return {'error': f'Task {task_id} not found'}

        target = task.target_subnet
        if not _is_rfc1918(target):
            task.status = 'failed'
            task.error_message = f'目标 {target} 不在允许的内网范围内'
            task.finished_at = datetime.utcnow()
            session.add(task)
            session.commit()
            return {'error': task.error_message}

        task.status = 'running'
        task.started_at = datetime.utcnow()
        task.celery_task_id = self.request.id
        session.add(task)
        session.commit()

    try:
        # Phase 1: Nmap ping 扫描发现存活主机
        nm = nmap.PortScanner(nmap_search_path=[settings.NMAP_PATH])
        nm.scan(hosts=target, arguments='-sn')

        discovered_hosts = []
        for host in nm.all_hosts():
            if nm[host].state() == 'up':
                # addresses / vendor 是字典键，不是方法
                addr_dict = nm[host].get('addresses', {})
                mac = addr_dict.get('mac', '')
                vendor_dict = nm[host].get('vendor', {})
                vendor = vendor_dict.get(mac, '') if mac else ''
                discovered_hosts.append({
                    'ip': host,
                    'hostname': nm[host].hostname() or host,
                    'mac': mac,
                    'vendor': vendor,
                })

        # Phase 2: 推断网关 (子网中最低 IP)
        if discovered_hosts:
            sorted_hosts = sorted(discovered_hosts, key=lambda h: ipaddress.ip_address(h['ip']))
            gateway_ip = sorted_hosts[0]['ip']
        else:
            gateway_ip = None

        # Phase 3: 创建节点和边
        with Session(engine) as session:
            task = session.get(TopologyDiscoveryTask, task_id)
            nodes = []
            node_map = {}  # ip -> node_id

            for i, h in enumerate(discovered_hosts):
                is_gateway = (h['ip'] == gateway_ip)
                device_type = 'router' if is_gateway else 'server'

                # 根据 MAC OUI 推断设备类型
                if h['mac'] and h['vendor']:
                    vendor_lower = h['vendor'].lower()
                    if any(kw in vendor_lower for kw in ['cisco', 'huawei', 'h3c', 'juniper', 'mikrotik', 'router']):
                        device_type = 'router' if not is_gateway else 'router'
                    elif any(kw in vendor_lower for kw in ['switch']):
                        device_type = 'switch'

                # 分层布局坐标
                if is_gateway:
                    x, y = 400.0, 50.0
                elif device_type in ('router', 'switch'):
                    x, y = 200.0 + i * 150, 200.0
                else:
                    x, y = 50.0 + (i % 8) * 120, 350.0 + (i // 8) * 100

                node = TopologyNode(
                    name=h['hostname'],
                    ip_address=h['ip'],
                    mac_address=h['mac'] or None,
                    device_type=device_type,
                    vendor=h['vendor'] or None,
                    subnet=target,
                    position_x=x,
                    position_y=y,
                    is_manual=False,
                    discovery_task_id=task_id,
                    metadata_json=json.dumps({'hostname': h['hostname']}, ensure_ascii=False),
                )
                session.add(node)
                session.flush()
                nodes.append(node)
                node_map[h['ip']] = node.id

            # 创建边：所有主机 -> 网关
            edges_created = 0
            if gateway_ip and gateway_ip in node_map:
                gateway_node_id = node_map[gateway_ip]
                for h in discovered_hosts:
                    if h['ip'] != gateway_ip and h['ip'] in node_map:
                        edge = TopologyEdge(
                            source_node_id=gateway_node_id,
                            target_node_id=node_map[h['ip']],
                            link_type='ethernet',
                            is_manual=False,
                            discovery_task_id=task_id,
                            style='dashed',
                        )
                        session.add(edge)
                        edges_created += 1

            task.status = 'completed'
            task.progress = 100
            task.nodes_discovered = len(nodes)
            task.edges_inferred = edges_created
            task.result_json = json.dumps({
                'hosts': discovered_hosts,
                'gateway': gateway_ip,
                'nodes': len(nodes),
                'edges': edges_created,
            }, ensure_ascii=False)
            task.finished_at = datetime.utcnow()
            session.add(task)
            session.commit()

        return {'status': 'completed', 'nodes': len(nodes), 'edges': edges_created}

    except Exception as e:
        logger.exception('拓扑发现失败')
        with Session(engine) as session:
            task = session.get(TopologyDiscoveryTask, task_id)
            if task:
                task.status = 'failed'
                task.error_message = str(e)[:500]
                task.finished_at = datetime.utcnow()
                session.add(task)
                session.commit()
        raise
