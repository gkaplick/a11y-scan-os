"""
WebSocket-Endpunkt für Live-Status eines Jobs.

``WS /ws/jobs/{job_id}`` — der Broker liefert pro Client eine Queue, die beim
Verbinden mit den letzten Events vorbefüllt ist (so sieht ein später
beigetretener Client sofort den aktuellen Stand). Events werden als
``ProgressEvent``-JSON gesendet; auf ``done``/``error`` schließt der Client
typischerweise die Verbindung selbst.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..engine.progress import broker

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    queue = broker.subscribe(job_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(job_id, queue)
