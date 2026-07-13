# -*- coding: utf-8 -*-

from __future__ import annotations

from importlib import import_module
from typing import Text


PARSER_MAPPING = {
    "weather": "function_call.dm.weather",
    "maps": "function_call.dm.maps",
    "music": "function_call.dm.music",
}


class DMFactory:
    """Lazy domain manager loader."""

    @staticmethod
    def get(name: Text):
        module_path = PARSER_MAPPING.get(name)
        if not module_path:
            return None
        try:
            return import_module(module_path).process
        except ModuleNotFoundError:
            legacy_path = module_path.replace("function_call.", "")
            return import_module(legacy_path).process
