from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


class SlowSubscriberDropped(RuntimeError):
    pass


@dataclass(eq=False)
class HubSubscription:
    session_id: str
    queue: asyncio.Queue[dict[str, Any]]
    dropped: bool = False

    async def receive(self) -> dict[str, Any]:
        if self.dropped and self.queue.empty():
            raise SlowSubscriberDropped("subscriber queue overflowed")
        return await self.queue.get()


class BoundedEventHub:
    def __init__(self, *, queue_size: int = 64) -> None:
        self.queue_size = queue_size
        self._subscribers: dict[str, set[HubSubscription]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str) -> HubSubscription:
        subscription = HubSubscription(
            session_id=session_id,
            queue=asyncio.Queue(maxsize=self.queue_size),
        )
        async with self._lock:
            self._subscribers.setdefault(session_id, set()).add(subscription)
        return subscription

    async def unsubscribe(self, subscription: HubSubscription) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(subscription.session_id)
            if subscribers is None:
                return
            subscribers.discard(subscription)
            if not subscribers:
                self._subscribers.pop(subscription.session_id, None)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(session_id, set()))
            for subscription in subscribers:
                try:
                    subscription.queue.put_nowait(event)
                except asyncio.QueueFull:
                    subscription.dropped = True
                    self._subscribers[session_id].discard(subscription)
            if session_id in self._subscribers and not self._subscribers[session_id]:
                self._subscribers.pop(session_id, None)

    def subscriber_count(self, session_id: str) -> int:
        return len(self._subscribers.get(session_id, set()))
