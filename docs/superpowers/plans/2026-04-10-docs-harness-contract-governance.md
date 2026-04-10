# Docs Harness Contract Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining first-phase gaps by syncing docs/harness status to current code reality and adding automated edge-to-central contract drift checks.

**Architecture:** First update repo truth documents so `active-plan`, tech debt, agent routing, and API docs all describe the current shipped system rather than the 2026-04-08 snapshot. Then add a cross-service contract-governance test that builds a real edge report payload and verifies it still validates against the current central-agent contract and forbidden-field rules.

**Tech Stack:** Markdown, Python unittest, Pydantic v2, existing edge-agent and central-agent test helpers

---

### Task 1: Sync Plan Status, Harness Docs, And API Truth

**Files:**
- Modify: `docs/exec-plans/active-plan.md`
- Modify: `docs/exec-plans/tech-debt.md`
- Modify: `.claude/agents/agents.md`
- Modify: `README.md`
- Modify: `docs/references/api_specs.md`

- [ ] **Step 1: Write the failing doc audit**

Run:

```bash
rg -n "WP-4 console 中心分析运营流|WP-5 文档与 harness 收口|TD-007|Last synced: 2026-04-08|central-agent \\| 进行中" \
  docs/exec-plans/active-plan.md \
  docs/exec-plans/tech-debt.md \
  .claude/agents/agents.md \
  README.md
```

Expected:
- finds `WP-5` still marked unfinished
- finds `TD-007` still in unresolved debt
- finds `.claude/agents/agents.md` still synced to `2026-04-08`
- finds `README.md` still says `central-agent | 进行中`

- [ ] **Step 2: Update the current-status source documents**

Apply these doc changes:

```md
# docs/exec-plans/active-plan.md
- [x] **WP-5 文档与 harness 收口**
  - `.claude/agents/` 已切换到 `console + edge-agent + central-agent` roster
  - `docs/design-docs/*` 与 `docs/references/*` 已成为当前事实来源
  - console 已补齐单 Edge 历史报告代理与 central reporting 展示
  - 剩余治理项转入技术债：schema 漂移自动检查、多 Edge 实际联动验证
```

```md
# docs/exec-plans/tech-debt.md
| TD-012 | edge-agent | 多 Edge 实际联动与批量校验路径仍缺少集成 | 中 | 设计多 Edge 汇聚上报与批量校验链路，完成端云一致性验证 |
| TD-010 | contract-governance | 端云契约尚无自动化 schema 漂移检查 | 中 | 在 CI 增加 schema 校验与 forbidden 字段检查 |

## 已解决债务
| TD-007 | console | 中央分析代理接口只有 latest 视图，历史报告检索能力不足 | 2026-04-10 | console 已实现 `/api/edges/{edge_id}/reports` 代理与归档历史切换 UI |
```

```md
# .claude/agents/agents.md
> Last synced: 2026-04-10

- 当前项目变更基线补充：
  - `edge-agent` 检测完成后自动写入 `meta.central_reporting`
  - `console` 已支持单 Edge 历史报告浏览和中心上报状态展示
- 当前里程碑责任映射改为：
  - 第一阶段服务实现已完成
  - 当前剩余主责任：`doc-gardener` 负责 docs/harness/plan 生命周期治理
  - 契约自动校验主责任：`central-agent-engineer` + `edge-agent-engineer`，验收由 `evaluator-agent`
```

```md
# README.md
| `central-agent` | 完成 | 归档、单 Edge 分析、全网分析与 SQLite 持久化已可用 |
```

```md
# docs/references/api_specs.md
### GET `/api/edges/{edge_id}/reports`

返回单个 edge 的历史归档报告列表，字段形状与 `/api/edges/{edge_id}/reports/latest` 相同，但为数组。
前端用途：归档页历史切换。
```

- [ ] **Step 3: Re-run the doc audit**

Run:

```bash
rg -n "TD-007|Last synced: 2026-04-08|central-agent \\| 进行中" \
  docs/exec-plans/tech-debt.md \
  .claude/agents/agents.md \
  README.md
```

Expected: no matches

Run:

```bash
rg -n "GET `/api/edges/\\{edge_id\\}/reports`|WP-5" \
  docs/references/api_specs.md \
  docs/exec-plans/active-plan.md
```

Expected:
- `api_specs.md` contains the history endpoint
- `active-plan.md` shows `WP-5` as completed

- [ ] **Step 4: Commit the doc/harness sync**

```bash
git add docs/exec-plans/active-plan.md docs/exec-plans/tech-debt.md .claude/agents/agents.md README.md docs/references/api_specs.md
git commit -m "docs: sync first-phase status and harness truth"
```

### Task 2: Add Cross-Service Contract Drift Coverage

**Files:**
- Create: `central-agent/tests/test_contract_governance.py`
- Modify: `central-agent/tests/test_central_agent_api.py`
- Modify: `edge-agent/tests/test_report_mapper.py`

- [ ] **Step 1: Write the failing governance test**

Create `central-agent/tests/test_contract_governance.py`:

```python
import sys
import unittest
from pathlib import Path

CENTRAL_DIR = Path(__file__).resolve().parents[1]
EDGE_DIR = CENTRAL_DIR.parents[0] / "edge-agent"

if str(CENTRAL_DIR) not in sys.path:
    sys.path.insert(0, str(CENTRAL_DIR))
if str(EDGE_DIR) not in sys.path:
    sys.path.insert(0, str(EDGE_DIR))

from app.models import EdgeReportIn
from app.security import DENIED_INTEL_FIELDS
from app.report_mapper import build_edge_report_payload


class ContractGovernanceTests(unittest.TestCase):
    def test_edge_report_mapper_output_validates_against_central_contract(self):
        edge_result = {
            "meta": {
                "task_id": "task-contract-001",
                "timestamp": "2026-04-10T10:00:00+00:00",
                "agent_version": "edge-agent-v1",
                "processing_time_ms": 980,
            },
            "statistics": {
                "total_packets": 64,
                "total_flows": 6,
                "normal_flows_dropped": 5,
                "anomaly_flows_detected": 1,
                "svm_filter_rate": "83.3%",
                "bandwidth_reduction": "78.5%",
            },
            "threats": [
                {
                    "id": "threat-contract-001",
                    "five_tuple": {
                        "src_ip": "10.0.0.5",
                        "dst_ip": "8.8.8.8",
                        "src_port": 50123,
                        "dst_port": 443,
                        "protocol": "TCP",
                    },
                    "classification": {
                        "primary_label": "Botnet",
                        "secondary_label": "Beaconing",
                        "confidence": 0.93,
                        "model": "Qwen3.5-0.8B",
                    },
                    "flow_metadata": {
                        "packet_count": 8,
                        "byte_count": 4120,
                    },
                    "token_info": {
                        "token_count": 128,
                        "truncated": True,
                    },
                }
            ],
            "metrics": {
                "original_pcap_size_bytes": 4096,
                "json_output_size_bytes": 880,
                "bandwidth_saved_percent": 78.5,
            },
        }

        payload = build_edge_report_payload(
            result=edge_result,
            edge_id="edge1",
            max_time_window=60,
            max_packet_count=10,
            max_token_length=690,
        )

        model = EdgeReportIn(**payload)
        self.assertEqual(model.edge_id, "edge1")
        self.assertEqual(model.report_id, "task-contract-001")

    def test_forbidden_field_set_still_blocks_payload_like_keys(self):
        self.assertIn("payloadhex", DENIED_INTEL_FIELDS)
        self.assertIn("rawpcap", DENIED_INTEL_FIELDS)
        self.assertIn("packethex", DENIED_INTEL_FIELDS)
```

- [ ] **Step 2: Run the governance test to verify failure**

Run:

```bash
/root/anxun/.venv/bin/python -m unittest central-agent.tests.test_contract_governance -q
```

Expected: FAIL because the cross-service import path or mapper payload shape is not yet wired for this test module.

- [ ] **Step 3: Implement the minimal governance support**

Apply these exact changes:

```python
# central-agent/tests/test_contract_governance.py
from importlib.util import module_from_spec, spec_from_file_location

EDGE_REPORT_MAPPER = EDGE_DIR / "app" / "report_mapper.py"
spec = spec_from_file_location("edge_report_mapper", EDGE_REPORT_MAPPER)
module = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
build_edge_report_payload = module.build_edge_report_payload
```

```python
# edge-agent/tests/test_report_mapper.py
class ReportMapperTests(unittest.TestCase):
    ...
    def test_build_edge_report_payload_matches_current_central_contract(self):
        ...
        self.assertEqual(payload["intel"]["schema_version"], "edge-intel/v1")
```

```python
# central-agent/tests/test_central_agent_api.py
def test_create_report_rejects_raw_payload_like_fields(self):
    payload = build_report_payload("edge1", "report-raw")
    payload["intel"]["context"]["payload_hex"] = "deadbeef"

    with self.assertRaises(ValueError):
        self.main.EdgeReportIn(**payload)
```

The intent is:
- import the real mapper without package-name collisions
- validate the actual shipped mapper output against `EdgeReportIn`
- keep forbidden-field behavior under central-agent ownership

- [ ] **Step 4: Run the governance and existing contract tests**

Run:

```bash
/root/anxun/.venv/bin/python -m unittest central-agent.tests.test_contract_governance -q
/root/anxun/.venv/bin/python -m unittest central-agent.tests.test_central_agent_api -q
/root/anxun/.venv/bin/python -m unittest edge-agent.tests.test_report_mapper -q
```

Expected: all pass with `OK`

- [ ] **Step 5: Commit the governance coverage**

```bash
git add central-agent/tests/test_contract_governance.py central-agent/tests/test_central_agent_api.py edge-agent/tests/test_report_mapper.py
git commit -m "test: add edge to central contract governance coverage"
```

### Task 3: Final Verification And Backlog Boundary

**Files:**
- Modify: `docs/exec-plans/active-plan.md`
- Modify: `docs/exec-plans/tech-debt.md`

- [ ] **Step 1: Run the final verification bundle**

Run:

```bash
/root/anxun/.venv/bin/python -m unittest discover central-agent/tests -q
/root/anxun/.venv/bin/python -m unittest edge-agent.tests.test_report_mapper -q
/root/anxun/.venv/bin/python -m unittest discover console/backend/tests -q
npm --prefix console/frontend test
```

Expected: all pass

- [ ] **Step 2: Confirm what remains out of scope**

Keep only this unresolved backlog in `docs/exec-plans/tech-debt.md`:

```md
| TD-012 | edge-agent | 多 Edge 实际联动与批量校验路径仍缺少集成 | 中 | 设计多 Edge 汇聚上报与批量校验链路，完成端云一致性验证 |
```

That boundary matters because multi-edge integration is a new feature plan, not part of first-phase cleanup.
