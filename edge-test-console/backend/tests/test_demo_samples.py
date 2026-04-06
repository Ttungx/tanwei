import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
import importlib

from fastapi import BackgroundTasks, HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

with patch("pathlib.Path.mkdir", return_value=None):
    main = importlib.import_module("app.main")


class DemoSamplesApiTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.demo_dir = Path(self.tmpdir.name) / "demo_show"
        self.upload_dir = Path(self.tmpdir.name) / "uploads"
        self.demo_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        main.tasks.clear()

    def tearDown(self):
        self.tmpdir.cleanup()
        main.tasks.clear()

    def test_get_demo_samples_lists_only_supported_files(self):
        async def run_test():
            pcap_file = self.demo_dir / "sample_attack.pcap"
            pcapng_file = self.demo_dir / "normal_traffic.pcapng"
            ignored_file = self.demo_dir / "README.txt"
            pcap_file.write_bytes(b"pcap-one")
            pcapng_file.write_bytes(b"pcap-two")
            ignored_file.write_text("ignore me", encoding="utf-8")

            with patch.object(main, "DEMO_SAMPLES_DIR", self.demo_dir):
                payload = await main.get_demo_samples()

            self.assertEqual(len(payload), 2)

            sample_by_filename = {item["filename"]: item for item in payload}
            self.assertEqual(
                set(sample_by_filename.keys()),
                {"sample_attack.pcap", "normal_traffic.pcapng"},
            )
            self.assertEqual(sample_by_filename["sample_attack.pcap"]["id"], "sample_attack.pcap")
            self.assertEqual(
                sample_by_filename["sample_attack.pcap"]["display_name"],
                "Sample Attack",
            )
            self.assertEqual(
                sample_by_filename["sample_attack.pcap"]["size_bytes"],
                len(b"pcap-one"),
            )

        import asyncio
        asyncio.run(run_test())

    def test_detect_demo_starts_task_for_existing_sample(self):
        async def run_test():
            sample_file = self.demo_dir / "demo_case.pcap"
            sample_file.write_bytes(b"demo payload")
            fake_called = {"value": False}

            async def fake_process_detection(task_id, file_path, original_size):
                fake_called["value"] = True
                self.assertEqual(file_path.name, f"{task_id}_demo_case.pcap")
                self.assertEqual(original_size, len(b"demo payload"))
                self.assertIn(task_id, main.tasks)

            with patch.object(main, "DEMO_SAMPLES_DIR", self.demo_dir), patch.object(
                main, "UPLOAD_DIR", self.upload_dir
            ), patch.object(main, "process_detection", fake_process_detection):
                background_tasks = BackgroundTasks()
                payload = await main.detect_demo_sample(
                    main.DemoDetectRequest(sample_id="demo_case.pcap"),
                    background_tasks,
                )

            self.assertEqual(payload.status, "success")
            self.assertTrue(payload.task_id)
            self.assertEqual(payload.message, "Detection task started")
            self.assertIn(payload.task_id, main.tasks)

            task = main.tasks[payload.task_id]
            self.assertEqual(task["status"], "pending")
            self.assertEqual(task["stage"], "pending")
            self.assertEqual(task["filename"], "demo_case.pcap")
            self.assertEqual(task["original_size"], len(b"demo payload"))
            self.assertEqual(len(background_tasks.tasks), 1)
            queued = background_tasks.tasks[0]
            self.assertIs(queued.func, fake_process_detection)
            self.assertEqual(queued.args[0], payload.task_id)
            self.assertEqual(queued.args[1], self.upload_dir / f"{payload.task_id}_demo_case.pcap")
            self.assertEqual(queued.args[2], len(b"demo payload"))
            await queued()
            self.assertTrue(fake_called["value"])

        import asyncio
        asyncio.run(run_test())

    def test_detect_demo_rejects_missing_sample(self):
        async def run_test():
            with patch.object(main, "DEMO_SAMPLES_DIR", self.demo_dir):
                with self.assertRaises(HTTPException) as exc:
                    await main.detect_demo_sample(
                        main.DemoDetectRequest(sample_id="not_found.pcap"),
                        BackgroundTasks(),
                    )
            self.assertEqual(exc.exception.status_code, 404)

        import asyncio
        asyncio.run(run_test())

    def test_detect_demo_rejects_unsupported_extension(self):
        async def run_test():
            bad_file = self.demo_dir / "bad.txt"
            bad_file.write_text("not pcap", encoding="utf-8")

            with patch.object(main, "DEMO_SAMPLES_DIR", self.demo_dir):
                with self.assertRaises(HTTPException) as exc:
                    await main.detect_demo_sample(
                        main.DemoDetectRequest(sample_id="bad.txt"),
                        BackgroundTasks(),
                    )
            self.assertEqual(exc.exception.status_code, 400)

        import asyncio
        asyncio.run(run_test())

    def test_detect_demo_rejects_path_traversal_sample_id(self):
        async def run_test():
            for invalid_sample_id in ("../sample.pcap", "/tmp/sample.pcap"):
                with patch.object(main, "DEMO_SAMPLES_DIR", self.demo_dir):
                    with self.assertRaises(HTTPException) as exc:
                        await main.detect_demo_sample(
                            main.DemoDetectRequest(sample_id=invalid_sample_id),
                            BackgroundTasks(),
                        )
                self.assertEqual(exc.exception.status_code, 400)

        import asyncio
        asyncio.run(run_test())

    def test_process_detection_marks_status_completed(self):
        async def run_test():
            task_id = "task-completed"
            file_path = self.upload_dir / "demo_case.pcap"
            file_path.write_bytes(b"payload")
            main.initialize_task(task_id, "demo_case.pcap", len(b"payload"))

            class FakeAioFile:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, tb):
                    return False

                async def read(self):
                    return b"payload"

            async def fake_sleep(*args, **kwargs):
                return None

            class FakeResponse:
                def __init__(self, payload):
                    self._payload = payload

                def raise_for_status(self):
                    return None

                def json(self):
                    return self._payload

            with patch.object(main.requests, "post", return_value=FakeResponse({"task_id": "agent-1"})), patch.object(
                main.requests,
                "get",
                side_effect=[
                    FakeResponse({"stage": "completed"}),
                    FakeResponse({"meta": {"task_id": task_id}}),
                ],
            ), patch.object(main.asyncio, "sleep", new=fake_sleep), patch.object(
                main.aiofiles, "open", return_value=FakeAioFile()
            ):
                await main.process_detection(task_id, file_path, len(b"payload"))

            self.assertEqual(main.tasks[task_id]["status"], "completed")

        import asyncio
        asyncio.run(run_test())

    def test_process_detection_marks_status_failed(self):
        async def run_test():
            task_id = "task-failed"
            file_path = self.upload_dir / "demo_case.pcap"
            file_path.write_bytes(b"payload")
            main.initialize_task(task_id, "demo_case.pcap", len(b"payload"))

            class FakeAioFile:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, tb):
                    return False

                async def read(self):
                    return b"payload"

            async def fake_sleep(*args, **kwargs):
                return None

            class FakeResponse:
                def __init__(self, payload):
                    self._payload = payload

                def raise_for_status(self):
                    return None

                def json(self):
                    return self._payload

            with patch.object(main.requests, "post", return_value=FakeResponse({"task_id": "agent-2"})), patch.object(
                main.requests,
                "get",
                return_value=FakeResponse({"stage": "failed", "error": "boom"}),
            ), patch.object(main.asyncio, "sleep", new=fake_sleep), patch.object(
                main.aiofiles, "open", return_value=FakeAioFile()
            ):
                await main.process_detection(task_id, file_path, len(b"payload"))

            self.assertEqual(main.tasks[task_id]["status"], "failed")
            self.assertEqual(main.tasks[task_id]["stage"], "failed")

        import asyncio
        asyncio.run(run_test())

    def test_process_detection_marks_status_failed_on_poll_timeout(self):
        async def run_test():
            task_id = "task-timeout"
            file_path = self.upload_dir / "demo_case.pcap"
            file_path.write_bytes(b"payload")
            main.initialize_task(task_id, "demo_case.pcap", len(b"payload"))

            class FakeAioFile:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, tb):
                    return False

                async def read(self):
                    return b"payload"

            async def fake_sleep(*args, **kwargs):
                return None

            class FakeResponse:
                def __init__(self, payload):
                    self._payload = payload

                def raise_for_status(self):
                    return None

                def json(self):
                    return self._payload

            with patch.object(main.requests, "post", return_value=FakeResponse({"task_id": "agent-timeout"})), patch.object(
                main.requests,
                "get",
                return_value=FakeResponse({"stage": "llm_inference", "progress": 75, "message": "still running"}),
            ), patch.object(main.asyncio, "sleep", new=fake_sleep), patch.object(
                main.aiofiles, "open", return_value=FakeAioFile()
            ):
                await main.process_detection(task_id, file_path, len(b"payload"))

            self.assertEqual(main.tasks[task_id]["status"], "failed")
            self.assertEqual(main.tasks[task_id]["stage"], "failed")
            self.assertIn("timeout", main.tasks[task_id]["error"].lower())
            self.assertIn("超时", main.tasks[task_id]["message"])

        import asyncio
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
