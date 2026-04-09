import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import types

SERVICE_DIR = Path(__file__).resolve().parents[1]
APP_DIR = SERVICE_DIR / "app"
for path in (SERVICE_DIR, APP_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

if "loguru" not in sys.modules:
    class _DummyLogger:
        def remove(self):
            return None

        def add(self, *args, **kwargs):
            return None

        def bind(self, **kwargs):
            return self

        def info(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

        def exception(self, *args, **kwargs):
            return None

    sys.modules["loguru"] = types.SimpleNamespace(logger=_DummyLogger())

if "flow_processor" not in sys.modules:
    sys.modules["flow_processor"] = types.SimpleNamespace(
        FlowProcessor=type("FlowProcessor", (), {}),
        Flow=type("Flow", (), {}),
    )

if "traffic_tokenizer" not in sys.modules:
    sys.modules["traffic_tokenizer"] = types.SimpleNamespace(
        TrafficTokenizer=type("TrafficTokenizer", (), {})
    )

from app import main


class PipelineReportingTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        main.tasks.clear()

    async def test_attach_central_reporting_skips_when_result_missing(self):
        task = main.Task(task_id="task-empty")

        status = await main.attach_central_reporting(task)

        self.assertEqual(status, {"status": "skipped", "message": "task.result is empty"})

    async def test_zero_flow_pipeline_stores_central_reporting_status(self):
        task = main.Task(task_id="task-zero", pcap_path="/tmp/fake.pcap", pcap_size=128)
        main.tasks[task.task_id] = task

        reporter_mock = AsyncMock(return_value={"status": "stored", "report_id": "task-zero"})
        flow_processor = SimpleNamespace(process_pcap=lambda _: ([], {"total_packets": 4}))
        tokenizer = SimpleNamespace()

        with patch.object(main, "FlowProcessor", return_value=flow_processor), patch.object(
            main, "TrafficTokenizer", return_value=tokenizer
        ), patch.object(main.central_reporter, "report", reporter_mock):
            await main.run_detection_pipeline(task.task_id)

        self.assertEqual(task.status, main.TaskStage.COMPLETED)
        self.assertEqual(task.stage, main.TaskStage.COMPLETED)
        self.assertEqual(
            task.result["meta"]["central_reporting"],
            {"status": "stored", "report_id": "task-zero"},
        )
        baseline_without_reporting = {
            "meta": {
                key: value
                for key, value in task.result["meta"].items()
                if key != "central_reporting"
            },
            "statistics": dict(task.result["statistics"]),
            "threats": list(task.result["threats"]),
            "metrics": dict(task.result["metrics"]),
        }
        baseline_without_reporting["metrics"]["json_output_size_bytes"] = 0
        baseline_size = len(main.json.dumps(baseline_without_reporting).encode("utf-8"))
        self.assertGreater(task.result["metrics"]["json_output_size_bytes"], baseline_size)
        self.assertEqual(
            task.result["metrics"]["json_output_size_bytes"],
            len(main.json.dumps(task.result).encode("utf-8")),
        )

    async def test_failed_central_reporting_is_recorded_without_failing_pipeline(self):
        task = main.Task(task_id="task-normal", pcap_path="/tmp/fake.pcap", pcap_size=512)
        main.tasks[task.task_id] = task

        flow = SimpleNamespace(
            five_tuple=SimpleNamespace(
                to_dict=lambda: {
                    "src_ip": "10.0.0.5",
                    "dst_ip": "8.8.8.8",
                    "src_port": 50123,
                    "dst_port": 443,
                    "protocol": "TCP",
                }
            ),
            start_time=1712655000,
            end_time=1712655060,
            packet_count=5,
            total_bytes=2500,
        )
        flow_processor = SimpleNamespace(
            process_pcap=lambda _: ([flow], {"total_packets": 5}),
            extract_statistical_features=lambda _: {"feature": 1},
            flow_to_text=lambda _: "flow text",
        )
        tokenizer = SimpleNamespace(
            tokenize_flow=lambda **_: ("prompt", 12, False),
            parse_llm_response=lambda _: {
                "primary_label": "Botnet",
                "secondary_label": "C2 Beaconing",
            },
        )
        reporter_mock = AsyncMock(
            return_value={
                "status": "failed",
                "error_code": "CENTRAL_REPORT_UPLOAD_FAILED",
                "message": "central down",
            }
        )

        with patch.object(main, "FlowProcessor", return_value=flow_processor), patch.object(
            main, "TrafficTokenizer", return_value=tokenizer
        ), patch.object(main, "call_svm_service", AsyncMock(return_value={"prediction": 1, "confidence": 0.88})), patch.object(
            main, "call_llm_service", AsyncMock(return_value={"content": "Botnet"})
        ), patch.object(main.central_reporter, "report", reporter_mock):
            await main.run_detection_pipeline(task.task_id)

        self.assertEqual(task.status, main.TaskStage.COMPLETED)
        self.assertEqual(task.stage, main.TaskStage.COMPLETED)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.result["meta"]["central_reporting"]["status"], "failed")
        self.assertEqual(
            task.result["meta"]["central_reporting"]["error_code"],
            "CENTRAL_REPORT_UPLOAD_FAILED",
        )

    async def test_reporting_exception_is_recorded_without_failing_pipeline(self):
        task = main.Task(task_id="task-exception", pcap_path="/tmp/fake.pcap", pcap_size=512)
        main.tasks[task.task_id] = task

        flow = SimpleNamespace(
            five_tuple=SimpleNamespace(
                to_dict=lambda: {
                    "src_ip": "10.0.0.5",
                    "dst_ip": "8.8.8.8",
                    "src_port": 50123,
                    "dst_port": 443,
                    "protocol": "TCP",
                }
            ),
            start_time=1712655000,
            end_time=1712655060,
            packet_count=5,
            total_bytes=2500,
        )
        flow_processor = SimpleNamespace(
            process_pcap=lambda _: ([flow], {"total_packets": 5}),
            extract_statistical_features=lambda _: {"feature": 1},
            flow_to_text=lambda _: "flow text",
        )
        tokenizer = SimpleNamespace(
            tokenize_flow=lambda **_: ("prompt", 12, False),
            parse_llm_response=lambda _: {
                "primary_label": "Botnet",
                "secondary_label": "C2 Beaconing",
            },
        )

        with patch.object(main, "FlowProcessor", return_value=flow_processor), patch.object(
            main, "TrafficTokenizer", return_value=tokenizer
        ), patch.object(main, "call_svm_service", AsyncMock(return_value={"prediction": 1, "confidence": 0.88})), patch.object(
            main, "call_llm_service", AsyncMock(return_value={"content": "Botnet"})
        ), patch.object(main.central_reporter, "report", AsyncMock(side_effect=RuntimeError("boom"))):
            await main.run_detection_pipeline(task.task_id)

        self.assertEqual(task.status, main.TaskStage.COMPLETED)
        self.assertEqual(task.stage, main.TaskStage.COMPLETED)
        self.assertEqual(task.result["meta"]["central_reporting"]["status"], "failed")
        self.assertEqual(
            task.result["meta"]["central_reporting"]["error_code"],
            "CENTRAL_REPORT_UPLOAD_FAILED",
        )
        self.assertEqual(task.result["meta"]["central_reporting"]["message"], "boom")


if __name__ == "__main__":
    unittest.main()
