from __future__ import annotations

import typing as t
import uuid

from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator

from magiccube.collections.cube import Cube


class Booster(Serializeable):

    def __init__(self, cubeables: Cube, booster_id: t.Optional[str] = None):
        self._cubeables = cubeables
        self._booster_id = str(uuid.uuid4()) if booster_id is None else booster_id

    @property
    def cubeables(self) -> Cube:
        return self._cubeables

    @property
    def booster_id(self) -> str:
        return self._booster_id

    def serialize(self) -> serialization_model:
        return {
            'booster_id': self._booster_id,
            'cubeables': self._cubeables.serialize(),
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Booster:
        return cls(
            booster_id = value['booster_id'],
            cubeables = Cube.deserialize(value['cubeables'], inflator),
        )

    def __hash__(self) -> int:
        return hash(self._booster_id)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._booster_id == other._booster_id
        )
