from __future__ import annotations

import typing as t
import uuid
from abc import abstractmethod

from dataclasses import dataclass

from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator

from magiccube.collections.cubeable import Cubeable, serialize_cubeable, deserialize_cubeable
from magiccube.collections.cube import Cube


@dataclass
class DraftRound(object):
    pack: int
    clockwise: bool


class Pick(Serializeable):

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


class SinglePickPick(Pick):

    def __init__(self, cubeable: Cubeable):
        self._cubeable = cubeable

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


class Booster(Serializeable):

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
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Booster:
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
