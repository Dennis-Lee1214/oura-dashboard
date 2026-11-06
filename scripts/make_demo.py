#!/usr/bin/env python3
"""生成假数据到 docs/data/demo/，格式和 Oura API v2 返回的一致。

演示版网页用这些数据，可以放心提交到公开仓库。
    python3 scripts/make_demo.py            # 默认 90 天
    python3 scripts/make_demo.py --days 60 --seed 7

假数据里刻意放了一些规律，方便演示各个功能：
- 入睡越晚，睡眠分数和第二天准备度越低
- 周末睡得更晚、更久（社交时差）
- 下午喝咖啡、晚饭吃得晚的那晚睡得差，运动的那晚睡得好
- 最近 3 天模拟一次"快感冒"：体温升高、HRV 下降、静息心率升高（触发异常提醒）
"""
import argparse
import datetime as dt
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "demo"
TZ = "+08:00"

# 标签：(Oura 标签代码, 出现概率, 对睡眠分数的影响, 对 HRV 的影响)
TAGS = [
    ("tag_generic_caffeine", 0.30, -4, -4),
    ("tag_generic_late_meal", 0.20, -5, -5),
    ("tag_generic_workout", 0.30, +3, +3),
    ("tag_generic_alcohol", 0.06, -9, -10),
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def iso(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S") + TZ


def phases_for_night(rnd, slots: int, deep_bias: float) -> str:
    """生成 sleep_phase_5_min：1=深睡 2=浅睡 3=REM 4=清醒，每个字符 5 分钟。"""
    out = ["4"] * rnd.randint(2, 4)  # 入睡前的清醒
    cycle = 0
    while len(out) < slots:
        frac = len(out) / slots
        # 一个约 90 分钟的周期：前半夜深睡多，后半夜 REM 多
        deep = max(0, round((5 - 6 * frac) * deep_bias + rnd.gauss(0, 1)))
        rem = max(1, round(1 + 5 * frac + rnd.gauss(0, 1)))
        light = max(3, 18 - deep - rem + rnd.randint(-2, 2))
        seq = ["2"] * (light // 2) + ["1"] * deep + ["2"] * (light - light // 2) + ["3"] * rem
        if cycle > 0 and rnd.random() < 0.5:
            seq.insert(rnd.randrange(len(seq)), "4")
        out += seq
        cycle += 1
    out = out[:slots - 2] + ["4", "4"]  # 醒来
    return "".join(out)


def heart_rate_for_night(rnd, phases: str, rhr: float) -> list:
    items, n = [], len(phases)
    for i, p in enumerate(phases):
        frac = i / max(1, n - 1)
        # 前半夜逐渐下降，凌晨最低，醒前回升
        base = rhr + 9 * (1 - frac) ** 2 + 3 * max(0, frac - 0.8) / 0.2
        bump = {"1": -1.5, "2": 0, "3": 3, "4": 6}[p]
        v = base + bump + rnd.gauss(0, 1.2)
        items.append(None if rnd.random() < 0.03 else round(v))
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rnd = random.Random(args.seed)

    today = dt.date.today()
    daily_sleep, sleep, readiness, activity, stress, tags = [], [], [], [], [], []
    temp = 0.0

    for i in range(args.days, 0, -1):
        day = today - dt.timedelta(days=i - 1)      # 醒来的那天（Oura 的 day）
        night = day - dt.timedelta(days=1)          # 入睡的那晚
        free_night = night.weekday() in (4, 5)      # 周五、周六晚
        sick = i <= 3                                # 最近 3 天模拟快感冒

        # 当晚的标签（打在入睡那天）
        night_tags = [t for t in TAGS if rnd.random() < t[1]]
        for code, *_ in night_tags:
            hour = 20 if code == "tag_generic_late_meal" else (15 if code == "tag_generic_caffeine" else 18)
            start = dt.datetime.combine(night, dt.time(hour, rnd.randint(0, 59)))
            tags.append({"id": f"demo-{night}-{code}", "tag_type_code": code, "start_time": iso(start),
                         "end_time": None, "start_day": night.isoformat(), "end_day": None,
                         "comment": None, "custom_name": None})
        tag_sleep = sum(t[2] for t in night_tags)
        tag_hrv = sum(t[3] for t in night_tags)

        # 入睡时间：以 23:30 为中心，周五周六晚更晚
        bed_min = clamp(rnd.gauss(30 + (75 if free_night else 0), 45), -60, 220)  # 相对 23:00
        bed_dt = dt.datetime.combine(night, dt.time(23, 0)) + dt.timedelta(minutes=bed_min)
        late = clamp((bed_min - 30) / 120, -0.5, 1.6)

        in_bed_h = clamp(rnd.gauss(7.8 - 0.8 * late + (0.9 if free_night else 0), 0.6), 5, 10.5)
        slots = round(in_bed_h * 12)
        phases = phases_for_night(rnd, slots, clamp(1 - 0.25 * late + tag_sleep / 40, 0.4, 1.3))
        cnt = {k: phases.count(k) * 300 for k in "1234"}
        total = cnt["1"] + cnt["2"] + cnt["3"]
        end_dt = bed_dt + dt.timedelta(seconds=slots * 300)

        hrv = round(clamp(rnd.gauss(62 - 8 * late + tag_hrv - (14 if sick else 0), 6), 25, 95))
        rhr = clamp(rnd.gauss(54 + 3 * late + (5 if sick else 0), 1.8), 46, 70)
        sleep_score = round(clamp(rnd.gauss(80 - 9 * late + (total / 3600 - 7.2) * 4 + tag_sleep, 4), 40, 98))
        temp = 0.55 + rnd.gauss(0, 0.1) if sick else clamp(temp * 0.6 + rnd.gauss(0, 0.15), -0.6, 0.6)
        ready = round(clamp(rnd.gauss(78 - 8 * late + (hrv - 60) * 0.35 - abs(temp) * 8, 4), 30, 98))
        steps = round(clamp(rnd.gauss(7200 if day.weekday() >= 5 else 9800, 2600) * (0.6 if sick else 1), 1200, 22000))
        act_score = round(clamp(60 + steps / 400 + rnd.gauss(0, 5), 35, 100))
        hi_stress = round(clamp(rnd.gauss(90 + 40 * late, 35), 0, 300)) * 60
        recovery = round(clamp(rnd.gauss(110 - 30 * late, 35), 0, 300)) * 60

        d = day.isoformat()
        hr_items = heart_rate_for_night(rnd, phases, rhr)
        valid_hr = [v for v in hr_items if v is not None]
        daily_sleep.append({"day": d, "score": sleep_score})
        sleep.append({
            "day": d, "type": "long_sleep",
            "bedtime_start": iso(bed_dt), "bedtime_end": iso(end_dt),
            "total_sleep_duration": total, "deep_sleep_duration": cnt["1"],
            "light_sleep_duration": cnt["2"], "rem_sleep_duration": cnt["3"], "awake_time": cnt["4"],
            "time_in_bed": slots * 300, "efficiency": round(100 * total / (slots * 300)),
            "average_hrv": hrv, "average_heart_rate": round(sum(valid_hr) / len(valid_hr), 1),
            "lowest_heart_rate": min(valid_hr),
            "sleep_phase_5_min": phases,
            "heart_rate": {"interval": 300, "items": hr_items, "timestamp": iso(bed_dt)},
        })
        readiness.append({"day": d, "score": ready, "temperature_deviation": round(temp, 2)})
        activity.append({"day": d, "score": act_score, "steps": steps,
                         "active_calories": round(steps * 0.045 + rnd.gauss(0, 40))})
        stress.append({"day": d, "stress_high": hi_stress, "recovery_high": recovery})

    OUT.mkdir(parents=True, exist_ok=True)
    files = {"daily_sleep": daily_sleep, "sleep": sleep, "daily_readiness": readiness,
             "daily_activity": activity, "daily_stress": stress, "enhanced_tag": tags,
             "meta": {"source": "demo", "generated": dt.datetime.now().isoformat(timespec="seconds"),
                      "start": daily_sleep[0]["day"], "end": daily_sleep[-1]["day"]}}
    for name, data in files.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"已生成 {args.days} 天假数据 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
