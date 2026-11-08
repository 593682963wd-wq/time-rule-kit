"""作者：Wangyuan；日期：2026-10-29；职责：独立离线JSON命令行入口。"""
from __future__ import annotations
import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from monitor import distribution, interval_truth, tier_bounds, monitor_milestones, escalate, chain_windows, compare_plan, affected_events
def run(payload: dict, output: Path) -> Any:
    """运行显式配置的监控算法，无定时器或发送器。"""
    actions = {"distribution": distribution, "truth": interval_truth, "tiers": tier_bounds, "milestones": monitor_milestones, "escalate": escalate, "chains": chain_windows, "compare": compare_plan, "affected": affected_events}
    if payload["action"] not in actions: raise ValueError("未知动作")
    return actions[payload["action"]](**payload["args"])

def demo(output: Path) -> dict:
    """合成时间链、未知比例与里程碑。"""
    items = [{"id": "step-1", "asset": "asset-1", "start": "2030-01-01T10:00:00+00:00", "end": "2030-01-01T11:00:00+00:00", "delay_seconds": 600}, {"id": "step-2", "asset": "asset-1", "start": "2030-01-01T11:05:00+00:00", "end": "2030-01-01T12:00:00+00:00", "delay_seconds": 0}]
    return {"chains": chain_windows(items, "2030-01-01T00:00:00+00:00", "2030-01-02T00:00:00+00:00"), "uncertainty": interval_truth(2, 2, 10, 30), "milestones": monitor_milestones([{ "id": "step-1", "planned_at": "2030-01-01T10:00:00+00:00", "observed_at": "2030-01-01T12:00:00+00:00", "actual_at": None}], ["step-1", "step-2"], "2030-01-01T12:00:00+00:00", max_age_seconds=300)}

def main() -> int:
    """运行合成演示或显式输入；错误返回非零，不访问外部服务。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo", "run"])
    parser.add_argument("input", nargs="?")
    parser.add_argument("--output", help="显式输出目录；默认临时目录")
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(args.output or temporary)
            output.mkdir(parents=True, exist_ok=True)
            if args.command == "demo":
                result = demo(output)
            else:
                if not args.input:
                    raise ValueError("run必须提供JSON文件")
                source = Path(args.input)
                if source.stat().st_size > 10_000_000:
                    raise ValueError("JSON文件超出预算")
                result = run(json.loads(source.read_text(encoding="utf-8")), output)
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
if __name__ == "__main__":
    raise SystemExit(main())
