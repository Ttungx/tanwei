import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


CENTRAL_DIR = Path(__file__).resolve().parents[1]
EDGE_DIR = CENTRAL_DIR.parents[0] / "edge-agent"
CENTRAL_APP_DIR = CENTRAL_DIR / "app"


def load_package_module(package_name: str, package_dir: Path, module_name: str):
    if package_name not in sys.modules:
        package_spec = spec_from_file_location(
            package_name,
            package_dir / "__init__.py",
            submodule_search_locations=[str(package_dir)],
        )
        assert package_spec and package_spec.loader
        package = module_from_spec(package_spec)
        sys.modules[package_name] = package
        package_spec.loader.exec_module(package)

    full_name = f"{package_name}.{module_name}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    module_spec = spec_from_file_location(full_name, package_dir / f"{module_name}.py")
    assert module_spec and module_spec.loader
    module = module_from_spec(module_spec)
    sys.modules[full_name] = module
    module_spec.loader.exec_module(module)
    return module


EDGE_REPORT_MAPPER = EDGE_DIR / "app" / "report_mapper.py"
SPEC = spec_from_file_location("edge_report_mapper", EDGE_REPORT_MAPPER)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_edge_report_payload = MODULE.build_edge_report_payload

central_models = load_package_module("central_contract_app", CENTRAL_APP_DIR, "models")
central_security = load_package_module("central_contract_app", CENTRAL_APP_DIR, "security")
EdgeReportIn = central_models.EdgeReportIn
DENIED_INTEL_FIELDS = central_security.DENIED_INTEL_FIELDS


def build_edge_result() -> dict:
    return {
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


def build_payload() -> dict:
    return build_edge_report_payload(
        result=build_edge_result(),
        edge_id="edge1",
        max_time_window=60,
        max_packet_count=10,
        max_token_length=690,
    )


class ContractGovernanceTests(unittest.TestCase):
    def test_edge_report_mapper_output_preserves_expected_contract_shape(self):
        payload = build_payload()

        self.assertEqual(payload["edge_id"], "edge1")
        self.assertEqual(payload["report_id"], "task-contract-001")
        self.assertEqual(payload["source"], "edge-agent")
        self.assertEqual(payload["reported_at"], "2026-04-10T10:00:00+00:00")
        self.assertEqual(payload["intel"]["schema_version"], "edge-intel/v1")
        self.assertEqual(payload["intel"]["summary"]["threat_count"], 1)
        self.assertEqual(payload["intel"]["summary"]["risk_level"], "medium")
        self.assertEqual(payload["intel"]["statistics"]["total_packets"], 64)
        self.assertEqual(payload["intel"]["metrics"]["bandwidth_saved_percent"], 78.5)
        self.assertEqual(payload["intel"]["threats"][0]["threat_id"], "threat-contract-001")
        self.assertEqual(payload["intel"]["threats"][0]["title"], "Botnet")
        self.assertEqual(payload["intel"]["threats"][0]["category"], "Beaconing")
        self.assertEqual(
            payload["intel"]["threats"][0]["evidence"]["flow_metadata"]["packet_count"],
            8,
        )
        self.assertEqual(
            payload["intel"]["context"]["analysis_constraints"],
            {
                "max_time_window_s": 60,
                "max_packet_count": 10,
                "max_token_length": 690,
            },
        )

    def test_edge_report_mapper_output_validates_against_central_contract(self):
        model = EdgeReportIn(**build_payload())
        self.assertEqual(model.edge_id, "edge1")
        self.assertEqual(model.report_id, "task-contract-001")
        self.assertEqual(model.intel.schema_version, "edge-intel/v1")
        record = model.to_record()
        self.assertEqual(record["edge_id"], "edge1")
        self.assertEqual(record["report_id"], "task-contract-001")
        self.assertEqual(record["report"]["summary"]["threat_count"], 1)
        self.assertEqual(
            record["report"]["context"]["analysis_constraints"]["max_packet_count"],
            10,
        )

    def test_forbidden_payload_like_fields_are_rejected_by_central_contract(self):
        payload = build_payload()
        payload["intel"]["context"]["payload_hex"] = "deadbeef"

        with self.assertRaises(ValueError):
            EdgeReportIn(**payload)

        self.assertIn("payloadhex", DENIED_INTEL_FIELDS)
        self.assertIn("rawpcap", DENIED_INTEL_FIELDS)
        self.assertIn("packethex", DENIED_INTEL_FIELDS)
