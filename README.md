# Oura 数据面板

一个读取 Oura 戒指数据并可视化的静态网页。

**功能**

- **异常提醒**：体温连续偏高、HRV 明显下降、静息心率明显升高时在顶部提示
- **三项分数**：睡眠、准备度、活动分数趋势
- **个人基线**：准备度、HRV、静息心率叠加前 30 天均值 ±1 标准差的阴影带，标出超出正常范围的日子
- **作息规律性**：每晚入睡到醒来的时间条，入睡/起床时间波动和社交时差
- **睡眠阶段**、**入睡时间 vs 准备度**（带回归趋势线）
- **星期对比**：按星期几分组的睡眠时长、入睡时间、准备度
- **标签分析**：咖啡、运动、晚餐较晚等标签对当晚睡眠的影响
- **步数**、**压力与恢复**
- **睡眠日历**：类似 GitHub 贡献图的睡眠分数热力图
- **单日详情**：当晚的睡眠阶段时间轴和心率曲线，点击任意图表、日历格子或表格行即可切换

演示数据里刻意放了一些规律（晚睡影响准备度、周末晚睡、咖啡影响睡眠、最近几天模拟快要感冒），方便看到每个功能的效果。

- **线上演示**（GitHub Pages）只显示随机生成的假数据
- **真实数据**只保存在本地，被 `.gitignore` 排除，永远不会提交

零依赖：Python 标准库 + 原生 JavaScript/SVG，没有 npm 包或图表库。

## 目录结构

```
scripts/
  fetch_oura.py   从 Oura API v2 拉取真实数据 → docs/data/real/（不提交）
  make_demo.py    生成假数据 → docs/data/demo/（提交）
docs/
  index.html      网页本体
  data/demo/      假数据
  data/real/      真实数据（被 .gitignore 排除）
```

## 本地使用（看真实数据）

1. 在 [Oura 开发者平台](https://developer.ouraring.com) 获取访问令牌
2. 复制 `.env.example` 为 `.env`，填入 `OURA_TOKEN=你的令牌`
3. 拉取数据并启动本地服务器：

```bash
python3 scripts/fetch_oura.py          # 默认最近 90 天，可加 --days 30
python3 -m http.server 8000 -d docs
```

4. 打开 <http://localhost:8000>

本地打开时页面会优先读取真实数据，右上角可以切换"演示 / 真实"。以后想更新数据，重新运行 `fetch_oura.py` 再刷新页面即可。

> 不能直接双击 `index.html` 打开，浏览器不允许 `file://` 页面读取 JSON，必须通过本地服务器。

## 部署演示版到 GitHub Pages

1. 把仓库推到 GitHub（`.env` 和 `docs/data/real/` 已被忽略）
2. 仓库 Settings → Pages → Source 选 `Deploy from a branch`，分支 `main`，目录 `/docs`
3. 线上页面只会显示演示数据，并隐藏"真实"切换按钮

想换一批假数据：`python3 scripts/make_demo.py --seed 7`

## 提交前检查

```bash
git status --ignored     # 确认 .env 和 docs/data/real/ 出现在 Ignored 里
```

如果不小心提交过真实数据或令牌，仅删除文件不够，旧提交里仍然有。需要重写历史，并立刻在 Oura 那边作废这个令牌。
