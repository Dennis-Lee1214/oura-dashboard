#!/usr/bin/env python3
"""生成假数据到 docs/data/demo/，格式和 Oura API v2 返回的一致。

演示版网页用这些数据，可以放心提交到公开仓库。
    python3 scripts/make_demo.py            # 默认 90 天
    python3 scripts/make_demo.py --days 60 --seed 7
"""
import argparse
import datetime as dt
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "demo"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rnd = random.Random(args.seed)

    today = dt.date.today()
    daily_sleep, sleep, readiness, activity, stress = [], [], [], [], []
    temp = 0.0

    for i in range(args.days, 0, -1):
        day = today - dt.timedelta(days=i - 1)
        weekend = day.weekday() >= 5
        # 入睡时间：以 23:30 为中心，周末更晚
        bed_min = rnd.gauss(30 + (50 if weekend else 0), 55)  # 相对 23:00 的分钟数
        bed_min = clamp(bed_min, -60, 200)
        bed_dt = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(23, 0)) + dt.timedelta(minutes=bed_min)
        late = clamp((bed_min - 30) / 120, -0.5, 1.4)  # 越晚越大

        total = clamp(rnd.gauss(7.3 - 0.9 * late + (0.6 if weekend else 0), 0.6), 4.5, 9.5) * 3600
        deep = total * clamp(rnd.gauss(0.18 - 0.03 * late, 0.03), 0.08, 0.28)
        rem = total * clamp(rnd.gauss(0.22, 0.03), 0.12, 0.30)
        light = total - deep - rem
        awake = clamp(rnd.gauss(35, 12), 8, 80) * 60
        end_dt = bed_dt + dt.timedelta(seconds=total + awake)

        hrv = round(clamp(rnd.gauss(62 - 8 * late, 7), 30, 95))
        rhr = round(clamp(rnd.gauss(54 + 3 * late, 2.2), 46, 66))
        sleep_score = round(clamp(rnd.gauss(80 - 9 * late + (total / 3600 - 7.3) * 4, 4), 45, 98))
        temp = clamp(temp * 0.6 + rnd.gauss(0, 0.18), -0.9, 0.9)
        ready = round(clamp(rnd.gauss(78 - 8 * late + (hrv - 60) * 0.3 - abs(temp) * 6, 4), 40, 98))
        steps = round(clamp(rnd.gauss(7200 if weekend else 9800, 2600), 1200, 22000))
        act_score = round(clamp(60 + steps / 400 + rnd.gauss(0, 5), 35, 100))
        hi_stress = round(clamp(rnd.gauss(90 + 40 * late, 35), 0, 300)) * 60
        recovery = round(clamp(rnd.gauss(110 - 30 * late, 35), 0, 300)) * 60

        d = day.isoformat()
        tz = "+08:00"
        daily_sleep.append({"day": d, "score": sleep_score})
        sleep.append({
            "day": d, "type": "long_sleep",
            "bedtime_start": bed_dt.strftime("%Y-%m-%dT%H:%M:%S") + tz,
            "bedtime_end": end_dt.strftime("%Y-%m-%dT%H:%M:%S") + tz,
            "total_sleep_duration": round(total), "deep_sleep_duration": round(deep),
            "rem_sleep_duration": round(rem), "light_sleep_duration": round(light),
            "awake_time": round(awake), "average_hrv": hrv,
            "average_heart_rate": rhr + 4, "lowest_heart_rate": rhr,
        })
        readiness.append({"day": d, "score": ready, "temperature_deviation": round(temp, 2)})
        activity.append({"day": d, "score": act_score, "steps": steps,
                         "active_calories": round(steps * 0.045 + rnd.gauss(0, 40))})
        stress.append({"day": d, "stress_high": hi_stress, "recovery_high": recovery})

    OUT.mkdir(parents=True, exist_ok=True)
    files = {"daily_sleep": daily_sleep, "sleep": sleep, "daily_readiness": readiness,
             "daily_activity": activity, "daily_stress": stress,
             "meta": {"source": "demo", "generated": dt.datetime.now().isoformat(timespec="seconds"),
                      "start": daily_sleep[0]["day"], "end": daily_sleep[-1]["day"]}}
    for name, data in files.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"已生成 {args.days} 天假数据 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
