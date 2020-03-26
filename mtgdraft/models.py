from __future__ import annotations

import typing as t
import uuid
from abc import abstractmethod

from dataclasses import dataclass

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.strategies.raw import RawStrategy
from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator

from magiccube.laps.purples.purple import Purple
from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from magiccube.collections.cubeable import Cubeable
from magiccube.collections.cube import Cube


def _serialize_cubeable(cubeable: Cubeable) -> t.Any:
    return cubeable.id if isinstance(cubeable, Printing) else RawStrategy.serialize(cubeable)


@dataclass
class DraftRound(object):
    pack: int
    clockwise: bool


class Pick(Serializeable):
    _deserialize_type_map = {
        'Trap': Trap,
        'Ticket': Ticket,
        'Purple': Purple,
    }

    @classmethod
    def _deserialize_cubeable(cls, cubeable: serialization_model, inflator: Inflator) -> Cubeable:
        return (
            inflator.inflate(Printing, cubeable)
            if isinstance(cubeable, int) else
            cls._deserialize_type_map[cubeable['type']].deserialize(cubeable, inflator)
        )

    @property
    @abstractmethod
    def added_cubeables(self) -> t.Iterable[Cubeable]:
        pass

    @abstractmethod
    def serialize(self) -> serialization_model:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        pass

    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        pass


class SinglePickPick(Pick):

    def __init__(self, cubeable: Cubeable):
        self._cubeable = cubeable

    @property
    def added_cubeables(self) -> t.Iterable[Cubeable]:
        return self._cubeable,

    @property
    def cubeable(self) -> Cubeable:
        return self._cubeable

    def serialize(self) -> serialization_model:
        return _serialize_cubeable(self._cubeable)

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        return cls(cls._deserialize_cubeable(value, inflator))

    def __hash__(self) -> int:
        return hash(self._cubeable)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._cubeable == other._cubeable
        )


class BurnPick(Pick):

    def __init__(self, pick: Cubeable, burn: t.Optional[Cubeable]):
        self._pick = pick
        self._burn = burn

    @property
    def added_cubeables(self) -> t.Iterable[Cubeable]:
        return self._pick,

    @property
    def pick(self) -> Cubeable:
        return self._pick

    @property
    def burn(self) -> t.Optional[Cubeable]:
        return self._burn

    def serialize(self) -> serialization_model:
        return {
            'pick': _serialize_cubeable(self._pick),
            'burn': None if self._burn is None else _serialize_cubeable(self._burn),
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        return cls(
            cls._deserialize_cubeable(value['pick'], inflator),
            None if value['burn'] is None else cls._deserialize_cubeable(value['burn'], inflator),
        )

    def __hash__(self) -> int:
        return hash((self._pick, self._burn))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._pick == other._pick
            and self._burn == other._burn
        )


class Booster(Serializeable):

    def __init__(
        self,
        cubeables: Cube,
        booster_id: t.Optional[str] = None,
        pick: int = 1,
    ):
        self._cubeables = cubeables
        self._booster_id = str(uuid.uuid4()) if booster_id is None else booster_id
        self._pick = pick

    @property
    def cubeables(self) -> Cube:
        return self._cubeables

    @cubeables.setter
    def cubeables(self, cube: Cube) -> None:
        self._cubeables = cube

    @property
    def booster_id(self) -> str:
        return self._booster_id

    @property
    def pick(self) -> int:
        return self._pick

    @pick.setter
    def pick(self, value: int) -> None:
        self._pick = value

    def serialize(self) -> serialization_model:
        return {
            'booster_id': self._booster_id,
            'cubeables': self._cubeables.serialize(),
            'pick': self._pick,
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Booster:
        return cls(
            booster_id = value['booster_id'],
            cubeables = Cube.deserialize(value['cubeables'], inflator),
            pick = value['pick'],
        )

    def __hash__(self) -> int:
        return hash(self._booster_id)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._booster_id == other._booster_id
        )
