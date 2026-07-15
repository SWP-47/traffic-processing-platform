# ==============================================================================
# CnSS UDP Ingestion Server Unit Tests
# Validates UDP datagram reception, MTU enforcement, JSON/Pydantic validation,
# and the processing pipeline orchestration against architecture.md §2.1.
# ==============================================================================

import json
from unittest.mock import MagicMock, patch

import pytest

from core.contracts.udp_contracts import PacketMeta, TelemetryBatch
from core.exceptions import ConfigurationError
from services.ingestion.udp_server import UDPIngestionProtocol, UDPIngestionServer

# --- Custom Mock Helper ---


class MockAsyncMethod:
    """
    Custom async method mock to bypass Python 3.13 AsyncMock GC warnings.
    Python 3.13's AsyncMock can emit 'coroutine was never awaited' warnings
    during garbage collection. This lightweight class provides the exact
    same assertion semantics without relying on unittest.mock internals.
    """

    def __init__(self):
        self.call_count = 0
        self.call_args = None

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.call_args = (args, kwargs)

    def assert_called_once_with(self, *args, **kwargs):
        assert self.call_count == 1, f"Expected 1 call, got {self.call_count}"
        assert self.call_args == (args, kwargs), f"Expected args {(args, kwargs)}, got {self.call_args}"


# --- Test Fixtures ---


@pytest.fixture
def mock_transport():
    """Provides a mocked asyncio transport."""
    return MagicMock()


@pytest.fixture
def mock_on_batch_received():
    """
    Provides a mock for the batch received callback.
    IMPORTANT: We use MagicMock instead of AsyncMock here. In synchronous tests
    where asyncio.create_task is mocked, using AsyncMock would create a coroutine
    that is never awaited, triggering Python 3.13 GC warnings.
    """
    return MagicMock()


@pytest.fixture
def protocol(mock_on_batch_received):
    """Provides a UDPIngestionProtocol instance."""
    return UDPIngestionProtocol(on_batch_received=mock_on_batch_received)


@pytest.fixture
def server():
    """Provides a UDPIngestionServer instance with dummy dependencies."""
    # Use simple MagicMock for dependencies to avoid AsyncMock initialization warnings
    return UDPIngestionServer(
        state_manager=MagicMock(),
        buffer_manager=MagicMock(),
        flusher=MagicMock(),
    )


@pytest.fixture
def valid_batch_payload():
    """Returns a valid TelemetryBatch dictionary."""
    return {
        "channel_id": "test-ch",
        "timestamp": 1700000000,
        "sequence": 100,
        "window_ms": 1000,
        "packets": [{"direction": 0, "src_ip": "10.0.0.1", "dst_ip": "10.0.0.2", "src_port": 1234, "dst_port": 80, "size": 128}],
    }


# --- UDPIngestionProtocol Tests ---


class TestUDPIngestionProtocol:
    """Tests for the low-level UDP datagram handling and validation."""

    def test_connection_made(self, protocol, mock_transport):
        """Verify that connection_made stores the transport reference."""
        protocol.connection_made(mock_transport)
        assert protocol.transport == mock_transport

    @patch("services.ingestion.udp_server.asyncio.create_task")
    def test_datagram_received_valid(self, mock_create_task, protocol, valid_batch_payload):
        """
        Architecture §2.1: Valid JSON payloads must be parsed and scheduled for processing.
        """
        data = json.dumps(valid_batch_payload).encode("utf-8")
        addr = ("192.168.1.1", 5000)

        protocol.datagram_received(data, addr)

        # Verify create_task was called to schedule the async callback
        mock_create_task.assert_called_once()

    @patch("services.ingestion.udp_server.asyncio.create_task")
    @patch("services.ingestion.udp_server.settings")
    def test_datagram_received_oversized_mtu(self, mock_settings, mock_create_task, protocol, valid_batch_payload):
        """
        Architecture §2.1: MTU constraint is warn-only. Oversized payloads must still be processed.
        """
        # Set artificially low MTU to trigger the warning path
        mock_settings.cnss_udp_mtu = 10
        data = json.dumps(valid_batch_payload).encode("utf-8")
        addr = ("192.168.1.1", 5000)

        protocol.datagram_received(data, addr)

        # Verify it was still scheduled despite exceeding MTU
        mock_create_task.assert_called_once()

    @patch("services.ingestion.udp_server.asyncio.create_task")
    def test_datagram_received_invalid_json(self, mock_create_task, protocol):
        """
        Verify that malformed JSON is rejected and callback is not scheduled.
        """
        data = b"not a json string"
        addr = ("192.168.1.1", 5000)

        protocol.datagram_received(data, addr)

        mock_create_task.assert_not_called()

    @patch("services.ingestion.udp_server.asyncio.create_task")
    def test_datagram_received_invalid_structure(self, mock_create_task, protocol):
        """
        Verify that JSON with invalid structure (Pydantic ValidationError) is rejected.
        """
        # Missing required fields like 'channel_id', 'sequence', etc.
        data = json.dumps({"invalid": "payload"}).encode("utf-8")
        addr = ("192.168.1.1", 5000)

        protocol.datagram_received(data, addr)

        mock_create_task.assert_not_called()

    def test_error_received(self, protocol):
        """Verify that protocol errors are logged without crashing."""
        # Should not raise any exceptions
        protocol.error_received(Exception("Test error"))

    def test_connection_lost(self, protocol):
        """Verify that connection loss is handled gracefully."""
        # Should not raise any exceptions
        protocol.connection_lost(None)
        protocol.connection_lost(Exception("Test error"))


# --- UDPIngestionServer Tests ---


class TestUDPIngestionServer:
    """Tests for the high-level server orchestration and lifecycle."""

    async def test_handle_batch_pipeline(self, server):
        """
        Architecture §2.1: _handle_batch must orchestrate the processing pipeline:
        1. Register channel with flusher.
        2. Fast Path state update.
        3. Buffer raw packet metadata.
        """
        batch = TelemetryBatch(
            channel_id="test-ch",
            timestamp=1700000000,
            sequence=100,
            window_ms=1000,
            packets=[PacketMeta(direction=0, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=1234, dst_port=80, size=128)],
        )
        addr = ("192.168.1.1", 5000)

        # Use custom MockAsyncMethod to completely bypass Python 3.13 AsyncMock GC warnings
        mock_register = MockAsyncMethod()
        mock_process = MockAsyncMethod()
        mock_push = MockAsyncMethod()

        # Inject custom mocks directly into the server's dependencies
        server._flusher.register_channel = mock_register
        server._state_manager.process_batch = mock_process
        server._buffer_manager.push_packets = mock_push

        await server._handle_batch(batch, addr)

        # Verify pipeline execution and arguments
        mock_register.assert_called_once_with("test-ch")
        mock_process.assert_called_once_with(batch)
        mock_push.assert_called_once_with(batch)

    async def test_start_binds_endpoint(self, server):
        """
        Verify that start() creates a UDP datagram endpoint on the configured port.
        """
        mock_transport = MagicMock()
        mock_protocol = MagicMock()

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()

            # Define a real async function to mock the endpoint creation.
            # This prevents AsyncMock from generating unawaited coroutines.
            async def mock_create_endpoint(*args, **kwargs):
                return (mock_transport, mock_protocol)

            mock_loop.create_datagram_endpoint = mock_create_endpoint
            mock_get_loop.return_value = mock_loop

            await server.start()

            # Verify transport and protocol were assigned correctly
            assert server.transport == mock_transport
            assert server.protocol == mock_protocol

    async def test_start_invalid_port(self, server):
        """
        Verify that start() raises ConfigurationError for invalid port numbers.
        """
        with patch("services.ingestion.udp_server.settings") as mock_settings:
            mock_settings.cnss_udp_port = 0  # Invalid port

            with pytest.raises(ConfigurationError):
                await server.start()

    async def test_stop_closes_transport(self, server):
        """
        Verify that stop() gracefully closes the UDP transport.
        """
        mock_transport = MagicMock()
        server.transport = mock_transport

        await server.stop()

        mock_transport.close.assert_called_once()
        assert server.transport is None
        assert server.protocol is None

    async def test_stop_no_transport(self, server):
        """
        Verify that stop() handles the case where transport is already None.
        """
        server.transport = None
        # Should not raise any exceptions
        await server.stop()
