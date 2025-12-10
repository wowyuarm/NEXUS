"""
Asynchronous event bus (NexusBus) for the NEXUS system.

This bus is the single communication channel across services. It provides:
- publish(topic, message): non-blocking message enqueue per topic
- subscribe(topic, handler): register async handlers to consume messages
- run_forever(): spawn a listener per topic and run them concurrently

Design notes:
- Each topic owns an asyncio.Queue used as the inbound buffer.
- Multiple subscribers per topic are supported; each handler execution is
  scheduled via asyncio.create_task to avoid one slow handler blocking others.
- Logging is added at key points to aid observability.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from .models import Message

logger = logging.getLogger(__name__)


class NexusBus:
    """Asynchronous, non-blocking event bus with per-topic queues and subscribers."""

    def __init__(self) -> None:
        # Per-topic inbound queues
        self._queues: dict[str, asyncio.Queue] = {}
        # Per-topic list of async handlers: Callable[[Message], Awaitable[None]]
        self._subscribers: dict[str, list[Callable[[Message], Awaitable[None]]]] = {}
        logger.debug("NexusBus initialized with no topics/subscribers")

    async def publish(self, topic: str, message: Message) -> None:
        """Publish a message to a topic if the topic queue exists.

        This is non-blocking with respect to subscribers: it only enqueues.
        """
        queue = self._queues.get(topic)
        if queue is None:
            logger.debug(
                "Dropping message for topic without queue: topic=%s run_id=%s msg_id=%s",
                topic,
                getattr(message, "run_id", None),
                getattr(message, "id", None),
            )
            return
        await queue.put(message)
        logger.info(
            "Published message: topic=%s run_id=%s msg_id=%s",
            topic,
            getattr(message, "run_id", None),
            getattr(message, "id", None),
        )

    def subscribe(
        self, topic: str, handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """Register an async handler for a topic; create queue/list if missing."""
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue()
            logger.debug("Created queue for topic=%s", topic)
        if topic not in self._subscribers:
            self._subscribers[topic] = []
            logger.debug("Created subscriber list for topic=%s", topic)
        self._subscribers[topic].append(handler)
        logger.info(
            "Subscribed handler to topic=%s (total=%d)",
            topic,
            len(self._subscribers[topic]),
        )

    async def run_forever(self) -> None:
        """Start listeners for all current topics and run indefinitely.

        Note: Listeners are started for the topics known at invocation time.
        """
        if not self._queues:
            logger.info("NexusBus run_forever started with no topics; idling")
            # Idle forever until externally cancelled, preserving contract.
            await asyncio.Event().wait()
            return

        tasks: list[asyncio.Task] = []
        for topic, queue in self._queues.items():
            task = asyncio.create_task(
                self._listener(topic, queue), name=f"nexusbus-listener:{topic}"
            )
            tasks.append(task)
            logger.info("Listener started for topic=%s", topic)

        # Run all listeners concurrently; they are long-lived tasks
        await asyncio.gather(*tasks)

    async def _listener(self, topic: str, queue: asyncio.Queue) -> None:
        """Continuously consume messages from a topic queue and fan-out to handlers."""
        while True:
            message: Message = await queue.get()
            try:
                handlers = self._subscribers.get(topic, [])
                logger.debug(
                    "Message received on topic=%s run_id=%s msg_id=%s; dispatching to %d handlers",
                    topic,
                    getattr(message, "run_id", None),
                    getattr(message, "id", None),
                    len(handlers),
                )
                for handler in handlers:
                    task: asyncio.Task[None] = asyncio.ensure_future(handler(message))

                    # Attach a done callback to surface exceptions for observability
                    def _done_cb(t: asyncio.Task, msg: Message = message) -> None:
                        exc = t.exception()
                        if exc is not None:
                            logger.exception(
                                "Subscriber handler raised on topic=%s run_id=%s msg_id=%s: %s",
                                topic,
                                getattr(msg, "run_id", None),
                                getattr(msg, "id", None),
                                exc,
                            )

                    task.add_done_callback(_done_cb)
            finally:
                queue.task_done()
