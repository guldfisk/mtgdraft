from __future__ import annotations

import json
import logging
import ssl
import threading
import typing as t
from abc import ABC, abstractmethod
from collections import defaultdict

import websocket

from ring import Ring

from mtgorp.db.database import CardDatabase
from mtgorp.models.serilization.strategies.raw import RawStrategy

from magiccube.collections.cube import Cube
from magiccube.collections.infinites import Infinites

from cubeclient.models import User, ApiClient, PoolSpecification

from mtgdraft.models import DraftBooster, DraftRound, DraftConfiguration, draft_format_map, PickPoint, DraftFormat


class PickHistory(t.Sequence[PickPoint]):

    def __init__(self):
        self._lock = threading.Lock()
        self._picks: t.MutableSequence[PickPoint] = []
        self._picks_map: t.MutableMapping[str, t.List[PickPoint]] = defaultdict(list)

    @property
    def current(self) -> t.Optional[PickPoint]:
        with self._lock:
            try:
                return self._picks[-1]
            except IndexError:
                return None

    def add_pick(self, pick: PickPoint) -> None:
        with self._lock:
            self._picks.append(pick)
            self._picks_map[pick.booster.booster_id].append(pick)

    def preceding_picks(self, pick: PickPoint) -> t.List[PickPoint]:
        with self._lock:
            picks = []
            for _pick in self._picks_map[pick.booster.booster_id]:
                if _pick == pick:
                    break
                picks.append(_pick)
            return picks

    def __getitem__(self, item) -> PickPoint:
        with self._lock:
            return self._picks[item]

    def __iter__(self) -> t.Iterator[PickPoint]:
        with self._lock:
            for pick in self._picks:
                yield pick

    def __len__(self) -> int:
        with self._lock:
            return len(self._picks)


class BoosterTracker(t.MutableMapping[User, int]):

    def __init__(self, users: t.Iterable[User]):
        self._user_map = {user: 0 for user in users}
        self._lock = threading.Lock()

    def __setitem__(self, k: User, v: int) -> None:
        with self._lock:
            self._user_map[k] = v

    def __delitem__(self, v: User) -> None:
        raise NotImplemented()

    def __getitem__(self, k: User) -> int:
        with self._lock:
            return self._user_map[k]

    def __len__(self) -> int:
        with self._lock:
            return len(self._user_map)

    def __iter__(self) -> t.Iterator[User]:
        with self._lock:
            for k in self._user_map.keys():
                yield k


class DraftClient(ABC):

    def __init__(
        self,
        api_client: ApiClient,
        draft_id: str, db: CardDatabase,
        *,
        verify_ssl: bool = True,
    ):
        self._api_client = api_client
        self._draft_id = draft_id
        self._db = db

        self._draft_format: t.Optional[DraftFormat] = None
        self._draft_configuration: t.Optional[DraftConfiguration] = None

        self._pool_id: t.Optional[int] = None
        self._session_name: t.Optional[str] = None

        self._round: t.Optional[DraftRound] = None

        self._pick_counter = 0
        self._global_pick_counter = 0

        self._history = PickHistory()
        self._booster_tracker: t.Optional[BoosterTracker] = None

        self._user_map: t.MutableMapping[int, User] = {}

        self._pool = Cube()

        self._lock = threading.Lock()

        self._ws = websocket.WebSocketApp(
            '{}://{}/ws/draft/{}/'.format(
                'wss' if self._api_client.scheme == 'https' else 'ws',
                self._api_client.host,
                self._draft_id,
            ),
            on_message = self.on_message,
            on_error = self.on_error,
            on_close = self.on_close,
        )
        self._ws.on_open = self.on_open

        self._ws_thread = threading.Thread(
            target = self._ws.run_forever,
            daemon = True,
            kwargs = None if verify_ssl else {'sslopt': {'cert_reqs': ssl.CERT_NONE}},
        )
        self._ws_thread.start()

    @property
    def history(self) -> PickHistory:
        return self._history

    @property
    def booster_tracker(self) -> BoosterTracker:
        return self._booster_tracker

    @property
    def draft_format(self) -> t.Optional[DraftFormat]:
        return self._draft_format

    @property
    def draft_configuration(self) -> t.Optional[DraftConfiguration]:
        return self._draft_configuration

    @property
    def socket(self) -> websocket.WebSocketApp:
        return self._ws

    def close(self):
        self._ws.close()

    @property
    def pool(self) -> Cube:
        with self._lock:
            return self._pool

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
    def _received_booster(self, pick_point: PickPoint) -> None:
        pass

    @abstractmethod
    def _picked(self, pick_point: PickPoint) -> None:
        pass

    @abstractmethod
    def _completed(self, pool_id: int, session_name: str) -> None:
        pass

    @abstractmethod
    def _on_start(self, draft_configuration: DraftConfiguration) -> None:
        pass

    @abstractmethod
    def _on_round(self, draft_round: DraftRound) -> None:
        pass

    @abstractmethod
    def _on_boosters_changed(self, booster_tracker: BoosterTracker) -> None:
        pass

    def _on_message_error(self, error: Exception) -> None:
        raise error

    def on_error(self, error):
        logging.error(f'socket_error: {error}')

    def on_close(self):
        logging.info('socket closed')

    def on_open(self) -> None:
        pass

    def on_message(self, message) -> None:
        try:
            self._handle_message(
                json.loads(message)
            )
        except Exception as e:
            self._on_message_error(e)

    def _handle_message(self, message: t.Mapping[str, t.Any]) -> None:
        logging.info(f'received {message}')
        message_type = message['type']

        if message_type == 'booster':
            booster = RawStrategy(self._db).deserialize(
                DraftBooster,
                message['booster'],
            )

            self._pick_counter += 1
            self._global_pick_counter += 1

            pick_point = PickPoint(
                self._draft_id,
                self._global_pick_counter,
                self._round,
                self._pick_counter,
                booster,
            )

            self._history.add_pick(pick_point)

            self._received_booster(pick_point)

        elif message_type == 'booster_amount_update':
            self._booster_tracker[self._user_map[message['drafter']]] = message['queue_size']
            self._on_boosters_changed(self._booster_tracker)

        elif message_type == 'pick':
            pick = RawStrategy(self._db).deserialize(
                self._draft_configuration.draft_format.pick_type,
                message['pick'],
            )
            with self._lock:
                self._pool += Cube(pick.added_cubeables)
            pick_point = self._history.current
            pick_point.set_pick(pick)
            self._picked(pick_point)

        elif message_type == 'round':
            self._round = DraftRound(
                booster_specification = self._draft_configuration.booster_specification_at(message['round']['pack']),
                **message['round'],
            )
            self._pick_counter = 0
            self._on_round(self._round)

        elif message_type == 'started':
            draft_format_type = draft_format_map[message['draft_format']]
            self._draft_configuration = DraftConfiguration(
                drafters = Ring(
                    User.deserialize(
                        user,
                        self._api_client,
                    ) for user in
                    message['drafters']
                ),
                draft_format = draft_format_type,
                pool_specification = PoolSpecification.deserialize(message['pool_specification'], self._api_client),
                infinites = RawStrategy(self._db).deserialize(Infinites, message['infinites']),
                reverse = message['reverse'],
            )
            self._draft_format = draft_format_type(self)
            self._user_map = {u.id: u for u in self._draft_configuration.drafters.all}
            self._booster_tracker = BoosterTracker(self._draft_configuration.drafters.all)
            self._on_start(self._draft_configuration)

        elif message_type == 'completed':
            self._pool_id = message['pool_id']
            self._session_name = message['session_name']
            self._completed(self._pool_id, self._session_name)
            self._ws.close()

        elif message_type == 'previous_messages':
            for sub_message in message['messages']:
                self._handle_message(sub_message)

        else:
            logging.warning(f'unknown message type {message_type}')
