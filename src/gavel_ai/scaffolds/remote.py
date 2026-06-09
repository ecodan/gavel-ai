"""
RemoteSystemUnderTest — HTTP transport scaffold.

Provides glue for building an HTTP server that handles Gavel task requests.
Subclass this and implement ``handle(request) -> result``.

This module does NOT import from gavel_ai.core.*.
See: docs/specs/schema-external-runner.md
"""

import json
from typing import Any, Dict

from gavel_ai.scaffolds.base import _BaseSystemUnderTest, _logger
from gavel_ai.models.runtime import ExternalResponseEnvelope


class RemoteSystemUnderTest(_BaseSystemUnderTest):
    """
    HTTP-transport scaffold for an external system under test.

    Subclasses implement ``handle(request) -> result``.  The ``handle_http_request``
    method wraps the full lifecycle (parse → handle → assemble) and returns a
    JSON-serialisable dict suitable for an HTTP response body.

    Example::

        from gavel_ai.scaffolds import RemoteSystemUnderTest
        from gavel_ai.models.runtime import ExternalTaskRequest

        class MyHTTPSystem(RemoteSystemUnderTest):
            def handle(self, request: ExternalTaskRequest):
                return {"output": call_my_model(request.rendered_prompt)}

        system = MyHTTPSystem()

        # In your HTTP handler (framework-agnostic):
        response_dict = system.handle_http_request(request_body_dict)
        # → {"status": "ok", "result": {...}, "metadata": {}, "issue": null, "trace_id": ...}
    """

    def handle_http_request(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Process an inbound HTTP POST body and return a serialisable response dict.

        Args:
            raw: Parsed JSON body dict from the HTTP request.

        Returns:
            JSON-serialisable dict matching ``ExternalResponseEnvelope`` schema.
        """
        envelope: ExternalResponseEnvelope = self.process(raw)
        result: Dict[str, Any] = json.loads(envelope.model_dump_json())
        return result
