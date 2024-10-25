from typing import Any, Dict, List


def chat(
    model: str,
    messages: List[str] = [],
    stream: bool = False,
    options: Dict[str, Any] = {},
):
    if stream:
        for _ in range(1):
            yield {"message": {"content": "dummy content"}}
    else:
        return {"message": {"content": "dummy content"}}
