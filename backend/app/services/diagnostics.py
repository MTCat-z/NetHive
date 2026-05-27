"""
网络诊断服务 — 封装 ping/traceroute/dns/port/mtr 等诊断工具
"""
import platform
import re
import shlex
import shutil
import socket
import subprocess
import time
from typing import Optional

_IS_WINDOWS = platform.system() == 'Windows'


def _run_cmd(cmd: list[str], timeout: int = 30) -> dict:
    """执行系统命令，返回 {success, output, returncode}"""
    try:
        # Windows 命令行默认 GBK 编码，Linux 默认 UTF-8
        enc = 'gbk' if _IS_WINDOWS else 'utf-8'
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            encoding=enc,
            errors='replace',
        )
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output = output + '\n' + result.stderr if output else result.stderr
        return {
            'success': result.returncode == 0,
            'output': output.strip(),
            'returncode': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': f'命令超时 ({timeout}s)', 'returncode': -1}
    except FileNotFoundError:
        return {'success': False, 'output': f'命令不存在: {cmd[0]}', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'output': str(e), 'returncode': -1}


def _validate_host(host: str) -> bool:
    """验证主机名/IP 格式，防止命令注入"""
    if not host or len(host) > 253:
        return False
    # 禁止 shell 元字符
    if any(c in host for c in ';|&$`\\\'"!(){}[]<>?#~'):
        return False
    return True


def _validate_port(port: int) -> bool:
    return isinstance(port, int) and 1 <= port <= 65535


def run_ping(host: str, count: int = 4, timeout: int = 5) -> dict:
    """ICMP Ping 测试"""
    if not _validate_host(host):
        return {'success': False, 'output': '无效的主机地址', 'stats': None}

    count = max(1, min(count, 100))
    timeout = max(1, min(timeout, 30))

    if _IS_WINDOWS:
        # Windows: -n count, -w timeout_ms
        cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
    else:
        cmd = ['ping', '-c', str(count), '-W', str(timeout), host]

    result = _run_cmd(cmd, timeout=count * timeout + 10)

    stats = None
    if result['success']:
        stats = _parse_ping_stats(result['output'])

    return {
        'success': result['success'],
        'output': result['output'],
        'stats': stats,
    }


def _parse_ping_stats(output: str) -> Optional[dict]:
    """解析 ping 输出中的统计信息 (兼容 Linux / Windows)"""
    stats = {}

    # Linux: "4 packets transmitted, 4 received, 0% packet loss"
    pkt_match = re.search(r'(\d+)\s+packets?\s+transmitted,\s+(\d+)\s+received', output)
    if pkt_match:
        stats['sent'] = int(pkt_match.group(1))
        stats['received'] = int(pkt_match.group(2))

    # Windows: "Sent = 4, Received = 4, Lost = 0 (0% loss)"
    win_pkt = re.search(r'Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+),\s*Lost\s*=\s*(\d+)', output)
    if win_pkt:
        stats['sent'] = int(win_pkt.group(1))
        stats['received'] = int(win_pkt.group(2))

    # packet loss
    loss_match = re.search(r'(\d+)%\s*(?:packet\s+)?loss', output)
    if loss_match:
        stats['loss_percent'] = float(loss_match.group(1))

    # Linux rtt
    rtt_match = re.search(
        r'(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*'
        r'([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
        output,
    )
    if rtt_match:
        stats['min_rtt'] = float(rtt_match.group(1))
        stats['avg_rtt'] = float(rtt_match.group(2))
        stats['max_rtt'] = float(rtt_match.group(3))

    # Windows rtt: "Minimum = 1ms, Maximum = 3ms, Average = 2ms"
    win_rtt = re.search(
        r'Minimum\s*=\s*(\d+)ms,\s*Maximum\s*=\s*(\d+)ms,\s*Average\s*=\s*(\d+)ms',
        output,
    )
    if win_rtt:
        stats['min_rtt'] = float(win_rtt.group(1))
        stats['max_rtt'] = float(win_rtt.group(2))
        stats['avg_rtt'] = float(win_rtt.group(3))

    return stats if stats else None


def run_traceroute(host: str, max_hops: int = 30, timeout: int = 5) -> dict:
    """Traceroute 路由追踪"""
    if not _validate_host(host):
        return {'success': False, 'output': '无效的主机地址', 'hops': []}

    max_hops = max(1, min(max_hops, 64))
    timeout = max(1, min(timeout, 30))

    if _IS_WINDOWS:
        # Windows: tracert -h max_hops -w timeout_ms
        cmd = ['tracert', '-h', str(max_hops), '-w', str(timeout * 1000), host]
    else:
        cmd = ['traceroute', '-m', str(max_hops), '-w', str(timeout), host]

    result = _run_cmd(cmd, timeout=max_hops * timeout + 15)

    hops = _parse_traceroute_hops(result['output']) if result['success'] else []

    return {
        'success': result['success'],
        'output': result['output'],
        'hops': hops,
    }


def _parse_traceroute_hops(output: str) -> list[dict]:
    """解析 traceroute/tracert 输出中的跳数信息 (兼容 Linux / Windows)"""
    hops = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # Linux: " 1  hostname (ip)  rtt1  rtt2  rtt3"
        match = re.match(
            r'\s*(\d+)\s+(\S+)\s+\(([\d.]+)\)\s+([\d.]+)\s+ms\s+([\d.]+)\s+ms\s+([\d.]+)\s+ms',
            line,
        )
        if match:
            hops.append({
                'hop': int(match.group(1)),
                'hostname': match.group(2),
                'ip': match.group(3),
                'rtt1': float(match.group(4)),
                'rtt2': float(match.group(5)),
                'rtt3': float(match.group(6)),
            })
            continue

        # Windows: "  1     2 ms     1 ms     1 ms  192.168.1.1"
        win_match = re.match(
            r'\s*(\d+)\s+(?:<1\s+ms|(\d+)\s+ms)\s+(?:<1\s+ms|(\d+)\s+ms)\s+(?:<1\s+ms|(\d+)\s+ms)\s+(.+)',
            line,
        )
        if win_match:
            hop_num = int(win_match.group(1))
            rtt1 = float(win_match.group(2)) if win_match.group(2) else 0.0
            rtt2 = float(win_match.group(3)) if win_match.group(3) else 0.0
            rtt3 = float(win_match.group(4)) if win_match.group(4) else 0.0
            target = win_match.group(5).strip()
            # Try to extract IP from "hostname [ip]" format
            ip_match = re.search(r'\[([\d.]+)\]', target)
            ip = ip_match.group(1) if ip_match else target
            hostname = re.sub(r'\s*\[[\d.]+\]', '', target).strip()
            hops.append({
                'hop': hop_num,
                'hostname': hostname,
                'ip': ip,
                'rtt1': rtt1,
                'rtt2': rtt2,
                'rtt3': rtt3,
            })
            continue

        # 超时跳: " 2  * * *"
        timeout_match = re.match(r'\s*(\d+)\s+(\*\s+\*\s+\*|.*\*.*\*.*)', line)
        if timeout_match:
            hops.append({
                'hop': int(timeout_match.group(1)),
                'hostname': '*',
                'ip': '*',
                'rtt1': None,
                'rtt2': None,
                'rtt3': None,
            })

    return hops


def run_dns_lookup(domain: str, record_type: str = 'A', dns_server: Optional[str] = None) -> dict:
    """DNS 查询"""
    if not _validate_host(domain):
        return {'success': False, 'output': '无效的域名', 'records': []}

    record_type = record_type.upper()
    valid_types = {'A', 'AAAA', 'MX', 'NS', 'CNAME', 'TXT', 'SOA', 'PTR', 'SRV', 'CAA'}
    if record_type not in valid_types:
        return {'success': False, 'output': f'不支持的记录类型: {record_type}', 'records': []}

    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        if dns_server:
            if not _validate_host(dns_server):
                return {'success': False, 'output': '无效的 DNS 服务器地址', 'records': []}
            resolver.nameservers = [dns_server]
        resolver.lifetime = 10

        answers = resolver.resolve(domain, record_type)
        records = []
        for rdata in answers:
            records.append({
                'type': record_type,
                'value': str(rdata),
                'ttl': answers.rrset.ttl,
            })

        output_lines = [f'{domain}.\t\t{r["ttl"]}\tIN\t{r["type"]}\t{r["value"]}' for r in records]
        return {
            'success': True,
            'output': '\n'.join(output_lines),
            'records': records,
        }
    except ImportError:
        # dnspython 未安装时降级到 nslookup
        cmd = ['nslookup', f'-type={record_type}', domain]
        if dns_server:
            cmd.append(dns_server)
        result = _run_cmd(cmd, timeout=15)
        return {
            'success': result['success'],
            'output': result['output'],
            'records': [],
        }
    except Exception as e:
        return {
            'success': False,
            'output': f'DNS 查询失败: {e}',
            'records': [],
        }


def run_port_check(host: str, port: int, protocol: str = 'tcp', timeout: int = 5) -> dict:
    """端口连通性检测"""
    if not _validate_host(host):
        return {'success': False, 'open': False, 'output': '无效的主机地址', 'latency_ms': None}
    if not _validate_port(port):
        return {'success': False, 'open': False, 'output': '无效的端口号', 'latency_ms': None}

    timeout = max(1, min(timeout, 30))
    protocol = protocol.lower()

    if protocol == 'tcp':
        return _tcp_port_check(host, port, timeout)
    elif protocol == 'udp':
        return _udp_port_check(host, port, timeout)
    else:
        return {'success': False, 'open': False, 'output': f'不支持的协议: {protocol}', 'latency_ms': None}


def _tcp_port_check(host: str, port: int, timeout: int) -> dict:
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        latency = round((time.time() - start) * 1000, 2)
        # 尝试获取 banner
        banner = None
        try:
            sock.settimeout(2)
            data = sock.recv(1024)
            if data:
                banner = data.decode('utf-8', errors='replace').strip()[:200]
        except (socket.timeout, OSError):
            pass
        sock.close()
        return {
            'success': True,
            'open': True,
            'output': f'TCP {host}:{port} 开放 (延迟 {latency}ms)',
            'latency_ms': latency,
            'banner': banner,
        }
    except socket.timeout:
        latency = round((time.time() - start) * 1000, 2)
        return {
            'success': True,
            'open': False,
            'output': f'TCP {host}:{port} 连接超时',
            'latency_ms': latency,
            'banner': None,
        }
    except ConnectionRefusedError:
        latency = round((time.time() - start) * 1000, 2)
        return {
            'success': True,
            'open': False,
            'output': f'TCP {host}:{port} 连接被拒绝 (端口关闭)',
            'latency_ms': latency,
            'banner': None,
        }
    except OSError as e:
        return {
            'success': False,
            'open': False,
            'output': f'TCP {host}:{port} 检测失败: {e}',
            'latency_ms': None,
            'banner': None,
        }


def _udp_port_check(host: str, port: int, timeout: int) -> dict:
    """UDP 端口检测（UDP 检测不完全可靠，仅作参考）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        start = time.time()
        sock.sendto(b'\x00', (host, port))
        try:
            data, _ = sock.recvfrom(1024)
            latency = round((time.time() - start) * 1000, 2)
            sock.close()
            return {
                'success': True,
                'open': True,
                'output': f'UDP {host}:{port} 可能有服务 (收到响应)',
                'latency_ms': latency,
                'banner': None,
            }
        except socket.timeout:
            latency = round((time.time() - start) * 1000, 2)
            sock.close()
            return {
                'success': True,
                'open': None,  # UDP 超时不能确定端口状态
                'output': f'UDP {host}:{port} 无响应 (端口可能开放或过滤)',
                'latency_ms': latency,
                'banner': None,
            }
    except Exception as e:
        return {
            'success': False,
            'open': False,
            'output': f'UDP {host}:{port} 检测失败: {e}',
            'latency_ms': None,
            'banner': None,
        }


def run_mtr(host: str, count: int = 10) -> dict:
    """MTR 综合路由追踪 (Linux: mtr, Windows: 降级为 tracert)"""
    if not _validate_host(host):
        return {'success': False, 'output': '无效的主机地址', 'hops': []}

    count = max(1, min(count, 100))

    if _IS_WINDOWS:
        # Windows 无 mtr，降级为 tracert
        cmd = ['tracert', '-h', '30', '-w', '3000', host]
        result = _run_cmd(cmd, timeout=120)
        hops = _parse_traceroute_hops(result['output']) if result['success'] else []
        return {
            'success': result['success'],
            'output': result['output'] + '\n\n(Windows 环境无 MTR，使用 tracert 替代)',
            'hops': hops,
        }

    cmd = ['mtr', '--report', '--report-cycles', str(count), '--no-dns', host]
    result = _run_cmd(cmd, timeout=count * 5 + 15)

    hops = []
    if result['success']:
        hops = _parse_mtr_report(result['output'])

    return {
        'success': result['success'],
        'output': result['output'],
        'hops': hops,
    }


def _parse_mtr_report(output: str) -> list[dict]:
    """解析 MTR report 输出 (兼容多种格式)"""
    hops = []
    in_report = False
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # 检测报告头部: "HOST" 或 "Host" 开头
        if line.upper().startswith('HOST'):
            in_report = True
            continue
        if not in_report:
            continue
        # 格式 1: "  1.|-- 127.0.0.1   0.0%  3  0.1  0.1  0.1  0.1  0.0"
        m1 = re.match(
            r'(\d+)\.\|--\s+(\S+)\s+([\d.]+)%\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',
            line,
        )
        # 格式 2: "HOST   Loss%  Snt  Last  Avg  Best  Wrst  StDev"
        m2 = re.match(
            r'(\S+)\s+([\d.]+)%\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',
            line,
        )
        m = m1 or m2
        if m:
            groups = m.groups()
            try:
                if m1:
                    hops.append({
                        'hop': int(groups[0]),
                        'host': groups[1],
                        'loss_percent': float(groups[2]),
                        'sent': int(groups[3]),
                        'last': float(groups[4]),
                        'avg': float(groups[5]),
                        'best': float(groups[6]),
                        'worst': float(groups[7]),
                        'stdev': float(groups[8]),
                    })
                else:
                    hops.append({
                        'hop': len(hops) + 1,
                        'host': groups[0],
                        'loss_percent': float(groups[1]),
                        'sent': int(groups[2]),
                        'last': float(groups[3]),
                        'avg': float(groups[4]),
                        'best': float(groups[5]),
                        'worst': float(groups[6]),
                        'stdev': float(groups[7]),
                    })
            except (ValueError, IndexError):
                continue
    return hops
