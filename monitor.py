"""作者：Wangyuan；日期：2026-10-29；职责：显式参数的时间窗口、风险边界及进度监控。"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from fractions import Fraction
from typing import Any


def stamp(value: str) -> datetime:
    """只接受带时区时间。"""
    result = datetime.fromisoformat(value)
    if result.tzinfo is None: raise ValueError("缺少时区")
    return result.astimezone(timezone.utc)


def number(value: int | float, name: str) -> int | float:
    """保留整数精度并拒绝布尔与非有限数。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or isinstance(value, float) and not math.isfinite(value): raise ValueError(name + "不是有限数")
    return value


def weighted_quantile(values: list[int | float], weights: list[int | float], probability: float) -> int | float:
    """按累计十进制有理权重取样本分位数，不插值。"""
    number(probability, "概率")
    if not values or len(values) != len(weights) or not 0 <= probability <= 1: raise ValueError("样本或概率无效")
    pairs = []
    for value, weight in zip(values, weights):
        number(value, "值"); number(weight, "权重")
        if weight < 0: raise ValueError("权重不能为负")
        if weight: pairs.append((value, Fraction(str(weight))))
    if not pairs: raise ValueError("有效权重为空")
    pairs.sort(); target = Fraction(str(probability)) * sum((x[1] for x in pairs), Fraction()); running = Fraction()
    for value, weight in pairs:
        running += weight
        if running >= target: return value
    return pairs[-1][0]


def distribution(samples: list[dict], target: str, *, half_life_days: float,
                 levels: list[dict], probabilities: list[float], cutoff: str) -> dict:
    """按显式月份/小时匹配层次及新近程度计算分位区间，未来样本不使用。"""
    if number(half_life_days, "半衰期") <= 0: raise ValueError("半衰期须为正")
    now, desired = stamp(cutoff), stamp(target)
    for probability in probabilities:
        if not 0 <= number(probability, "概率") <= 1: raise ValueError("概率无效")
    valid = []
    for sample in samples:
        when = stamp(sample["timestamp"]); duration = number(sample["duration"], "时长")
        if duration < 0: raise ValueError("时长不能为负")
        if when <= now: valid.append((when, duration))
    for index, level in enumerate(levels):
        minimum = level.get("minimum_samples")
        if type(minimum) is not int or minimum < 1: raise ValueError("样本门槛须显式为正整数")
        radius = level.get("hour_radius")
        if radius is not None and (number(radius, "小时窗口") < 0 or radius > 12): raise ValueError("小时窗口无效")
        chosen = [(when, value) for when, value in valid if
                  (not level.get("same_month", False) or when.month == desired.month) and
                  (radius is None or min(abs(when.hour - desired.hour), 24 - abs(when.hour - desired.hour)) <= radius)]
        if len(chosen) < minimum: continue
        newest=max(when for when,_ in chosen)
        weights = [2 ** (-((newest - when).total_seconds() / 86400) / half_life_days) for when, _ in chosen]
        if not any(weights): continue
        return {"status": "available", "level": index, "samples": len(chosen),
                "quantiles": {str(p): weighted_quantile([v for _, v in chosen], weights, p) for p in probabilities}}
    return {"status": "missing", "level": None, "samples": len(valid), "quantiles": None}


def interval_truth(known: int, unknown: int, denominator: int | None, percent: int | float,
                   *, applicable: bool = True, semantics_ready: bool = True) -> str:
    """三态区间比较：已知下界和未知上界，不把未知计成零。"""
    if any(type(x) is not int or x < 0 for x in (known, unknown)): raise ValueError("计数须为非负整数")
    if denominator is not None and (type(denominator) is not int or denominator < 0 or known + unknown > denominator): raise ValueError("分母或上下界无效")
    if not 0 <= number(percent, "比例") <= 100: raise ValueError("比例无效")
    if not applicable or denominator == 0: return "not_applicable"
    if denominator is None or not semantics_ready: return "unknown"
    threshold = Fraction(str(percent)) * denominator
    if known * 100 >= threshold: return "true"
    if (known + unknown) * 100 < threshold: return "false"
    return "unknown"


def tri_or(states: list[str]) -> str:
    """按真实、未知、假、无适用项的顺序聚合。"""
    if set(states) - {"true", "false", "unknown", "not_applicable"}: raise ValueError("三态值无效")
    for value in ["true", "unknown", "false"]:
        if value in states: return value
    return "not_applicable"


def tier_bounds(tiers: list[dict]) -> dict:
    """输出已证明最高级与仍可能最高级，级别须由调用方显式排序。"""
    proven = possible = None
    for tier in tiers:
        state = tri_or(tier["branches"])
        if state == "true": proven = tier["id"]
        if state in {"true", "unknown"}: possible = tier["id"]
    return {"proven": proven, "possible": possible, "requires_review": proven != possible}


def monitor_milestones(items: list[dict], expected_ids: list[str], now: str, *, max_age_seconds: int) -> dict:
    """检查节点覆盖、时效、逾期与偏差；未完成不等于完成为零。"""
    if type(max_age_seconds) is not int or max_age_seconds < 0: raise ValueError("时效无效")
    moment = stamp(now); lookup = {}; result = []
    if len(set(expected_ids)) != len(expected_ids): raise ValueError("节点清单重复")
    for item in items:
        if item["id"] in lookup: raise ValueError("节点身份重复")
        lookup[item["id"]] = item
    for identifier in expected_ids:
        item = lookup.get(identifier)
        if item is None:
            result.append({"id": identifier, "state": "missing", "deviation_seconds": None}); continue
        observed = stamp(item["observed_at"])
        age = (moment - observed).total_seconds()
        planned = stamp(item["planned_at"]); actual = stamp(item["actual_at"]) if item.get("actual_at") else None
        state = "future_observation" if age < 0 else "future_actual" if actual and actual > min(moment, observed) else "stale" if age > max_age_seconds else "completed" if actual else "overdue" if moment > planned else "pending"
        result.append({"id": identifier, "state": state, "deviation_seconds": (actual - planned).total_seconds() if actual and actual<=min(moment,observed) else None})
    result.sort(key=lambda x: ({"missing": 0, "future_observation": 1, "future_actual": 1, "stale": 2, "overdue": 3, "pending": 4, "completed": 5}[x["state"]], x["id"]))
    counts = {state: sum(x["state"] == state for x in result) for state in {x["state"] for x in result}}
    return {"items": result, "counts": counts, "total": len(result), "unrequested": sorted(set(lookup) - set(expected_ids))}


def escalate(current_level: int, seen_levels: list[int], elapsed_seconds: float | None,
             thresholds: list[float], *, source_ready: bool) -> dict:
    """单调升级和每级一次提示；未知来源阻断，输出仅是本地待复核草稿。"""
    if type(current_level) is not int or not 0 <= current_level <= len(thresholds): raise ValueError("当前级别无效")
    if any(number(x, "阈值") < 0 for x in thresholds) or thresholds != sorted(set(thresholds)): raise ValueError("阈值须严格递增且非负")
    if any(type(x) is not int or not 1 <= x <= len(thresholds) for x in seen_levels): raise ValueError("已提示级别无效")
    if not source_ready or elapsed_seconds is None: return {"state": "blocked", "level": current_level, "new_levels": [], "seen_levels": sorted(set(seen_levels))}
    if number(elapsed_seconds, "经过时间") < 0: raise ValueError("时间不能倒退")
    level = max(current_level, sum(elapsed_seconds >= x for x in thresholds))
    new = [x for x in range(1, level + 1) if x not in seen_levels]
    return {"state": "draft" if new else "unchanged", "level": level, "new_levels": new, "seen_levels": sorted(set(seen_levels) | set(new))}


def chain_windows(items: list[dict], window_start: str, window_end: str) -> dict:
    """按资产排序任务链，窗口交集、间隔及输入延误传播均保留证据。"""
    left, right = stamp(window_start), stamp(window_end)
    if right <= left: raise ValueError("时间窗口无效")
    groups: dict[str, list[dict]] = {}; seen = set()
    for item in items:
        if item["id"] in seen: raise ValueError("任务身份重复")
        seen.add(item["id"]); start, end = stamp(item["start"]), stamp(item["end"])
        if end <= start: raise ValueError("任务时间无效")
        if start < right: groups.setdefault(item["asset"], []).append(item)
    chains = {}
    for asset, rows in groups.items():
        rows.sort(key=lambda x: (stamp(x["start"]), x["id"])); previous_end = None; previous_delay = 0; output = []
        for row in rows:
            start, end = stamp(row["start"]), stamp(row["end"])
            gap = (start - previous_end).total_seconds() if previous_end else None
            delay = row.get("delay_seconds")
            if delay is not None and number(delay, "延误") < 0: raise ValueError("延误不能为负")
            inherited = max(0, previous_delay - max(gap or 0, 0)) if previous_delay is not None else None
            projected = max(delay, inherited) if delay is not None and inherited is not None else None
            output.append({**row, "gap_seconds": gap, "overlap": gap is not None and gap < 0, "projected_delay_seconds": projected, "state": "missing" if projected is None else "available"})
            previous_end, previous_delay = end, projected
        visible = [item for item in output if left < stamp(item["end"])]
        if visible:
            chains[asset] = visible
    return {"chains": chains, "window": [window_start, window_end]}


def compare_plan(before: list[dict], after: list[dict], identity_fields: list[str]) -> dict:
    """组合身份进行稳定版本比较，拒绝重复及缺字段。"""
    if not identity_fields: raise ValueError("身份字段不能为空")
    def index(rows: list[dict]) -> dict[str, dict]:
        """按显式身份建立索引，遇到冲突拒绝静默覆盖。"""
        output = {}
        for row in rows:
            key = json.dumps([row[x] for x in identity_fields], ensure_ascii=False)
            if key in output: raise ValueError("计划身份重复")
            output[key] = row
        return output
    left, right = index(before), index(after)
    encoded = json.dumps(after, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return {"fingerprint": hashlib.sha256(encoded.encode()).hexdigest(), "added": [right[k] for k in sorted(right.keys() - left.keys())],
            "removed": [left[k] for k in sorted(left.keys() - right.keys())],
            "changed": [{"before": left[k], "after": right[k]} for k in sorted(left.keys() & right.keys()) if json.dumps(left[k],sort_keys=True,allow_nan=False) != json.dumps(right[k],sort_keys=True,allow_nan=False)]}


def affected_events(windows: list[dict], events: list[dict], threshold: float) -> dict:
    """按显式地点与半开时间区间关联事件，不内置任何行业告警标准。"""
    number(threshold, "阈值"); matches = []
    for window in windows:
        left, right = stamp(window["start"]), stamp(window["end"])
        if right <= left: raise ValueError("影响窗口无效")
        value = window.get("value")
        if value is None: continue
        if number(value, "指标") < threshold: continue
        for event in events:
            if event["location"] == window["location"] and left <= stamp(event["timestamp"]) < right:
                matches.append({"window": window["id"], "event": event["id"], "value": value})
    return {"matches": matches, "missing_windows": [x["id"] for x in windows if x.get("value") is None]}
