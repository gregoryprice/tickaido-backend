#!/usr/bin/env python3
"""
Performance Tests for FastMCP Implementation

Tests performance characteristics of the FastMCP implementation including:
- Tool call latency requirements
- Concurrent request handling
- Resource usage and cleanup
"""

import pytest
import asyncio
import time
import json
from statistics import mean, median
from unittest.mock import patch, AsyncMock
from mcp_client.fast_client import FastMCPClientWrapper


class TestFastMCPPerformance:
    """Performance tests to ensure FastMCP implementation is efficient."""
    
    @pytest.mark.asyncio
    async def test_tool_call_latency(self):
        """Test that tool calls complete within acceptable time."""
        client = FastMCPClientWrapper(token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8")
        
        # Mock fast responses
        with patch.object(client, '_get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_mcp_client.__aenter__.return_value = mock_mcp_client
            mock_mcp_client.__aexit__.return_value = None
            
            async def mock_call_tool(tool_name, params):
                # Simulate realistic API response time (100-500ms)
                await asyncio.sleep(0.1 + (hash(str(params)) % 4) / 10)
                result = type('Result', (), {
                    'content': '{"success": true, "tickets": []}'
                })()
                return result
            
            mock_mcp_client.call_tool = mock_call_tool
            mock_get_client.return_value = mock_mcp_client
            
            # Measure latencies over multiple calls
            latencies = []
            for i in range(10):
                start_time = time.time()
                await client.call_tool("list_tickets", page=i+1, page_size=5)
                latency = time.time() - start_time
                latencies.append(latency)
            
            avg_latency = mean(latencies)
            median_latency = median(latencies)
            max_latency = max(latencies)
            
            # Assert performance requirements from PRP
            assert avg_latency < 2.0, f"Average latency too high: {avg_latency:.2f}s (required: <2.0s)"
            assert median_latency < 1.5, f"Median latency too high: {median_latency:.2f}s (required: <1.5s)"
            assert max_latency < 5.0, f"Max latency too high: {max_latency:.2f}s (required: <5.0s)"
            
            # Log performance metrics for debugging
            print(f"Performance metrics: avg={avg_latency:.2f}s, median={median_latency:.2f}s, max={max_latency:.2f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test FastMCP handles concurrent tool calls efficiently."""
        client = FastMCPClientWrapper(token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8")
        
        # Mock responses for concurrent calls
        with patch.object(client, '_get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_mcp_client.__aenter__.return_value = mock_mcp_client
            mock_mcp_client.__aexit__.return_value = None
            
            call_count = 0
            async def mock_call_tool(tool_name, params):
                nonlocal call_count
                call_count += 1
                # Simulate realistic response time
                await asyncio.sleep(0.1)
                result = type('Result', (), {
                    'content': f'{{"success": true, "call_id": {call_count}, "tickets": []}}'
                })()
                return result
            
            mock_mcp_client.call_tool = mock_call_tool
            mock_get_client.return_value = mock_mcp_client
            
            # Test 5 concurrent calls
            start_time = time.time()
            tasks = [
                client.call_tool("list_tickets", page=1, page_size=3),
                client.call_tool("list_tickets", page=2, page_size=3),
                client.call_tool("get_system_health"),
                client.call_tool("search_tickets", query="test"),
                client.call_tool("list_tickets", page=3, page_size=3)
            ]
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # All calls should succeed
            assert len(results) == 5
            for i, result in enumerate(results[:4], 1):  # First 4 have call_id
                if "call_id" in result:
                    result_data = json.loads(result)
                    assert result_data["success"] is True
            
            # Should complete faster than 5 sequential calls
            # With 0.1s per call, concurrent should be ~0.1s, sequential would be ~0.5s
            assert total_time < 1.0, f"Concurrent calls took too long: {total_time:.2f}s (required: <1.0s)"
            
            # Verify all calls were made
            assert call_count == 5
            
            print(f"Concurrent performance: {len(tasks)} calls in {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test that FastMCP client doesn't leak memory."""
        # This test ensures proper cleanup and resource management
        
        client_instances = []
        
        # Create multiple client instances
        for i in range(10):
            client = FastMCPClientWrapper(token=f"test-token-{i}")
            client_instances.append(client)
        
        # Mock client interactions
        with patch.object(FastMCPClientWrapper, '_get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_mcp_client.__aenter__.return_value = mock_mcp_client
            mock_mcp_client.__aexit__.return_value = None
            mock_mcp_client.call_tool.return_value = type('Result', (), {
                'content': '{"success": true}'
            })()
            mock_get_client.return_value = mock_mcp_client
            
            # Make calls with each client
            for client in client_instances:
                await client.call_tool("test_tool")
                await client.close()
        
        # Verify all clients can be cleaned up
        for client in client_instances:
            assert client._client is None or not hasattr(client, '_client')
        
        print(f"Memory test: Created and cleaned up {len(client_instances)} clients")
    
    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Test that error recovery doesn't impact performance significantly."""
        client = FastMCPClientWrapper(token="test-token")
        
        # Mock alternating success/failure pattern
        with patch.object(client, '_get_client') as mock_get_client:
            call_count = 0
            
            async def mock_get_client_func():
                nonlocal call_count
                call_count += 1
                
                mock_mcp_client = AsyncMock()
                mock_mcp_client.__aenter__.return_value = mock_mcp_client
                mock_mcp_client.__aexit__.return_value = None
                
                if call_count % 2 == 0:  # Every other call fails
                    mock_mcp_client.call_tool.side_effect = Exception("Simulated failure")
                else:
                    mock_mcp_client.call_tool.return_value = type('Result', (), {
                        'content': '{"success": true}'
                    })()
                
                return mock_mcp_client
            
            mock_get_client.side_effect = mock_get_client_func
            
            # Time multiple calls with mixed success/failure
            start_time = time.time()
            
            results = []
            for i in range(6):  # 3 successes, 3 failures
                result = await client.call_tool("test_tool", iteration=i)
                results.append(result)
            
            total_time = time.time() - start_time
            
            # Verify we got both successes and failures
            successes = sum(1 for r in results if "success" in r and '"success": true' in r)
            failures = sum(1 for r in results if "error" in r)
            
            assert successes == 3, f"Expected 3 successes, got {successes}"
            assert failures == 3, f"Expected 3 failures, got {failures}"
            
            # Error recovery should not significantly impact performance
            avg_call_time = total_time / 6
            assert avg_call_time < 0.5, f"Error recovery too slow: {avg_call_time:.2f}s per call"
            
            print(f"Error recovery performance: {successes} successes, {failures} failures in {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_large_payload_handling(self):
        """Test handling of large payloads efficiently."""
        client = FastMCPClientWrapper(token="test-token")
        
        # Mock response with large payload
        large_ticket_list = [
            {
                "id": f"ticket-{i}",
                "title": f"Test Ticket {i}",
                "description": "A" * 500,  # 500 char description
                "category": "test",
                "priority": "medium"
            }
            for i in range(100)  # 100 tickets
        ]
        
        large_response = json.dumps({
            "success": True,
            "tickets": large_ticket_list,
            "total": 100
        })
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_mcp_client.__aenter__.return_value = mock_mcp_client
            mock_mcp_client.__aexit__.return_value = None
            mock_mcp_client.call_tool.return_value = type('Result', (), {
                'content': large_response
            })()
            mock_get_client.return_value = mock_mcp_client
            
            # Time the large payload handling
            start_time = time.time()
            result = await client.call_tool("list_tickets", page=1, page_size=100)
            latency = time.time() - start_time
            
            # Verify result is complete
            assert result == large_response
            
            # Large payload should still be handled efficiently
            assert latency < 1.0, f"Large payload handling too slow: {latency:.2f}s"
            
            print(f"Large payload performance: {len(large_response)} chars in {latency:.2f}s")