import json
import threading
import typing as t
from abc import ABC, abstractmethod

import websocket

from cubeclient.models import User, ApiClient
from magiccube.laps.purples.purple import Purple
from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from mtgorp.db.database import CardDatabase
from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.strategies.raw import RawStrategy

from magiccube.collections import cubeable as Cubeable

from draft.models import Booster, DraftRound


class DraftClient(ABC):
    _deserialize_type_map = {
        'Trap': Trap,
        'Ticket': Ticket,
        'Purple': Purple,
    }

    def __init__(self, api_client: ApiClient, draft_id: str, db: CardDatabase):
        self._api_client = api_client
        self._draft_id = draft_id
        self._db = db

        self._drafters: t.Optional[t.List[User]] = None
        self._release: t.Optional[int] = None
        self._draft_format: t.Optional[str] = None
        self._pack_amount: t.Optional[int] = None
        self._pack_size: t.Optional[int] = None

        self._round: t.Optional[DraftRound] = None

        self._lock = threading.Lock()

        self._ws = websocket.WebSocketApp(
            'ws://{}/ws/draft/{}/'.format(
                self._api_client.host,
                self._draft_id,
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

    @property
    def drafters(self) -> t.List[User]:
        return self._drafters

    @property
    def round(self) -> DraftRound:
        return self._round

    def _deserialize_cubeable(self, cubeable: t.Any) -> Cubeable:
        return (
            self._db.printings[cubeable]
            if isinstance(cubeable, int) else
            RawStrategy(self._db).deserialize(
                self._deserialize_type_map[cubeable['type']],
                cubeable,
            )
        )

    @abstractmethod
    def _received_booster(self, booster: Booster) -> None:
        pass

    @abstractmethod
    def _picked(self, pick: Cubeable) -> None:
        pass

    @abstractmethod
    def _completed(self) -> None:
        pass

    @abstractmethod
    def _on_start(self) -> None:
        pass
    
    @abstractmethod
    def _on_round(self, draft_round: DraftRound) -> None:
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

        elif message_type == 'round':
            self._round = DraftRound(**message['round'])
            self._on_round(self._round)

        elif message_type == 'started':
            try:
                self._drafters = [
                    User.deserialize(
                        user,
                        self._api_client,
                    ) for user in
                    message['drafters']
                ]
                self._draft_format = message['draft_format']
                self._on_start()
            except Exception as e:
                print(e)
                raise e

        elif message_type == 'completed':
            self._completed()
            self._ws.close()

        else:
            print('unknown message type', message_type)
