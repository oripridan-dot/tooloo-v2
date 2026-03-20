# tests/test_monitor.py
import asyncio
import unittest
from datetime import datetime, timedelta
import yaml
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

# --- Start: Re-definitions for isolation ---
CONFIG_FILE = "config.yaml"

class SystemHealth:
    def __init__(self, name: str, url: str, api_key: Optional[str] = None):
        self.name = name
        self.url = url
        self.api_key = api_key
        self.last_check: Optional[datetime] = None
        self.status: str = "UNKNOWN"
        self.response_time: Optional[float] = None
        self.error_message: Optional[str] = None
        self.checks_since_last_failure: int = 0
        self.consecutive_failures: int = 0

    async def check_health(self) -> bool:
        self.last_check = datetime.now()
        await asyncio.sleep(0.01)
        self.status = "OK"
        self.response_time = 0.05
        self.consecutive_failures = 0
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "status": self.status,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "response_time": self.response_time,
            "error_message": self.error_message,
            "consecutive_failures": self.consecutive_failures,
        }

class SystemMonitor:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.systems: Dict[str, SystemHealth] = {}
        self.load_config()
        self.alerting_cooldown: Dict[str, datetime] = {}
        self.semaphore = asyncio.Semaphore(5)

    def load_config(self) -> None:
        test_config_path = "test_monitor_config.yaml"
        if os.path.exists(test_config_path):
            try:
                with open(test_config_path, "r") as f:
                    config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                logging.error(f"Error loading test config file: {e}")
                config = {
                    "target_systems": [
                        {"name": "test_sys_a", "url": "http://localhost:9001"},
                        {"name": "test_sys_b", "url": "http://localhost:9002"},
                    ],
                    "monitoring_interval": 10,
                    "alerting_threshold": 2,
                    "max_concurrent_requests": 2,
                }
        else:
            config = {
                "target_systems": [
                    {"name": "test_sys_a", "url": "http://localhost:9001"},
                    {"name": "test_sys_b", "url": "http://localhost:9002"},
                ],
                "monitoring_interval": 10,
                "alerting_threshold": 2,
                "max_concurrent_requests": 2,
            }

        self.target_systems = config.get("target_systems", [])
        self.monitoring_interval = config.get("monitoring_interval", 10)
        self.alerting_threshold = config.get("alerting_threshold", 2)
        self.max_concurrent_requests = config.get("max_concurrent_requests", 2)
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        for sys_config in self.target_systems:
            name = sys_config.get("name")
            url = sys_config.get("url")
            api_key = sys_config.get("api_key")
            if name and url:
                self.systems[name] = SystemHealth(name, url, api_key)

    async def _perform_health_check(self, system_name: str) -> None:
        system = self.systems.get(system_name)
        if not system: return

        async with self.semaphore:
            is_healthy = await system.check_health()

        if not is_healthy:
            if system.consecutive_failures >= self.alerting_threshold:
                if (
                    system_name not in self.alerting_cooldown
                    or datetime.now() > self.alerting_cooldown[system_name]
                ):
                    self.trigger_alert(system)
                    self.alerting_cooldown[system_name] = datetime.now() + timedelta(minutes=5)
        else:
            if system_name in self.alerting_cooldown:
                del self.alerting_cooldown[system_name]

    def trigger_alert(self, system: SystemHealth) -> None:
        logging.critical(f"ALERT: System '{system.name}' is critical!")

    async def run_monitoring_cycle(self) -> None:
        tasks = [self._perform_health_check(name) for name in self.systems.keys()]
        await asyncio.gather(*tasks)

    def get_all_system_statuses(self) -> List[Dict[str, Any]]:
        return [system.get_status() for system in self.systems.values()]

class TestSystemMonitorIsolated(unittest.TestCase):
    def setUp(self) -> None:
        self.test_config_path = "test_monitor_config.yaml"
        test_config_content = {
            "target_systems": [
                {"name": "test_sys_1", "url": "http://localhost:9001"},
                {"name": "test_sys_2", "url": "http://localhost:9002"},
            ],
            "monitoring_interval": 5,
            "alerting_threshold": 2,
            "max_concurrent_requests": 2,
        }
        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config_content, f)
        self.monitor = SystemMonitor(config_path=self.test_config_path)
        self.monitor.load_config()
        for sys in self.monitor.systems.values():
            sys.checks_since_last_failure = 0
            sys.consecutive_failures = 0
            sys.status = "UNKNOWN"
            sys.error_message = None
            sys.last_check = None
            sys.response_time = None

    def tearDown(self) -> None:
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def test_system_health_check_success(self) -> None:
        async def run_test_scenario():
            system_to_test = self.monitor.systems.get("test_sys_1")
            if not system_to_test: self.fail("System 'test_sys_1' not found.")
            await self.monitor._perform_health_check("test_sys_1")
            self.assertEqual(system_to_test.status, "OK")
            self.assertEqual(system_to_test.consecutive_failures, 0)
            self.assertIsNotNone(system_to_test.last_check)
            self.assertGreater(system_to_test.response_time, 0)
        asyncio.run(run_test_scenario())

    def test_system_health_check_failure_triggers_alert_threshold(self) -> None:
        system_name = "test_sys_1"
        async def mock_failing_health_check(self):
            self.last_check = datetime.now()
            await asyncio.sleep(0.01)
            self.status = "CRITICAL"
            self.error_message = "Simulated network error"
            self.consecutive_failures += 1
            return False
        self.monitor.systems[system_name].check_health = mock_failing_health_check.__get__(self.monitor.systems[system_name])

        async def run_test_scenario():
            system_to_test = self.monitor.systems.get(system_name)
            if not system_to_test: self.fail(f"System '{system_name}' not found.")
            await self.monitor._perform_health_check(system_name)
            self.assertEqual(system_to_test.status, "CRITICAL")
            self.assertEqual(system_to_test.consecutive_failures, 1)
            await self.monitor._perform_health_check(system_name)
            self.assertEqual(system_to_test.status, "CRITICAL")
            self.assertEqual(system_to_test.consecutive_failures, 2)
        asyncio.run(run_test_scenario())

    def test_system_recovers_and_resets_cooldown(self) -> None:
        system_name = "test_sys_1"
        failures = 0
        async def mock_intermittent_health_check(self):
            nonlocal failures
            self.last_check = datetime.now()
            await asyncio.sleep(0.01)
            if failures < 2:
                self.status = "CRITICAL"
                self.error_message = "Simulated intermittent error"
                self.consecutive_failures += 1
                failures += 1
                return False
            else:
                self.status = "OK"
                self.error_message = None
                self.consecutive_failures = 0
                return True
        self.monitor.systems[system_name].check_health = mock_intermittent_health_check.__get__(self.monitor.systems[system_name])

        async def run_test_scenario():
            system_to_test = self.monitor.systems.get(system_name)
            if not system_to_test: self.fail(f"System '{system_name}' not found.")
            await self.monitor._perform_health_check(system_name)
            self.assertEqual(system_to_test.consecutive_failures, 1)
            await self.monitor._perform_health_check(system_name)
            self.assertEqual(system_to_test.consecutive_failures, 2)
            self.assertIn(system_name, self.monitor.alerting_cooldown)
            await self.monitor._perform_health_check(system_name)
            self.assertEqual(system_to_test.status, "OK")
            self.assertEqual(system_to_test.consecutive_failures, 0)
            self.assertNotIn(system_name, self.monitor.alerting_cooldown)
        asyncio.run(run_test_scenario())

    def test_get_all_system_statuses(self) -> None:
        statuses = self.monitor.get_all_system_statuses()
        self.assertEqual(len(statuses), 2)
        names = [s["name"] for s in statuses]
        self.assertIn("test_sys_1", names)
        self.assertIn("test_sys_2", names)
        for status in statuses:
            self.assertEqual(status["status"], "UNKNOWN")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
