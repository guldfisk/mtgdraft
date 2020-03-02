import json
import threading
import typing as t
from abc import ABC, abstractmethod

import websocket

from cubeclient.models import CubeRelease, User
from magiccube.laps.purples.purple import Purple
from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from mtgorp.db.database import CardDatabase
from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.strategies.raw import RawStrategy

from magiccube.collections import cubeable as Cubeable

from draft.models import Booster


class DraftClient(ABC):
    _deserialize_type_map = {
        'Trap': Trap,
        'Ticket': Ticket,
        'Purple': Purple,
    }

    def __init__(self, host: str, draft_id: str, db: CardDatabase):
        self._draft_id = draft_id
        self._db = db

        self._drafters: t.Optional[t.List[User]] = None
        self._release: t.Optional[int] = None
        self._draft_format: t.Optional[str] = None
        self._pack_amount: t.Optional[int] = None
        self._pack_size: t.Optional[int] = None

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

    def _deserialize_cubeable(self, cubeable: t.Any) -> Cubeable:
        try:
            return (
                self._db.printings[cubeable]
                if isinstance(cubeable, int) else
                RawStrategy(self._db).deserialize(
                    self._deserialize_type_map[cubeable['type']],
                    cubeable,
                )
            )
        except Exception as e:
            print(e)
            raise

    @abstractmethod
    def _received_booster(self, booster: Booster):
        pass

    @abstractmethod
    def _picked(self, pick: Cubeable):
        pass

    def pick(self, cubeable: Cubeable) -> None:
        self._ws.send(
            json.dumps(
                {
                    'type': 'pick',
                    'pick': cubeable.id if isinstance(cubeable, Printing) else RawStrategy.serialize(cubeable),
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
        elif message_type == 'pick':
            self._picked(
                self._deserialize_cubeable(message['pick'])
            )

        elif message_type == 'start':
            # self._users = [
            #     User.de
            # ]
            pass

        else:
            print('unknown message type', message_type)
