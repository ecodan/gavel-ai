"""
gavel_ai.scaffolds — Standalone helpers for external system authors.

Provides base classes and transport glue for building systems under test (SUT)
that integrate with the Gavel evaluation framework over the HTTP or script
(subprocess + temp-dir) transports.

Importing from this package does NOT pull in any gavel_ai.core.* pipeline
or runtime modules.

Quickstart::

    # HTTP transport
    from gavel_ai.scaffolds import RemoteSystemUnderTest
    from gavel_ai.models.runtime import ExternalTaskRequest

    class MyHTTPSUT(RemoteSystemUnderTest):
        def handle(self, request: ExternalTaskRequest):
            return {"output": "response text"}

    # Script transport
    from gavel_ai.scaffolds import ScriptSystemUnderTest

    class MyScriptSUT(ScriptSystemUnderTest):
        def handle(self, request: ExternalTaskRequest):
            return {"output": "response text"}

    if __name__ == "__main__":
        MyScriptSUT().main()

See: docs/specs/schema-external-runner.md
"""

from gavel_ai.scaffolds.base import ScaffoldValidationError, _BaseSystemUnderTest
from gavel_ai.scaffolds.remote import RemoteSystemUnderTest
from gavel_ai.scaffolds.script import ScriptSystemUnderTest

__all__ = [
    "_BaseSystemUnderTest",
    "RemoteSystemUnderTest",
    "ScaffoldValidationError",
    "ScriptSystemUnderTest",
]
