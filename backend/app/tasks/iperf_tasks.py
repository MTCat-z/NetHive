import json
import subprocess
from datetime import datetime
from sqlmodel import Session
from app.tasks.worker import celery_app
from app.core.config import settings
from app.core.database import engine
from app.models.iperf_task import IperfTask

@celery_app.task(bind=True, name='app.tasks.iperf_tasks.run_iperf_test')
def run_iperf_test(self, task_id: int):
    with Session(engine) as session:
        task = session.get(IperfTask, task_id)
        if not task: return {'error': f'Task {task_id} not found'}
        task.status = 'running'; task.started_at = datetime.utcnow()
        task.celery_task_id = self.request.id
        session.add(task); session.commit()
        sh, sp, proto, dur, par, rev = task.server_host, task.server_port, task.protocol, task.duration, task.parallel, task.reverse
    try:
        cmd = [settings.IPERF3_PATH, '-c', sh, '-p', str(sp), '-t', str(dur), '-P', str(par), '-J']
        if proto == 'udp': cmd.extend(['-u', '-b', '0'])
        if rev: cmd.append('-R')
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=dur+30)
        if res.returncode != 0:
            # iperf3 -J 模式下错误可能在 JSON stdout 的 error 字段
            err_msg = res.stderr.strip()
            try:
                err_data = json.loads(res.stdout)
                err_msg = err_data.get('error', err_msg) or err_msg
            except (json.JSONDecodeError, KeyError):
                pass
            raise RuntimeError(f'iperf3 failed: {err_msg}')
        data = json.loads(res.stdout)
        # 检查 JSON 内是否有 error 字段（某些连接错误 returncode=0 但仍有 error）
        if 'error' in data:
            raise RuntimeError(f'iperf3 error: {data["error"]}')
        m = _parse(data, proto)
        with Session(engine) as session:
            task = session.get(IperfTask, task_id)
            task.status = 'completed'; task.result_json = res.stdout
            task.bandwidth_mbps = m.get('bandwidth_mbps'); task.jitter_ms = m.get('jitter_ms')
            task.lost_percent = m.get('lost_percent'); task.retransmits = m.get('retransmits')
            task.finished_at = datetime.utcnow()
            session.add(task); session.commit()
        return {'status': 'completed'}
    except Exception as e:
        with Session(engine) as session:
            task = session.get(IperfTask, task_id)
            if task:
                task.status = 'failed'; task.error_message = str(e)[:500]
                task.finished_at = datetime.utcnow()
                session.add(task); session.commit()
        raise

def _parse(data, proto):
    m = {}; end = data.get('end', {})
    try:
        if proto == 'tcp':
            s = end.get('sum_sent', {})
            m['bandwidth_mbps'] = round(s.get('bits_per_second', 0)/1e6, 2)
            m['retransmits'] = s.get('retransmits', 0)
        else:
            s = end.get('sum', {})
            m['bandwidth_mbps'] = round(s.get('bits_per_second', 0)/1e6, 2)
            m['jitter_ms'] = round(s.get('jitter_ms', 0), 3)
            total = s.get('packets', 1); lost = s.get('lost_packets', 0)
            m['lost_percent'] = round(lost/total*100, 2) if total > 0 else 0
    except: pass
    return m
