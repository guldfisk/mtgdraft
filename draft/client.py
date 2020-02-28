import json
import threading
import typing as t
from abc import ABC, abstractmethod

import websocket

from mtgorp.db.database import CardDatabase
from mtgorp.models.serilization.strategies.raw import RawStrategy

from magiccube.collections import cubeable as Cubeable

from draft.models import Booster


class DraftClient(ABC):

    def __init__(self, host: str, draft_id: str, db: CardDatabase):
        self._draft_id = draft_id
        self._db = db

        self._lock = threading.Lock()

        self._ws = websocket.WebSocketApp(
            'ws://{}/ws/draft/{}/'.format(
                host,
                self._draft_id
            ),
            on_message = self.on_message,
            on_error = self.on_error,
            on_close = self.on_close,
        )
        self._ws.on_open = self.on_open

        self._booster_map: t.MutableMapping[str, Booster] = {}
        self._current_booster: t.Optional[Booster] = None

        self._ws_thread = threading.Thread(target = self._ws.run_forever, daemon = True)
        self._ws_thread.start()

    @abstractmethod
    def _received_booster(self, booster: Booster):
        pass

    def pick(self, cubeable: Cubeable) -> None:
        self._ws.send(
            json.dumps(
                {
                    'type': 'pick',
                    'pick': RawStrategy.serialize(cubeable),
                }
            )
        )

    def on_error(self, error):
        print(error)

    def on_close(self):
        print("### closed ###")

    def on_open(self):
        pass

    def on_message(self, message):
        message = json.loads(message)
        print(message)
        message_type = message['type']

        if message_type == 'booster':
            with self._lock:
                self._current_booster = RawStrategy(self._db).deserialize(
                    Booster,
                    message['booster'],
                )
            self._received_booster(self._current_booster)
