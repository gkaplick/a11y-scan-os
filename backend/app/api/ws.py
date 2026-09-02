"""
WebSocket-Endpunkt für Live-Status eines Jobs.

``WS /ws/jobs/{job_id}`` — der Broker liefert pro Client eine Queue, die beim
Verbinden mit den letzten Events vorbefüllt ist (so sieht ein später
beigetretener Client sofort den aktuellen Stand). Events werden als
``ProgressEvent``-JSON gesendet; auf ``done``/``error`` schließt der Client
typischerweise die Verbindung selbst.

Auth: Der Nitro-WS-Tunnel reicht Cookies nicht ans Backend weiter — die SPA
hängt deshalb ein kurzlebiges Einmal-Ticket (``?ws_token=…``) an. Ohne
gültiges Ticket wird die Verbindung vor dem Subscribe geschlossen (Code 1008).
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..engine.progress import broker
from ..security import consume_ws_token

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    # Auth prüfen (Einmal-Ticket wird beim Validieren verbraucht). Erst nach
    # erfolgreicher Prüfung subscriben — sonst bekäme der Client Events.
    user = await consume_ws_token(websocket.query_params.get("ws_token"))
    if user is None:
        await websocket.close(code=1008, reason="nicht autorisiert")
        return

    queue = broker.subscribe(job_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(job_id, queue)
