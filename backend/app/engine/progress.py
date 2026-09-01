"""
In-Process-ProgressBroker: publishes ProgressEvents an WebSocket-Subscriber.

Pro Job existiert eine Menge von ``asyncio.Queue``-Subscribern (ein Websocket
pro Client). Zusätzlich werden die letzten N Events pro Job behalten, damit
ein neu verbundener Client sofort den aktuellen Stand bekommt.

Die Broker-Schnittstelle ist bewusst klein gehalten (subscribe/unsubscribe/
publish) — ein späterer Umstieg auf Redis/Broadcast bleibt möglich, ohne
den Runner zu ändern.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from ..schemas import ProgressEvent


class ProgressBroker:
    def __init__(self, max_recent: int = 500) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._recent: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_recent))

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Neuen Subscriber anmelden; liefert Queue mit letzten Events vorbefüllt."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[job_id].add(queue)
        for event in self._recent[job_id]:
            queue.put_nowait(event)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(job_id)
        if subscribers:
            subscribers.discard(queue)

    def has_subscribers(self, job_id: str) -> bool:
        return bool(self._subscribers.get(job_id))

    async def publish(self, event: ProgressEvent) -> None:
        """Event an alle Subscriber des Jobs verteilen (+ Recent-Puffer)."""
        self._recent[event.job_id].append(event)
        for queue in list(self._subscribers.get(event.job_id, ())):
            queue.put_nowait(event)

    def close_job(self, job_id: str) -> None:
        """Subscriber-Sets für abgeschlossene Jobs aufräumen (Recent bleibt)."""
        self._subscribers.pop(job_id, None)


# Singleton — wird in main.py/ws.py genutzt
broker = ProgressBroker()
