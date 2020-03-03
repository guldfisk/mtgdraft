from __future__ import annotations

import typing as t
import uuid

from dataclasses import dataclass

from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator

from magiccube.collections.cube import Cube


@dataclass
class DraftRound(object):
    pack: int
    clockwise: bool


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
