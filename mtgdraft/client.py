from __future__ import annotations

import typing as t
import json
import threading

from abc import ABC, abstractmethod

import websocket

from mtgorp.db.database import CardDatabase
from mtgorp.models.serilization.strategies.raw import RawStrategy

from cubeclient.models import User, ApiClient

from mtgdraft.models import Booster, DraftRound, Pick, SinglePickPick, BurnPick


P = t.TypeVar('P', bound = Pick)


class DraftFormat(t.Generic[P]):
    pick_type: t.TypeVar[Pick]

    def __init__(self, draft_client: DraftClient):
        self._draft_client = draft_client

    def pick(self, pick: P) -> t.Any:
        self._draft_client.socket.send(
            json.dumps(
                {
                    'type': 'pick',
                    'pick': pick.serialize(),
                }
            )
        )


class SinglePick(DraftFormat[SinglePickPick]):
    pick_type = SinglePickPick


class Burn(DraftFormat[BurnPick]):
    pick_type = BurnPick


draft_format_map = {
    'single_pick': SinglePick,
    'burn': Burn,
}


class DraftClient(ABC):

    def __init__(self, api_client: ApiClient, draft_id: str, db: CardDatabase):
        self._api_client = api_client
        self._draft_id = draft_id
        self._db = db

        self._drafters: t.Optional[t.List[User]] = None
        self._draft_format: t.Optional[DraftFormat] = None

        self._pool_id: t.Optional[int] = None
        self._session_name: t.Optional[str] = None

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
    def socket(self) -> websocket.WebSocketApp:
        return self._ws

    def close(self):
        self._ws.close()

    @property
    def drafters(self) -> t.List[User]:
        return self._drafters

    @property
    def draft_format(self) -> DraftFormat:
        return self._draft_format

    @property
    def round(self) -> DraftRound:
        return self._round

    @property
    def pool_id(self) -> t.Optional[int]:
        return self._pool_id

    @property
    def session_name(self) -> t.Optional[str]:
        return self._session_name

    @abstractmethod
    def _received_booster(self, booster: Booster) -> None:
        pass

    @abstractmethod
    def _picked(self, pick: Pick, pick_number: int, booster: Booster) -> None:
        pass

    @abstractmethod
    def _completed(self, pool_id: int, session_name: str) -> None:
        pass

    @abstractmethod
    def _on_start(self) -> None:
        pass

    @abstractmethod
    def _on_round(self, draft_round: DraftRound) -> None:
        pass

    def on_error(self, error):
        print(error)

    def on_close(self):
        print("### closed ###")

    def on_open(self):
        pass

    def on_message(self, message):
        message = json.loads(message)
        self._handle_message(message)

    def _handle_message(self, message: t.Mapping[str, t.Any]):
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
                pick = RawStrategy(self._db).deserialize(self._draft_format.pick_type, message['pick']),
                pick_number = message['pick_number'],
                booster = RawStrategy(self._db).deserialize(
                    Booster,
                    message['booster'],
                ),
            )

        elif message_type == 'round':
            self._round = DraftRound(**message['round'])
            self._on_round(self._round)

        elif message_type == 'started':
            self._drafters = [
                User.deserialize(
                    user,
                    self._api_client,
                ) for user in
                message['drafters']
            ]
            self._draft_format = draft_format_map[message['draft_format']](self)
            self._on_start()

        elif message_type == 'completed':
            self._pool_id = message['pool_id']
            self._session_name = message['session_name']
            self._completed(self._pool_id, self._session_name)
            self._ws.close()

        elif message_type == 'previous_messages':
            for sub_message in message['messages']:
                self._handle_message(sub_message)

        else:
            print('unknown message type', message_type)
