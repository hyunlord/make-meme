"""MakeMemeSink: a cheap OUTPUT_NODE terminal.

Some workflows need to run purely for a side effect -- e.g. warming the Wan text
encoder's on-disk cache -- without producing anything worth saving or displaying.
ComfyUI requires every workflow to end at an OUTPUT_NODE; this is the cheapest one
that accepts any upstream output.
"""

from __future__ import annotations


class MakeMemeSink:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("*", {})}}

    RETURN_TYPES = ()
    FUNCTION = "sink"
    CATEGORY = "make-meme"
    OUTPUT_NODE = True

    def sink(self, value):
        return {"ui": {"ok": [True]}}
