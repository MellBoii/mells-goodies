"""Module for all weapons and base class."""
from __future__ import annotations
# Quick lesson on triggers;
# Assume a tuple () is somewhat like a code.
# 'set' allows you to specific attributes about the weapon instance. ('set', 'allow_shooting', False)
# 'timer' schedules a timer to evaluate a trigger. ('timer', 0.5, ('animation', 'jam'))
# Hopefully I myself should stick to this.

from typing import Literal, override, Any
from mell.bullet import *
import bascenev1 as bs
import random
REGISTERED_WEAPONS = {}

def register(cls):
    if cls not in REGISTERED_WEAPONS:
        REGISTERED_WEAPONS[cls.weapon_id] = cls
    return cls

class Weapon:
    """A class representing a weapon 
    and its statistics."""
    weapon_id: str = 'weapon'
    name: str = 'Weapon'
    #: Ammo stats.
    max_ammo: int = 100
    starting_ammo: int = 50
    #: Define how many extra bullets should shoot
    #: out with the first.
    extra_bullets: int = 0
    #: Spread of extra bullets.
    bullet_spread: float = 0
    #: Scale of bullets.
    bullet_scale: float = 0.8
    #: Speed multiplier of the bullets.
    bullet_speed: float = 0.9
    #: What type of bullet will be shot out.
    bullet_type: Bullet = Bullet
    #: How much damage this does in average.
    #: Will not be accurate due to appliance of randomness
    #: or nerfing for extra bullets. Change accordingly.
    avg_damage: int = 50
    #: In world appearance.
    inworld_mesh: str = 'box'
    inworld_texture: str = 'white'
    bullet_mesh: str = 'bomb'
    bullet_texture: str = 'yellow'
    #: Sound that plays when the weapon is shot.
    shoot_sound: str = 'explosion01'
    #: Cooldown that the weapon can be shot after.
    shoot_cooldown: float = 0.5
    #: Special message that pops up when grabbing this weapon.
    special_message: str | None = None

@register
class Shotgun(Weapon):
    weapon_id = 'shotgun'
    name = 'Shotgun'
    #: Ammo stats.
    max_ammo = 350
    starting_ammo = 100
    extra_bullets = 6
    bullet_spread = 0.5
    bullet_scale = 0.6
    bullet_speed = 0.8
    avg_damage = 60
    shoot_sound = 'shotgun'
    shoot_cooldown = 0.6
    inworld_mesh = 'shotgun'
    inworld_texture = 'shotgun_tex'

@register
class Pistol(Weapon):
    weapon_id = 'pistol'
    name = 'Pistol'
    max_ammo = 120
    starting_ammo = 40
    extra_bullets = 0
    bullet_scale = 0.7
    bullet_speed = 0.7
    avg_damage = 30
    shoot_sound = 'pistol'
    shoot_cooldown = 0.3
    inworld_mesh = 'pistol'
    inworld_texture = 'pistol_tex'

@register
class MachineGun(Weapon):
    weapon_id = 'machinegun'
    name = 'Machine Gun'
    max_ammo = 600
    starting_ammo = 140
    extra_bullets = 0
    bullet_spread = 0.1
    bullet_scale = 0.8
    bullet_speed = 0.7
    avg_damage = 5
    shoot_sound = 'plasmagun'
    shoot_cooldown = 0.04
    inworld_mesh = 'pistol'
    inworld_texture = 'pistol_tex'

@register
class RocketLauncher(Weapon):
    weapon_id = 'rocket'
    name = 'Rocket Launcher'
    max_ammo = 20
    starting_ammo = 3
    extra_bullets = 0
    bullet_spread = 0.1
    bullet_scale = 0.9
    bullet_speed = 0.35
    bullet_type = RocketBullet
    shoot_sound = 'plasmagun'
    shoot_cooldown = 3
    inworld_mesh = 'shotgun'
    inworld_texture = 'shotgun_tex'

@register
class GrenadeLauncher(Weapon):
    weapon_id = 'grenade'
    name = 'Grenade Launcher'
    max_ammo = 60
    starting_ammo = 6
    extra_bullets = 0
    bullet_spread = 0
    bullet_scale = 0.9
    bullet_speed = 0.006
    bullet_type = GrenadeBullet
    shoot_sound = 'plasmagun'
    shoot_cooldown = 1
    inworld_mesh = 'shotgun'
    inworld_texture = 'shotgun_tex'