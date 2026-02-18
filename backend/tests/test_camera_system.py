"""
Test script for the enhanced camera monitoring system
Tests all new features: status, open, test endpoints
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp


async def test_camera_api():
    """Test camera monitoring API endpoints"""
    base_url = "http://localhost:8000"

    print("=" * 60)
    print("TESTING CAMERA MONITORING SYSTEM")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # Test 1: Camera Status
        print("\n[TEST 1] Getting camera status...")
        async with session.get(f"{base_url}/api/camera/status") as resp:
            data = await resp.json()
            print(f"Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
            if data.get("success"):
                status = data.get("status", {})
                camera = status.get("camera", {})
                print(f"  Camera Available: {camera.get('available')}")
                print(f"  Camera Capturing: {camera.get('capturing')}")
                print(f"  Status: {camera.get('status')}")
                print(f"  Message: {camera.get('message')}")

                retry_info = status.get("retry_info")
                if retry_info:
                    print(f"  Retry Count: {retry_info.get('count')}")
                    print(
                        f"  Retry Interval: {retry_info.get('retry_interval_seconds')}s"
                    )

        # Test 2: Camera Test (Diagnostics)
        print("\n[TEST 2] Running camera diagnostics...")
        async with session.post(f"{base_url}/api/camera/test") as resp:
            data = await resp.json()
            print(f"Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
            diagnostics = data.get("diagnostics", {})
            print(f"  Overall Status: {diagnostics.get('overall_status')}")
            print(f"  Message: {diagnostics.get('message')}")

            tests = diagnostics.get("tests", [])
            print(f"  Tests Run: {len(tests)}")
            for test in tests:
                status_icon = "PASS" if test.get("status") == "PASS" else "FAIL"
                print(f"    - {test.get('name')}: {status_icon}")
                print(f"      {test.get('message')}")

        # Test 3: Try to Open Camera (if not already open)
        print("\n[TEST 3] Attempting to open camera...")
        async with session.post(f"{base_url}/api/camera/open") as resp:
            data = await resp.json()
            print(f"Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
            print(f"  Message: {data.get('message')}")
            print(f"  Status Code: {data.get('status')}")

        # Test 4: Check status again after open attempt
        print("\n[TEST 4] Checking status after open attempt...")
        async with session.get(f"{base_url}/api/camera/status") as resp:
            data = await resp.json()
            if data.get("success"):
                status = data.get("status", {})
                camera = status.get("camera", {})
                print(f"  Camera Available: {camera.get('available')}")
                print(f"  Camera Capturing: {camera.get('capturing')}")
                print(f"  Status: {camera.get('status')}")

        # Test 5: Get Alert History
        print("\n[TEST 5] Getting alert history...")
        async with session.get(f"{base_url}/api/alerts/history?limit=10") as resp:
            data = await resp.json()
            print(f"Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
            print(f"  Total Alerts: {data.get('count')}")
            alerts = data.get("alerts", [])
            if alerts:
                print("  Recent alerts:")
                for alert in alerts[:3]:  # Show first 3
                    print(
                        f"    - {alert.get('event_type')}: {alert.get('description', 'N/A')[:50]}"
                    )

        # Test 6: Get Alert Stats
        print("\n[TEST 6] Getting alert statistics...")
        async with session.get(f"{base_url}/api/alerts/stats") as resp:
            data = await resp.json()
            print(f"Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
            stats = data.get("stats", {})
            print(f"  Total Alerts: {stats.get('total_alerts')}")
            print(f"  Severity Breakdown: {stats.get('severity_breakdown')}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nTo test WebSocket alerts, open in browser console:")
    print("  const ws = new WebSocket('ws://localhost:8000/ws/alerts');")
    print("  ws.onmessage = (e) => console.log(JSON.parse(e.data));")


if __name__ == "__main__":
    asyncio.run(test_camera_api())
