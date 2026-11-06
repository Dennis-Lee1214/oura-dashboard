#!/usr/bin/env python3
"""从 Oura API v2 拉取真实数据，保存到 docs/data/real/（已被 .gitignore 排除，不会提交）。

用法:
    export OURA_TOKEN=你的令牌        # 或写进项目根目录的 .env 文件
    python3 scripts/fetch_oura.py            # 默认最近 90 天
    python3 scripts/fetch_oura.py --days 30

只用 Python 标准库，不需要 pip install。
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "real"
API = "https://api.ouraring.com/v2/usercollection/"

# 网页用到的数据类型
TYPES = ["daily_sleep", "sleep", "daily_readiness", "daily_activity", "daily_stress", "enhanced_tag"]


def load_token() -> str:
    token = os.environ.get("OURA_TOKEN", "").strip()
    env_file = ROOT / ".env"
    if not token and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("OURA_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        sys.exit("没有找到 OURA_TOKEN。请设置环境变量，或在项目根目录创建 .env（参考 .env.example）。")
    return token


def fetch(data_type: str, start: str, end: str, token: str) -> list:
    items, next_token = [], None
    while True:
        params = {"start_date": start, "end_date": end}
        if next_token:
            params["next_token"] = next_token
        url = API + data_type + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                sys.exit("令牌无效或已过期（401）。请重新获取令牌。")
            print(f"  ! {data_type} 请求失败：HTTP {e.code}，已跳过", file=sys.stderr)
            return items
        items.extend(body.get("data", []))
        next_token = body.get("next_token")
        if not next_token:
            return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()

    token = load_token()
    today = dt.date.today()
    start = (today - dt.timedelta(days=args.days)).isoformat()
    end = (today + dt.timedelta(days=1)).isoformat()  # end_date 不含当天，往后推一天
    OUT.mkdir(parents=True, exist_ok=True)

    for t in TYPES:
        data = fetch(t, start, end, token)
        (OUT / f"{t}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"  {t}: {len(data)} 条")

    meta = {"source": "real", "generated": dt.datetime.now().isoformat(timespec="seconds"),
            "start": start, "end": today.isoformat()}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"已保存到 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
