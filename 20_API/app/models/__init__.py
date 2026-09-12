"""SQLAlchemy persistence model exports.

Models are imported lazily so modules can import ``Base`` from
``app.core.database`` without recursively importing the aggregate model
package while that model module is still being initialized.
"""

from importlib import import_module
from typing import Any

__all__ = ["Bar", "Instrument", "ExecutionOrder", "ExecutionAuditEvent", "ExecutionFill"]

_MODEL_MODULES = {
    "Bar": "app.models.market_data",
    "Instrument": "app.models.market_data",
    "ExecutionOrder": "app.models.execution",
    "ExecutionAuditEvent": "app.models.execution_history",
    "ExecutionFill": "app.models.execution_history",
}


def __getattr__(name: str) -> Any:
    module_name = _MODEL_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    return getattr(import_module(module_name), name)
