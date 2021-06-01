from __future__ import annotations

import json
import typing as t
import uuid
from abc import abstractmethod, ABC
from dataclasses import dataclass

import websocket

from ring import Ring

from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator

from magiccube.collections.infinites import Infinites
from magiccube.collections.cubeable import Cubeable, serialize_cubeable, deserialize_cubeable
from magiccube.collections.cube import Cube

from cubeclient.models import User, PoolSpecification, BoosterSpecification


class Pick(Serializeable):

    @property
    @abstractmethod
    def picked(self) -> t.Iterable[Cubeable]:
        pass

    @property
    @abstractmethod
    def main_picked(self) -> Cubeable:
        pass

    @property
    @abstractmethod
    def added_cubeables(self) -> t.Iterable[Cubeable]:
        pass

    @abstractmethod
    def _serialize(self) -> t.Mapping[str, t.Any]:
        pass

    def serialize(self) -> serialization_model:
        return {
            'type': self.__class__.__name__,
            **self._serialize(),
        }

    @classmethod
    @abstractmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        if isinstance(value, int) or 'burn' not in value:
            return SinglePickPick.deserialize(value, inflator)
        return BurnPick.deserialize(value, inflator)

    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        pass

    def __repr__(self) -> str:
        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join(map(str, self.added_cubeables)),
        )


class SinglePickPick(Pick):

    def __init__(self, cubeable: Cubeable):
        self._cubeable = cubeable

    @property
    def picked(self) -> t.Iterable[Cubeable]:
        return self._cubeable,

    @property
    def main_picked(self) -> Cubeable:
        return self._cubeable

    @property
    def added_cubeables(self) -> t.Iterable[Cubeable]:
        return self._cubeable,

    @property
    def cubeable(self) -> Cubeable:
        return self._cubeable

    def _serialize(self) -> t.Mapping[str, t.Any]:
        return {
            'pick': serialize_cubeable(self._cubeable),
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        return cls(
            deserialize_cubeable(value['pick'], inflator)
            if isinstance(value, t.Mapping) and 'pick' in value else
            deserialize_cubeable(value, inflator)
        )

    def __hash__(self) -> int:
        return hash(self._cubeable)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._cubeable == other._cubeable
        )

    def __repr__(self) -> str:
        return '{}({})'.format(
            self.__class__.__name__,
            self._cubeable,
        )


class BurnPick(Pick):

    def __init__(self, pick: Cubeable, burn: t.Optional[Cubeable]):
        self._pick = pick
        self._burn = burn

    @property
    def picked(self) -> t.Iterable[Cubeable]:
        return self._pick, self._burn

    @property
    def main_picked(self) -> Cubeable:
        return self._pick

    @property
    def added_cubeables(self) -> t.Iterable[Cubeable]:
        return self._pick,

    @property
    def pick(self) -> Cubeable:
        return self._pick

    @property
    def burn(self) -> t.Optional[Cubeable]:
        return self._burn

    def _serialize(self) -> t.Mapping[str, t.Any]:
        return {
            'pick': serialize_cubeable(self._pick),
            'burn': None if self._burn is None else serialize_cubeable(self._burn),
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        return cls(
            deserialize_cubeable(value['pick'], inflator),
            None if value['burn'] is None else deserialize_cubeable(value['burn'], inflator),
        )

    def __hash__(self) -> int:
        return hash((self._pick, self._burn))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._pick == other._pick
            and self._burn == other._burn
        )

    def __repr__(self) -> str:
        return '{}({}, {})'.format(
            self.__class__.__name__,
            self._pick,
            self._burn,
        )


P = t.TypeVar('P', bound = Pick)


class BaseClient(ABC):

    @property
    @abstractmethod
    def socket(self) -> websocket.WebSocketApp:
        pass


class DraftFormat(t.Generic[P]):
    pick_type: t.Type[Pick]

    def __init__(self, draft_client: BaseClient):
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


@dataclass
class DraftConfiguration(object):
    pool_specification: PoolSpecification
    infinites: Infinites
    reverse: bool
    draft_format: t.Type[DraftFormat]
    drafters: Ring[User]

    def booster_specification_at(self, draft_round_number: int) -> t.Optional[BoosterSpecification]:
        for spec in self.pool_specification.booster_specifications:
            draft_round_number -= spec.amount
            if draft_round_number <= 0:
                return spec

        return self.pool_specification.booster_specifications[-1]


@dataclass
class DraftRound(object):
    pack: int
    clockwise: bool
    booster_specification: BoosterSpecification


class DraftBooster(Serializeable):

    def __init__(
        self,
        cubeables: Cube,
        booster_id: t.Optional[str] = None,
        pick_number: int = 1,
    ):
        self._cubeables = cubeables
        self._booster_id = str(uuid.uuid4()) if booster_id is None else booster_id
        self.pick_number: int = pick_number
        self.pick: t.Optional[Pick] = None

    @property
    def cubeables(self) -> Cube:
        return self._cubeables

    @cubeables.setter
    def cubeables(self, cube: Cube) -> None:
        self._cubeables = cube

    @property
    def booster_id(self) -> str:
        return self._booster_id

    def serialize(self) -> serialization_model:
        return {
            'booster_id': self._booster_id,
            'cubeables': self._cubeables.serialize(),
            'pick': self.pick_number,
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> DraftBooster:
        return cls(
            booster_id = value['booster_id'],
            cubeables = Cube.deserialize(value['cubeables'], inflator),
            pick_number = value['pick'],
        )

    def __hash__(self) -> int:
        return hash(self._booster_id)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._booster_id == other._booster_id
        )

    def __repr__(self) -> str:
        return '{}({})'.format(
            self.__class__.__name__,
            self._booster_id,
        )


class PickPoint(object):

    def __init__(
        self,
        draft_id: str,
        global_pick_number: int,
        draft_round: DraftRound,
        pick_number: int,
        booster: DraftBooster,
    ):
        self._draft_id = draft_id
        self._global_pick_number = global_pick_number
        self._draft_round = draft_round
        self._pick_number = pick_number
        self._booster = booster
        self._pick = None

    @property
    def draft_id(self) -> str:
        return self._draft_id

    @property
    def global_pick_number(self) -> int:
        return self._global_pick_number

    @property
    def round(self) -> DraftRound:
        return self._draft_round

    @property
    def pick_number(self) -> int:
        return self._pick_number

    @property
    def booster(self) -> DraftBooster:
        return self._booster

    def set_pick(self, pick: Pick) -> None:
        if self._pick is not None:
            raise ValueError('already picked')
        self._pick = pick

    @property
    def pick(self) -> t.Optional[Pick]:
        return self._pick

    def __hash__(self) -> int:
        return hash((self._draft_id, self.global_pick_number))

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._draft_id == other._draft_id
            and self.global_pick_number == other.global_pick_number
        )

    def __repr__(self):
        return '{}({}, {})'.format(
            self.__class__.__name__,
            self._draft_id,
            self._global_pick_number,
        )
