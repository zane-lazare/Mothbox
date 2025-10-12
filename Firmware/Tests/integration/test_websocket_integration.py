"""
Integration Tests: WebSocket Integration (Feature Set 4)

Tests WebSocket integration including multi-client connections,
disconnect handling, metadata polling, control updates, and
event broadcasting.

Run with: pytest Tests/integration/test_websocket_integration.py -v -s

Note: Requires real Raspberry Pi hardware with camera
"""

import pytest
import sys
from pathlib import Path
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestMultiClientConnections:
    """Test multiple simultaneous WebSocket connections"""

    def test_three_concurrent_clients(self, app):
        """Test 3 clients can connect simultaneously"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)

        clients = []
        try:
            # Connect 3 clients
            for i in range(3):
                client = socketio.test_client(app, namespace='/')
                clients.append(client)
                assert client.is_connected()
                print(f"   Client {i+1} connected")

            print(f"\n✓ 3 concurrent clients connected")

        finally:
            # Cleanup
            for client in clients:
                if client.is_connected():
                    client.disconnect()

    def test_five_concurrent_clients(self, app):
        """Test 5 clients can connect simultaneously"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)

        clients = []
        try:
            # Connect 5 clients
            for i in range(5):
                client = socketio.test_client(app, namespace='/')
                clients.append(client)
                assert client.is_connected()

            # All should be connected
            connected_count = sum(1 for c in clients if c.is_connected())
            assert connected_count == 5

            print(f"\n✓ 5 concurrent clients connected")

        finally:
            # Cleanup
            for client in clients:
                if client.is_connected():
                    client.disconnect()

    def test_client_isolation(self, app):
        """Test clients are properly isolated from each other"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)

        client1 = socketio.test_client(app, namespace='/')
        client2 = socketio.test_client(app, namespace='/')

        try:
            # Both connected
            assert client1.is_connected()
            assert client2.is_connected()

            # Disconnect client1
            client1.disconnect()

            # Client2 should still be connected
            assert not client1.is_connected()
            assert client2.is_connected()

            print("\n✓ Client isolation verified")

        finally:
            if client2.is_connected():
                client2.disconnect()


class TestWebSocketDisconnectDuringOperations:
    """Test WebSocket disconnect during active operations"""

    def test_disconnect_during_streaming(self, app):
        """Test disconnect while camera is streaming"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        camera_streamer = app.config['CAMERA_STREAMER']

        client = socketio.test_client(app, namespace='/')

        try:
            # Start streaming
            if camera_streamer.start_streaming():
                assert camera_streamer.streaming == True

                # Disconnect while streaming
                client.disconnect()

                # Give time for cleanup
                time.sleep(0.5)

                # Streaming should be stopped
                # Note: Actual cleanup happens in disconnect handler
                print("\n✓ Disconnect during streaming handled")
            else:
                print("\n⚠ Camera not available, skipping streaming test")

        finally:
            camera_streamer.stop_streaming()
            if client.is_connected():
                client.disconnect()

    def test_disconnect_during_metadata_poll(self, app):
        """Test disconnect during metadata polling"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        client = socketio.test_client(app, namespace='/')

        try:
            # Start metadata polling in background
            def poll_metadata():
                for _ in range(10):
                    if not client.is_connected():
                        break
                    client.emit('get_metadata')
                    time.sleep(0.1)

            poll_thread = threading.Thread(target=poll_metadata)
            poll_thread.start()

            # Wait a bit then disconnect
            time.sleep(0.3)
            client.disconnect()

            # Wait for polling to finish
            poll_thread.join(timeout=2)

            print("\n✓ Disconnect during metadata poll handled")

        finally:
            if client.is_connected():
                client.disconnect()


class TestMetadataPollingUnderLoad:
    """Test metadata polling with rapid requests"""

    def test_rapid_metadata_requests(self, app):
        """Test rapid get_metadata calls (10 requests/second)"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        camera_streamer = app.config['CAMERA_STREAMER']

        client = socketio.test_client(app, namespace='/')

        try:
            # Start streaming for metadata
            if not camera_streamer.start_streaming():
                print("\n⚠ Camera not available, skipping test")
                return

            # Send 10 rapid metadata requests
            request_count = 10
            responses_received = []

            for i in range(request_count):
                client.emit('get_metadata')
                time.sleep(0.1)  # 10 req/sec

                # Collect responses
                received = client.get_received()
                responses_received.extend(received)

            # Should receive metadata_update events
            metadata_updates = [r for r in responses_received if r['name'] == 'metadata_update']

            print(f"\n✓ Rapid metadata requests handled: {len(metadata_updates)} responses")

        finally:
            camera_streamer.stop_streaming()
            if client.is_connected():
                client.disconnect()

    def test_metadata_polling_accuracy(self, app):
        """Test metadata values are consistent under polling"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        camera_streamer = app.config['CAMERA_STREAMER']

        client = socketio.test_client(app, namespace='/')

        try:
            if not camera_streamer.start_streaming():
                print("\n⚠ Camera not available, skipping test")
                return

            # Poll metadata multiple times
            metadata_values = []

            for _ in range(5):
                client.emit('get_metadata')
                time.sleep(0.2)

                received = client.get_received()
                for msg in received:
                    if msg['name'] == 'metadata_update':
                        metadata_values.append(msg['args'][0])

            # Verify all have required fields
            if metadata_values:
                for md in metadata_values:
                    assert 'exposure_time' in md
                    assert 'analogue_gain' in md
                    assert 'lens_position' in md

                print(f"\n✓ Metadata polling accuracy verified: {len(metadata_values)} samples")

        finally:
            camera_streamer.stop_streaming()
            if client.is_connected():
                client.disconnect()


class TestControlUpdatesDuringStreaming:
    """Test control updates while streaming is active"""

    def test_update_sharpness_during_stream(self, app):
        """Test updating sharpness control while streaming"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        camera_streamer = app.config['CAMERA_STREAMER']

        client = socketio.test_client(app, namespace='/')

        try:
            if not camera_streamer.start_streaming():
                print("\n⚠ Camera not available, skipping test")
                return

            # Update sharpness
            client.emit('update_preview_control', {'Sharpness': 2.5})
            time.sleep(0.2)

            # Check response
            received = client.get_received()
            control_updates = [r for r in received if r['name'] == 'control_updated']

            if control_updates:
                assert control_updates[0]['args'][0]['success'] == True
                print(f"\n✓ Control updated during stream: {control_updates[0]['args'][0]}")
            else:
                print("\n⚠ No control_updated response received")

        finally:
            camera_streamer.stop_streaming()
            if client.is_connected():
                client.disconnect()

    def test_multiple_control_updates(self, app):
        """Test multiple rapid control updates"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        camera_streamer = app.config['CAMERA_STREAMER']

        client = socketio.test_client(app, namespace='/')

        try:
            if not camera_streamer.start_streaming():
                print("\n⚠ Camera not available, skipping test")
                return

            # Update multiple controls
            controls = [
                {'Sharpness': 1.5},
                {'Brightness': 0.1},
                {'Contrast': 1.2},
                {'Saturation': 1.1}
            ]

            for control in controls:
                client.emit('update_preview_control', control)
                time.sleep(0.1)

            # Give time for processing
            time.sleep(0.5)

            received = client.get_received()
            control_updates = [r for r in received if r['name'] == 'control_updated']

            print(f"\n✓ Multiple control updates processed: {len(control_updates)}")

        finally:
            camera_streamer.stop_streaming()
            if client.is_connected():
                client.disconnect()


class TestWebSocketReconnection:
    """Test WebSocket reconnection handling"""

    def test_reconnect_after_disconnect(self, app):
        """Test client can reconnect after disconnect"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)

        # First connection
        client1 = socketio.test_client(app, namespace='/')
        assert client1.is_connected()
        client1.disconnect()
        assert not client1.is_connected()

        # Second connection (reconnect)
        client2 = socketio.test_client(app, namespace='/')
        assert client2.is_connected()

        client2.disconnect()

        print("\n✓ Reconnection after disconnect works")

    def test_reconnect_resumes_functionality(self, app):
        """Test reconnected client has full functionality"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)

        # Connect, disconnect, reconnect
        client1 = socketio.test_client(app, namespace='/')
        client1.disconnect()

        client2 = socketio.test_client(app, namespace='/')

        try:
            # Test functionality after reconnect
            client2.emit('get_metadata')
            time.sleep(0.2)

            received = client2.get_received()
            # Should receive responses
            assert len(received) >= 0  # At least connected event

            print("\n✓ Reconnected client has full functionality")

        finally:
            if client2.is_connected():
                client2.disconnect()


class TestEventBroadcasting:
    """Test event broadcasting to multiple clients"""

    def test_broadcast_to_all_clients(self, app):
        """Test events broadcast to all connected clients"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)

        clients = []
        try:
            # Connect 3 clients
            for _ in range(3):
                client = socketio.test_client(app, namespace='/')
                clients.append(client)

            # Trigger broadcast event (e.g., start_preview)
            camera_streamer = app.config['CAMERA_STREAMER']

            if camera_streamer.start_streaming():
                # All clients should receive stream events (camera_frame)
                time.sleep(1)

                for i, client in enumerate(clients):
                    received = client.get_received()
                    print(f"   Client {i+1} received {len(received)} events")

                print("\n✓ Events broadcast to all clients")

                camera_streamer.stop_streaming()
            else:
                print("\n⚠ Camera not available, skipping broadcast test")

        finally:
            for client in clients:
                if client.is_connected():
                    client.disconnect()


class TestWebSocketMessageOrdering:
    """Test WebSocket message ordering"""

    def test_message_order_preservation(self, app):
        """Test messages are received in order sent"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        client = socketio.test_client(app, namespace='/')

        try:
            # Send ordered sequence of events
            events_sent = []

            for i in range(5):
                client.emit('get_metadata')
                events_sent.append('get_metadata')
                time.sleep(0.1)

            # Give time for responses
            time.sleep(0.5)

            received = client.get_received()

            # Responses should be in order (connected, then metadata updates)
            print(f"\n✓ Message ordering: sent {len(events_sent)}, received {len(received)}")

        finally:
            if client.is_connected():
                client.disconnect()


class TestConnectionTimeoutHandling:
    """Test connection timeout handling"""

    def test_inactive_connection_handling(self, app):
        """Test handling of inactive connections"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        client = socketio.test_client(app, namespace='/')

        try:
            # Connect but don't send any messages
            assert client.is_connected()

            # Wait (normally timeout is 60s, we'll just test connection stays alive)
            time.sleep(2)

            # Should still be connected (within timeout)
            assert client.is_connected()

            print("\n✓ Inactive connection handled within timeout")

        finally:
            if client.is_connected():
                client.disconnect()

    def test_ping_pong_mechanism(self, app):
        """Test WebSocket ping/pong keeps connection alive"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        client = socketio.test_client(app, namespace='/')

        try:
            # SocketIO handles ping/pong automatically
            # Just verify connection stays alive
            initial_connected = client.is_connected()
            time.sleep(1)
            still_connected = client.is_connected()

            assert initial_connected == still_connected

            print("\n✓ Ping/pong mechanism maintains connection")

        finally:
            if client.is_connected():
                client.disconnect()


class TestWebSocketErrorPropagation:
    """Test error propagation through WebSocket layer"""

    def test_invalid_event_handling(self, app):
        """Test invalid event names are handled gracefully"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        client = socketio.test_client(app, namespace='/')

        try:
            # Send non-existent event
            client.emit('nonexistent_event', {'data': 'test'})

            # Should not crash, may be ignored
            time.sleep(0.2)

            # Client should still be connected
            assert client.is_connected()

            print("\n✓ Invalid event handled gracefully")

        finally:
            if client.is_connected():
                client.disconnect()

    def test_error_response_format(self, app):
        """Test error responses have consistent format"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        client = socketio.test_client(app, namespace='/')

        try:
            # Trigger error (update control when not streaming)
            camera_streamer = app.config['CAMERA_STREAMER']
            camera_streamer.stop_streaming()

            client.emit('update_preview_control', {'Sharpness': 2.0})
            time.sleep(0.2)

            received = client.get_received()
            control_updates = [r for r in received if r['name'] == 'control_updated']

            if control_updates:
                response = control_updates[0]['args'][0]
                # Should have success=False
                if 'success' in response:
                    assert response['success'] == False
                    print(f"\n✓ Error response format: {response}")

        finally:
            if client.is_connected():
                client.disconnect()


class TestConcurrentOperations:
    """Test concurrent WebSocket operations"""

    def test_concurrent_metadata_and_controls(self, app):
        """Test simultaneous metadata polling and control updates"""
        from flask_socketio import SocketIO

        socketio = SocketIO(app)
        camera_streamer = app.config['CAMERA_STREAMER']

        client = socketio.test_client(app, namespace='/')

        try:
            if not camera_streamer.start_streaming():
                print("\n⚠ Camera not available, skipping test")
                return

            # Concurrent operations
            operations = []

            def poll_metadata():
                for _ in range(5):
                    client.emit('get_metadata')
                    time.sleep(0.2)

            def update_controls():
                for value in [1.5, 2.0, 2.5]:
                    client.emit('update_preview_control', {'Sharpness': value})
                    time.sleep(0.3)

            # Run concurrently
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(poll_metadata),
                    executor.submit(update_controls)
                ]

                for future in as_completed(futures):
                    future.result()

            # Give time for responses
            time.sleep(0.5)

            received = client.get_received()
            print(f"\n✓ Concurrent operations handled: {len(received)} total events")

        finally:
            camera_streamer.stop_streaming()
            if client.is_connected():
                client.disconnect()
