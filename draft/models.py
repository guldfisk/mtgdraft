from __future__ import annotations

import typing as t
import uuid

from magiccube.collections.cube import Cube
from magiccube.collections.cubeable import Cubeable
from yeetlong.multiset import Multiset

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator

from magiccube.collections import cubeable
from magiccube.laps.purples.purple import Purple
from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap


_deserialize_type_map = {
    'Trap': Trap,
    'Ticket': Ticket,
    'Purple': Purple,
}


class Booster(Cube):

    def __init__(self, booster_id: uuid.UUID, cubeables: t.Optional[t.Iterable[Cubeable]] = None):
        super().__init__(cubeables)
        self._booster_id = booster_id

    # def __init__(self, cubeables: t.Iterable[cubeable]):
    #     self._cubeables = Multiset(cubeables)
    #     self._booster_id = uuid.uuid4()

    @property
    def cubeables(self) -> Multiset[cubeable]:
        return self._cubeables

    @property
    def booster_id(self) -> uuid.UUID:
        return self._booster_id

    def serialize(self) -> serialization_model:
        return {
            **super().serialize(),
            'booster_id': str(self._booster_id),
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Booster:
        pass

    # def serialize(self) -> serialization_model:
    #     return [
    #         _cubeable.serialize()
    #         if isinstance(_cubeable, Serializeable) else
    #         _cubeable
    #         for _cubeable in
    #         self._cubeables
    #     ]
    #
    # @classmethod
    # def deserialize(cls, value: serialization_model, inflator: Inflator) -> Booster:
    #     return cls(
    #         inflator.inflate(Printing, _value)
    #         if isinstance(_value, int) else
    #         _deserialize_type_map[_value['type']].deserialize(_value, inflator)
    #         for _value in
    #         value
    #     )

    def __hash__(self) -> int:
        return hash(self._booster_id)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._booster_id == other._booster_id
        )
