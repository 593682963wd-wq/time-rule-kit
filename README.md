# 时间窗口、证据边界与规则监控

作者：Wangyuan · 2026-10-29

本项目源码采用 MIT 许可证，见 LICENSE；第三方依赖仍适用各自上游许可。

## 可用能力

- 显式样本层次、月份/小时窗口和半衰期的加权分位区间；未来样本排除，样本不足保持missing。
- 计数已知/未知区间三态判断、tri_or、已证明与仍可能最高级；任意精度整数比较。
- 节点覆盖、过期、未来观测、待办/逾期/完成与偏差聚合；显式阈值的单调升级、每级去重，仅本地草稿。
- 资产时间链、窗口交集、相邻间隔/重叠及输入延误传播；窗口前证据仍参与传播。
- 组合身份计划版本差异、显式地点/半开时间窗关联影响事件；不内置行业标准。

## 运行

Python 3.11+。依赖仅为标准库，或 requirements.txt 明确列出的开源解析库。程序默认不联网；安装依赖时由包管理器下载。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -B cli.py demo
python3 -B cli.py demo --output demo-output
python3 -B cli.py run example.json --output demo-output
python3 -B -m unittest discover -s tests -v
```

演示数据从零生成；默认临时目录会在命令结束时释放。需要保留文件或数据库时必须指定 --output，输入与输出目录应由使用者自行控制。JSON输出到标准输出，参数错误返回非零状态。

## 输入与输出

动作：`distribution`、`truth`、`tiers`、`milestones`、`escalate`、`chains`、`compare`、`affected`。每个动作参数名称对应核心文件中的同名函数/方法签名，公共接口有类型标注及中文说明。通用调用格式是 action 与 args；目录、收集模块另接受 tools/events/contract 等顶层显式合同。

```json
{
  "action": "truth",
  "args": {
    "known": 2,
    "unknown": 2,
    "denominator": 10,
    "percent": 30
  }
}
```

调用方须保存升级级别和seen_levels并随下次调用提供；CLI没有后台定时器。三态unknown不得当false；proven与possible不一致须人工复核。链传播是输入时长与间隔的算术估计，不宣称业务预测准确率。空概率/层次按调用方合同处理。

## 保留边界

实时数据源、航空报文完整解释器、公司情景与阈值、预警发送、行业决策、原可视化页面及模型精度承诺均未包含。

只保留通用流程与算法；这是经过提取/重构的独立工具或组件集合，并不声称完整迁移原应用、原业务质量或生产验收。源码来源、哈希与原入口映射保存在本地私有审计台账，不随此目录分发。

## 验证

tests/仅使用合成数据与临时文件，覆盖主流程、空/缺失、身份冲突和关键异常；cli.py demo可独立复现完整示例。未运行真实业务数据、联网/正式发送、原系统回归或生产部署。本项目为CLI/库，不包含Web UI。

## 2026-11-08 候选修订

- 以最新所选样本归一化衰减年龄，整体陈旧不因共同下溢误报缺失。
- 实际完成偏差独立检查actual不晚于当前/观测时刻。
- 规范JSON比较保留布尔/数值类型差异。

使用包内合成样例复跑；发布集合根目录的 `verify_release.py --project workflow-rule-monitor` 会依次执行测试和首次使用命令。原有版本的测试计数属于当时记录，本轮汇总以集合验证报告为准。
