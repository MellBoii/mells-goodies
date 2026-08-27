"""Factory for mell related stuff."""
from typing import Any
from bascenev1lib.gameutils import SharedObjects
import bascenev1 as bs
from dataclasses import dataclass

@dataclass
class FootingMessage:
	state: bool

@dataclass
class InteractedMessage:
    """A message that a DoomGuy
    has interacted with something."""
    who: Any

class AskedIfForceInteractionsMessage:
    """A message where a DoomGuy asks
    if a object wants to force interactions.
    So even light nodes, terrain, etc.. can be interacted with"""

class BulletHitMessage:
    pass

class MellFactory:
    """A factory of materials."""
    _STORENAME = bs.storagename()
    def __init__(self):
        activity = bs.getactivity()
        if self._STORENAME in activity.customdata:
            raise RuntimeError(
                'Use MellFactory.get() to fetch the'
                ' shared instance for this activity.'
            )
        shared = SharedObjects.get()
        #: Material that collides with nothing.
        mat = self.no_collide_mat = bs.Material()
        mat.add_actions(('modify_part_collision', 'collide', False))
        #: Material for bullets.
        mat = self.bullet_material = bs.Material()
        mat.add_actions(
            actions=(
                ('message', 'our_node', 'at_connect', BulletHitMessage()),
            ),
        )
        mat.add_actions(
            conditions=(
                ('we_are_younger_than', 10),
                'and',
                ('they_are_different_node_than_us',),
            ),
            actions=('modify_node_collision', 'collide', False),
        )
        

    @classmethod
    def get(cls):
        """Fetch/create the instance of
        this class for the current activity."""
        activity = bs.getactivity()
        us = activity.customdata.get(cls._STORENAME)
        if us is None:
            us = MellFactory()
            activity.customdata[cls._STORENAME] = us
        return us