"""Tests for Prometheus metrics push gateway functionality."""

import asyncio
from unittest.mock import patch

import pytest

from langhook.map.metrics import metrics


class TestPrometheusMetrics:
    """Test Prometheus metrics push gateway functionality."""

    @pytest.mark.asyncio
    async def test_default_configuration_no_push(self):
        """Test that default configuration doesn't enable push gateway."""
        # Reset to default state
        metrics.configure_push_gateway(None)
        
        # Start and stop should work without issues
        await metrics.start_push_task()
        await asyncio.sleep(0.1)
        await metrics.stop_push_task()
        
        # Should not have a push task running
        assert metrics._push_task is None
        assert not metrics._push_enabled

    @pytest.mark.asyncio
    async def test_push_gateway_configuration(self):
        """Test configuring push gateway settings."""
        test_url = "http://test-pushgateway:9091"
        test_job = "test-job"
        test_interval = 10
        
        metrics.configure_push_gateway(test_url, test_job, test_interval)
        
        assert metrics._pushgateway_url == test_url
        assert metrics._job_name == test_job
        assert metrics._push_interval == test_interval
        assert metrics._push_enabled is True

    @pytest.mark.asyncio
    async def test_push_gateway_functionality(self):
        """Test that metrics are actually pushed to gateway."""
        test_url = "http://localhost:9091"
        
        with patch('langhook.map.metrics.push_to_gateway') as mock_push:
            metrics.configure_push_gateway(test_url, "test-job", 1)  # 1 second interval
            await metrics.start_push_task()
            
            # Record some metrics
            metrics.record_event_processed("test")
            metrics.record_event_mapped("test")
            
            # Wait for push to happen
            await asyncio.sleep(1.5)
            
            await metrics.stop_push_task()
            
            # Verify push was called
            assert mock_push.called
            
            # Verify correct parameters
            call_args = mock_push.call_args
            assert call_args[0][0] == test_url  # First positional arg is gateway URL
            assert call_args[1]['job'] == 'test-job'  # Keyword arg

    @pytest.mark.asyncio
    async def test_push_gateway_error_handling(self):
        """Test that push gateway errors are handled gracefully."""
        test_url = "http://invalid-url:9091"
        
        with patch('langhook.map.metrics.push_to_gateway', side_effect=Exception("Connection error")):
            metrics.configure_push_gateway(test_url, "test-job", 1)
            await metrics.start_push_task()
            
            # Wait for push attempt
            await asyncio.sleep(1.5)
            
            # Should still be running despite error
            assert metrics._push_task is not None
            
            await metrics.stop_push_task()

    @pytest.mark.asyncio
    async def test_start_stop_push_task_idempotent(self):
        """Test that start/stop push task operations are idempotent."""
        metrics.configure_push_gateway("http://localhost:9091", "test-job", 30)
        
        # Multiple starts should not create multiple tasks
        await metrics.start_push_task()
        first_task = metrics._push_task
        await metrics.start_push_task()
        assert metrics._push_task is first_task
        
        # Stop should work
        await metrics.stop_push_task()
        assert metrics._push_task is None
        
        # Multiple stops should not cause issues
        await metrics.stop_push_task()
        assert metrics._push_task is None

    def test_metrics_text_generation(self):
        """Test that metrics text generation still works."""
        # Record some metrics
        metrics.record_event_processed("github")
        metrics.record_event_mapped("github")
        
        # Get metrics text
        metrics_text = metrics.get_metrics_text()
        
        # Should contain Prometheus format
        assert "langhook_events_processed_total" in metrics_text
        assert "langhook_events_mapped_total" in metrics_text
        assert isinstance(metrics_text, str)
        assert len(metrics_text) > 0

    def test_metrics_dict_generation(self):
        """Test that metrics dict generation still works."""
        metrics_dict = metrics.get_metrics_dict()
        
        assert isinstance(metrics_dict, dict)
        assert "uptime_seconds" in metrics_dict
        assert "active_mappings" in metrics_dict
        assert isinstance(metrics_dict["uptime_seconds"], (int, float))