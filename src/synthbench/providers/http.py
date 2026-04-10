"""Generic HTTP endpoint provider."""

from __future__ import annotations

import httpx

from synthbench.providers.base import Provider, Response


class HttpProvider(Provider):
    """Call an arbitrary HTTP endpoint that accepts survey questions.

    The endpoint receives a POST with JSON body:
        {"question": str, "options": [str, ...]}

    And returns JSON:
        {"selected_option": str}
    """

    def __init__(self, url: str, headers: dict[str, str] | None = None, **kwargs):
        self._url = url
        self._client = httpx.AsyncClient(
            headers=headers or {},
            timeout=30,
        )

    @property
    def name(self) -> str:
        return f"http/{self._url}"

    async def respond(self, question: str, options: list[str]) -> Response:
        resp = await self._client.post(
            self._url,
            json={"question": question, "options": options},
        )
        resp.raise_for_status()
        data = resp.json()

        selected = data.get("selected_option", "")
        if selected not in options:
            # Try to match
            for opt in options:
                if opt.lower() == selected.lower():
                    selected = opt
                    break
            else:
                selected = options[0]

        return Response(
            selected_option=selected,
            raw_text=str(data),
            metadata=data.get("metadata"),
        )

    async def close(self) -> None:
        await self._client.aclose()
