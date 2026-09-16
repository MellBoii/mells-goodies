"""Module for the player doomguy thing."""
from __future__ import annotations

import bascenev1 as bs
import babase as ba
import _babase as _ba
import math
import random
import weakref
from mell.factory import (
    MellFactory, 
    FootingMessage, 
    InteractedMessage, 
    AskedIfForceInteractionsMessage,
)
from mell.resources import look_at, euler_to_quaternion, connect_pos, get_direction
from mell.weapons import REGISTERED_WEAPONS
from mell.doomguystats import DoomGuyStats, WeaponInstance
from bascenev1lib.gameutils import SharedObjects
from bascenev1lib.actor.spazfactory import SpazFactory
from bascenev1lib.actor.powerupbox import PowerupBoxFactory, PowerupBox

class DoomGuy(bs.Actor):
    """A guy of doom who can move 
    around and shoot or 
    interact with things."""
    def on_expire(self):
        self._stats = None
        
    def __init__(
        self,
        color,
        highlight,
        character,
        player: bs.Player,
        position: tuple[float] = (0, 0, 0),
    ):
        super().__init__()
        # Unused.
        del color, highlight, character
        self._footing = False
        self._dead = False
        self._source_player = player
        self._weapons = {}
        self._last_weapon = None
        self._weapon = None
        self._weapon_index = 0
        self._input_x = 0
        self._input_y = 0
        self._last_input_x = 1
        self._last_input_y = 1
        self._time_held_attack = 0
        self._last_face_update_time = -99999
        self._last_hit_time = 0
        self._last_player_hit_by = None
        self._shoot_pressed = False
        self._celebrating = False
        self._aim_offset = bs.Vec3(0, 0.4, 1)
        self._last_shoot_time = -99999999
        shared = SharedObjects.get()
        mf = MellFactory.get()
        character = 'Alikisser'
        spazfac = SpazFactory.get()
        media = spazfac.get_media(character)
        # Make a nice lil spaz.
        pam = PowerupBoxFactory.get().powerup_accept_material
        self.node = bs.newnode(
            'spaz',
            delegate=self,
            attrs={
                'materials': (shared.object_material, pam),
                'name': player.getname(),
                'jump_sounds': media['jump_sounds'],
                'attack_sounds': media['attack_sounds'],
                'impact_sounds': media['impact_sounds'],
                'death_sounds': media['death_sounds'],
                'pickup_sounds': media['pickup_sounds'],
                'fall_sounds': media['fall_sounds'],
                'color_texture': media['color_texture'],
                'color_mask_texture': media['color_mask_texture'],
                'head_mesh': media['head_mesh'],
                'torso_mesh': media['torso_mesh'],
                'pelvis_mesh': media['pelvis_mesh'],
                'upper_arm_mesh': media['upper_arm_mesh'],
                'forearm_mesh': media['forearm_mesh'],
                'hand_mesh': media['hand_mesh'],
                'upper_leg_mesh': media['upper_leg_mesh'],
                'lower_leg_mesh': media['lower_leg_mesh'],
                'toes_mesh': media['toes_mesh'],
                'style': spazfac.get_style(character),
            }
        )
        # Teleport it and give it some 
        # footing so it can run.
        self.node.handlemessage('footing', 1)
        self.node.handlemessage(
            'stand',
            position[0], 
            position[1], 
            position[2],
            0,
        )
        # Give it a color.
        color = player.color
        self.node.color = color
        self.node.name_color = color
        self.node.highlight = color
        # Other nodes.
        self.crosshair = bs.newnode(
            'image',
            owner=self.node,
            attrs={
                'scale': (0.2, 0.2),
                'in_world': True,
                'color': color,
                'texture': bs.gettexture('circle')
            }
        )
        self._weapon_node = bs.newnode(
            'prop',
            attrs={
                'body': 'box',
                'mesh_scale': 0.6,
                'body_scale': 0.1,
                'materials': (mf.no_collide_mat,),
            }
        )
        # Ok; let's tell the activity to tell us to
        # tick when it wants to.
        self.getactivity().add_tick_callback(
            bs.WeakCallPartial(self.do_tick)
        )
        self._stats = DoomGuyStats(self)
        self._default_rotate_mult = self._rotate_mult = 1.4
        self._current_rotate_increment = 0
        wpns = REGISTERED_WEAPONS
        for weapon in (
            wpns['pistol'],
            wpns['machinegun'],
            wpns['shotgun'],
            wpns['rocket'],
            wpns['grenade'],
        ):
            self.add_weapon(weapon)
        self.index_weapon(0)
        self.set_face_state('normal')
    
    def do_tick(self):
        if not self.node or not self.crosshair:
            return
        p_pos = bs.Vec3(self.node.position)
        # fix replays
        self.node.handlemessage('footing', 1)
        
        input_x = self.node.move_left_right
        input_z = -self.node.move_up_down

        offset = bs.Vec3(
            self._aim_offset.x + input_x,
            self._aim_offset.y,
            self._aim_offset.x + input_z,
        )

        c_pos = p_pos + offset
        w_pos = p_pos + offset * 0.5
        w_pos = w_pos + bs.Vec3(0, 0.35, 0)
        self.crosshair.position = c_pos
        # If we have a interactable, make our cursor
        # reflect that
        if self.get_interactable():
            self.crosshair.texture = bs.gettexture('star')
        else:
            self.crosshair.texture = bs.gettexture('circle')
        if self._weapon_node:
            self._weapon_node.position = w_pos
            self._weapon_node.rotate = look_at(p_pos, c_pos)

        # Camera.
        if self._dead:
            cam_yoffs = 0
        else:
            cam_yoffs = 0.9
        t_pos = bs.Vec3(self.node.torso_position)
        direction = bs.Vec3(offset.x, 0, offset.z)

        if direction.length() > 0:
            direction = direction.normalized()
        # Handle shooting.
        if self._shoot_pressed:
            if not self._weapon:
                return
            self._time_held_attack += 0.1
            cooldown = self._weapon.wclass.shoot_cooldown
            current_time = bs.time() - self._weapon._last_shoot_time
            if current_time > cooldown:
                self.shoot_weapon()
                self._weapon._last_shoot_time = bs.time()
        else:
            self._time_held_attack = 0
        # Face state.
        # Have some cooldown so we don't update TOO fast.
        if bs.time() - self._last_face_update_time > 0.4:
            self._last_face_update_time = bs.time()
            if self._dead:
                self.set_face_state('dead')
            elif self._celebrating:
                self.set_face_state('evil')
            elif self._time_held_attack >= 5:
                self.set_face_state('kill')
            elif bs.time() - self._last_hit_time < 0.4:
                self.set_face_state('kill')
            else:
                states = [
                    'normal_r',
                    'normal_l',
                ]
                # FIXME: add chance weighing??
                for _ in range(5):
                    states.append('normal')
                state = random.choice(states)
                self.set_face_state(state)
        
    def move_x(self, value: float):
        if not self.node:
            return
        self.node.move_left_right = value
        self._input_x = value

    def move_y(self, value: float):
        if not self.node:
            return
        self.node.move_up_down = value
        self._input_y = value
    
    def shoot_press(self):
        self._shoot_pressed = True
    
    def shoot_release(self):
        self._shoot_pressed = False
    
    def shoot_weapon(self):
        if self._dead or not self.node:
            return
        if self._weapon.ammo <= 0:
            bs.getsound('click01').play(
                position=self.node.position
            )
            return

        input_x = self.node.move_left_right
        input_z = -self.node.move_up_down
        if input_x == 0 and input_z == 0:
            input_x += 1

        offset = bs.Vec3(
            self._aim_offset.x + input_x,
            self._aim_offset.y,
            self._aim_offset.x + input_z,
        )
        pos = bs.Vec3(self.node.torso_position)
        direction = bs.Vec3(offset.x, 0, offset.z)
        rotation = look_at(pos, direction)
        velocity = direction
        # Allow controlling speed 
        # for slower projectiles (like rockets).
        weapon_speed = self._weapon.wclass.bullet_speed
        velocity = (velocity * 10) * weapon_speed
        self._weapon.spawn_bullets(
            position=pos,
            velocity=velocity,
            rotation=rotation,
        )
        self._stats._update_weapon_text()
        # Send some effects 'round for that EXTRA punchiness.
        bs.emitfx(
            position=pos + direction,
            velocity=direction,
            count=random.randrange(20, 30),
            scale=0.6,
            spread=0.3,
            chunk_type='spark',
        )
        flash_color = (1, 1, 0)
        light = bs.newnode(
            'light',
            attrs={
                'position': pos,
                'radius': 0.7,
                'height_attenuated': False,
                'color': flash_color,
            },
        )
        bs.animate(
            light, 
            'intensity',
            {
                0: 0,
                0.1: 3,
            }
        )
        bs.timer(0.1, light.delete)
        # flash = bs.newnode(
            # 'flash',
            # attrs={
                # 'position': pos,
                # 'size': 0.17,
                # 'color': flash_color,
            # },
        # )
        # bs.timer(0.06, flash.delete)
        # Make a sound so we're not quiet.
        shoot_sound = self._weapon.wclass.shoot_sound
        bs.getsound(shoot_sound).play(
            position=pos
        )
    
    def set_face_state(self, state: str):
        self._face_state = state
        self._stats.update_face()
    
    def _parse_triggers(self, triggers: list):
        for trigger in triggers:
            if trigger[0] == 'timer':
                bs.timer(
                    trigger[1],
                    bs.WeakCallPartial(
                        self._parse_triggers,
                        trigger[2]
                    )
                )
            elif trigger[0] == 'set':
                setattr(self._weapon, trigger[1], trigger[2])
    
    def on_animation_finish(self, animation: str):
        wclass = self._weapon.wclass
        cooldown = wclass.shoot_cooldown
        triggers = wclass.animation_finish_triggers
        triggers = triggers.get(animation, [])
        self._parse_triggers(triggers)
        
    def _play_voiceline(self, voiceline: str):
        if not self.node:
            return
        self._voiceline = bs.NodeActor(
            bs.newnode(
                'sound',
                attrs={
                    'sound': bs.getsound(voiceline),
                    'positional': True,
                    'position': self.node.position,
                    'volume': 1,
                    'loop': False,
                }
            )
        )
    
    def get_interactable(self):
        chosen = None
        shared = SharedObjects.get()
        for node in bs.getnodes():
            position = getattr(node, 'position', ())
            # Wanna make sure interactables are ALWAYS 3D.
            if len(position) != 3:
                continue
            # Alright, ask this bugger if they want to force
            # interactions, and if they do not; just check if they
            # can be interacted with normally.
            forced_interactions = node.handlemessage(
                AskedIfForceInteractionsMessage()
            )
            if not forced_interactions:
                # Only most grabbable props 
                # are interactable.
                if node.getnodetype() not in ['flag', 'bomb', 'prop']:
                    continue
                if (
                    node.getnodetype() == 'prop'
                    and shared.object_material not in node.materials
                ):
                    continue
            # Get how far they are.
            n_pos = bs.Vec3(position)
            our_pos = bs.Vec3(self.crosshair.position)
            dist = (n_pos - our_pos).length()
            dist_min = 0.9
            # Close enough; let's set them as 
            # our interactable.
            if dist < dist_min:
                chosen = node
        return chosen

    def interact(self):
        if self._dead:
            return
        interacted = False
        interactable = self.get_interactable()
        # Throw anything if we were holding it.
        if self.node.hold_node:
            self.punch()
            interacted = True
        if interactable and not interacted:
            dele = interactable.getdelegate(bs.Actor)
            # Ask the interactable if they can handle it.
            interacted = interactable.handlemessage(
                InteractedMessage(weakref.ref(self))
            )
            # If not, try grabbing it
            if not interacted:
                self.node.hold_node = interactable
                interacted = True
        if not interacted:
            self._play_voiceline('noway')
    
    def index_weapon(self, value: int):
        self._weapon_index = (
            self._weapon_index + value 
        ) % len(self._weapons)
        self._last_weapon = self._weapon
        vals = list(self._weapons.keys())
        chosen = vals[self._weapon_index]
        self._weapon = self._weapons[chosen]
        if self._weapon_node:
            # vanilla compat toggle
            # mesh = 'neoSpazHead'
            # tex = 'white'
            mesh = chosen.inworld_mesh
            tex = chosen.inworld_texture
            self._weapon_node.mesh = bs.getmesh(mesh)
            self._weapon_node.color_texture = bs.gettexture(tex)
        self._stats._update_weapon_text()
    
    def add_weapon(self, weapon: Weapon):
        # If this weapon already exists for us, give us its' ammo
        if weapon in self._weapons:
            instance = self._weapons[weapon]
            instance.ammo += weapon.starting_ammo
            # Hit the max ammo? Reset to it.
            if instance.ammo >= weapon.max_ammo:
                instance.ammo = weapon.max_ammo
        # Any other case, just add it to us
        else:
            self._weapons[weapon] = WeaponInstance(
                weapon,
                source_player=self._source_player,
            )
            instance = self._weapons[weapon]
        # We have no on-hand weapon? Make it the one then.
        self._weapon = instance
        message = weapon.special_message or f'Obtained a {weapon.name}'
        self._stats.log_info(message)
    
    def get_death_points(self, how: bs.DeathType):
        del how
        return (10, 1)
    
    def handle_death(self, msg):
        if self._dead:
            return
        self._play_voiceline('death')
        if self._weapon_node:
            self._weapon_node.delete()
        self.node.dead = True
        bs.timer(2, self.node.delete)
        self._dead = True
        
        # Report player deaths to the game.
        # Was this player attacked before death?
        was_attacked_recently = (
            self._last_player_hit_by
            and bs.time() - self._last_hit_time < 4.0
        )
        # Leaving the game doesn't count as a kill *unless*
        # someone does it intentionally while being attacked.
        left_game_cleanly = (
            msg.how is bs.DeathType.LEFT_GAME 
            and not was_attacked_recently
        )

        killed = not (msg.immediate or left_game_cleanly)

        activity = self._activity()

        player = self._source_player
        if not killed:
            killerplayer = None
        else:
            # Otherwise, if they were attacked by someone in the
            # last few seconds, that person is the killer.
            # Otherwise it was a suicide.
            # FIXME: Currently disabling suicides in Co-Op since
            #  all bot kills would register as suicides; need to
            #  change this from last_player_attacked_by to
            #  something like last_actor_attacked_by to fix that.
            if was_attacked_recently:
                killerplayer = self._last_player_hit_by
            else:
                # ok, call it a suicide unless we're in co-op
                if activity is not None and not isinstance(
                    activity.session, bs.CoopSession
                ):
                    killerplayer = player
                else:
                    killerplayer = None

        # We should never wind up with a dead-reference here;
        # we want to use None in that case.
        assert killerplayer is None or killerplayer

        # Only report if both the player and the activity still exist.
        if killed and activity is not None and player:
            activity.handlemessage(
                bs.PlayerDiedMessage(
                    player, killed, killerplayer, msg.how
                )
            )
    
    def punch(self):
        self.node.punch_pressed = True
        def set():
            self.node.punch_pressed = False
        bs.timer(0, set)
        
    def run(self, value: float):
        self.node.run = value + 0.15
    
    def exists(self):
        return bool(self.node)
    
    def is_alive(self):
        return not self._dead
        
    def handlemessage(self, msg):
        if isinstance(msg, FootingMessage):
            self._footing = msg.state
        elif isinstance(msg, bs.DieMessage):
            self.handle_death(msg)
        elif isinstance(msg, bs.OutOfBoundsMessage):
            self.handlemessage(bs.DieMessage())
        elif isinstance(msg, bs.HitMessage):
            if self._dead:
                return
            impact_scale = 1
            damage_scale = 0.20
            mag = msg.magnitude
            velocity_mag = msg.velocity_magnitude
            self._play_voiceline('hurt')
            self._last_hit_time = bs.time()
            self._last_player_hit_by = msg.get_source_player(bs.Player)
            if msg.flat_damage:
                damage = msg.flat_damage * impact_scale
            else:
                self.node.handlemessage(
                    'impulse',
                    msg.pos[0],
                    msg.pos[1],
                    msg.pos[2],
                    msg.velocity[0],
                    msg.velocity[1],
                    msg.velocity[2],
                    mag,
                    velocity_mag,
                    msg.radius,
                    0, # change to 0 for impulse
                    msg.force_direction[0],
                    msg.force_direction[1],
                    msg.force_direction[2],
                )
                damage = damage_scale * self.node.damage
            if damage > 0:
                # If we're holding something, drop it.
                if self.node.hold_node:
                    self.node.hold_node = None
            # Play punch impact sound based on damage if it was a punch.
            if msg.hit_type == 'punch':
                # Let's always add in a super-punch sound with boxing
                # gloves just to differentiate them.
                if msg.hit_subtype == 'super_punch':
                    SpazFactory.get().punch_sound_stronger.play(
                        1.0,
                        position=self.node.position,
                    )
                if damage >= 500:
                    sounds = SpazFactory.get().punch_sound_strong
                    sound = sounds[random.randrange(len(sounds))]
                elif damage >= 100:
                    sound = SpazFactory.get().punch_sound
                else:
                    sound = SpazFactory.get().punch_sound_weak
                sound.play(1.0, position=self.node.position)

                # Throw up some chunks.
                assert msg.force_direction is not None
                bs.emitfx(
                    position=msg.pos,
                    velocity=(
                        msg.force_direction[0] * 0.5,
                        msg.force_direction[1] * 0.5,
                        msg.force_direction[2] * 0.5,
                    ),
                    count=min(10, 1 + int(damage * 0.0025)),
                    scale=0.3,
                    spread=0.03,
                )

                bs.emitfx(
                    position=msg.pos,
                    chunk_type='sweat',
                    velocity=(
                        msg.force_direction[0] * 1.3,
                        msg.force_direction[1] * 1.3 + 5.0,
                        msg.force_direction[2] * 1.3,
                    ),
                    count=min(30, 1 + int(damage * 0.04)),
                    scale=0.9,
                    spread=0.28,
                )

                # Momentary flash.
                hurtiness = damage * 0.003
                punchpos = (
                    msg.pos[0] + msg.force_direction[0] * 0.02,
                    msg.pos[1] + msg.force_direction[1] * 0.02,
                    msg.pos[2] + msg.force_direction[2] * 0.02,
                )
                flash_color = (1.0, 0.8, 0.4)
                light = bs.newnode(
                    'light',
                    attrs={
                        'position': punchpos,
                        'radius': 0.12 + hurtiness * 0.12,
                        'intensity': 0.3 * (1.0 + 1.0 * hurtiness),
                        'height_attenuated': False,
                        'color': flash_color,
                    },
                )
                bs.timer(0.06, light.delete)

                flash = bs.newnode(
                    'flash',
                    attrs={
                        'position': punchpos,
                        'size': 0.17 + 0.17 * hurtiness,
                        'color': flash_color,
                    },
                )
                bs.timer(0.06, flash.delete)
            if msg.hit_type == 'impact':
                assert msg.force_direction is not None
                bs.emitfx(
                    position=msg.pos,
                    velocity=(
                        msg.force_direction[0] * 2.0,
                        msg.force_direction[1] * 2.0,
                        msg.force_direction[2] * 2.0,
                    ),
                    count=min(10, 1 + int(damage * 0.01)),
                    scale=0.4,
                    spread=0.1,
                )
            self.node.handlemessage('flash')
            self._stats.on_damage(damage)
        elif isinstance(msg, bs.CelebrateMessage):
            self._celebrating = True
            if self.node:
                self.node.handlemessage('celebrate', int(msg.duration * 1000))
            bs.timer(msg.duration, 
                lambda: setattr(
                    self, 
                    '_celebrating', 
                    False,
                )
            )
        elif isinstance(msg, bs.PowerupMessage):
            type = msg.poweruptype
            if type == 'health':
                self._stats.health = self._stats._max_hp
                self._stats._update_status_text()
                self._stats.log_info('Healed up health')
            elif type == 'shield':
                self._stats.armor = self._stats._max_armor
                self._stats._update_status_text()
                self._stats.log_info('Filled up armor')
            else:
                # Ok... let's add some random ammo 
                # based on how much they want maximum.
                weapon = self._weapon
                max = weapon.max_ammo
                amount = random.randint(
                    int(max * 0), 
                    int(max * 0.15),
                )
                weapon.ammo += amount
                if weapon.ammo >= max:
                    weapon.ammo = max
                self._stats._update_weapon_text()
                self._stats.log_info(f'Got {amount} ammo for {weapon.wclass.name}')
            if msg.sourcenode:
                msg.sourcenode.handlemessage(bs.PowerupAcceptMessage())
            return True
        else:
            return super().handlemessage(msg)
        return None
    
    def stop(self, value: int):
        self.node.hold_position_pressed = bool(value)
    
    def connect_controls_to_player(self):
        player = self._source_player
        player.resetinput()
        player.assigninput(bs.InputType.LEFT_RIGHT, self.move_x)
        player.assigninput(bs.InputType.UP_DOWN, self.move_y)
        # Gonna be hard working with only 4 buttons...
        player.assigninput(bs.InputType.PUNCH_PRESS, self.shoot_press)
        player.assigninput(bs.InputType.PUNCH_RELEASE, self.shoot_release)
        player.assigninput(bs.InputType.BOMB_PRESS, lambda: self.index_weapon(1))
        player.assigninput(bs.InputType.JUMP_PRESS, lambda: self.stop(1))
        player.assigninput(bs.InputType.JUMP_RELEASE, lambda: self.stop(0))
        player.assigninput(bs.InputType.PICK_UP_PRESS, self.interact)
        player.assigninput(bs.InputType.RUN, self.run)