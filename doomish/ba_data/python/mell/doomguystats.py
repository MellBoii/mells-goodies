"""Module for DoomGuy's stats handler."""
import bascenev1 as bs
import random
from mell.bullet import Bullet
from mell.resources import connect_pos

class DoomGuyStats:
    """The stats of guy of doom.
    Handles health, ammo, HUD, allat."""
    def on_expire(self):
        self._source = None

    def __init__(self, source_actor: DoomGuy):
        self._log_text_node = None
        self._logs = []
        self._source = source_actor
        self._max_hp = 1000
        self.health = self._max_hp
        self._max_armor = 1000
        self.armor = 0
        # HUD layout.
        face_pos = (-0.4, 1.8, 0)
        face_scale = 0.7
        bg_scale = face_scale + 0.2
        # Status icons
        icon_scale = 0.32
        icon_x = -0.7
        icon_y = face_pos[1] + 0.5
        icon_label_scale = icon_scale / 30
        icon_label_math = lambda: (
            icon_x + (icon_scale - 0.1), 
            icon_y - (icon_scale * 0.5), 
            0
        )

        text_scale = 1.0 / 100

        # Common node attributes.
        owner = self._source.node

        def make_image(
            scale: float,
            texture: str,
            *,
            opacity: float = 1.0,
            color: tuple = (1, 1, 1),
        ):
            return bs.newnode(
                'image',
                owner=owner,
                attrs={
                    'scale': (scale, scale),
                    'in_world': True,
                    'texture': bs.gettexture(texture),
                    'opacity': opacity,
                    'color': color,
                },
            )

        def make_text(
            color: tuple,
            *,
            shadow: float = 0.5,
            flatness: float = 0.6,
            scale: float = 0.01,
            maxwidth: int | None = None,
        ):
            attrs = {
                'scale': scale,
                'shadow': shadow,
                'flatness': flatness,
                'color': color,
                'in_world': True,
            }

            if maxwidth is not None:
                attrs['maxwidth'] = maxwidth

            return bs.newnode('text', owner=owner, attrs=attrs)

        def attach(node, offset: tuple[float, float, float]):
            connect_pos(node, owner, offset)

        # Face background.
        self.face_node_bg = make_image(
            bg_scale,
            'softRect',
            opacity=0.5,
            color=owner.color,
        )
        attach(self.face_node_bg, face_pos)

        # Face.
        self.face_node = make_image(
            face_scale,
            'empty',
            opacity=0.7,
        )
        attach(self.face_node, face_pos)


        # Weapon text.
        self._weapon_text_node = make_text(
            (0.9, 0.9, 0.9),
            shadow=0.2,
            flatness=0.8,
            maxwidth=300,
        )
        attach(
            self._weapon_text_node,
            (
                face_pos[0] + face_scale - 0.16,
                face_pos[1],
                0,
            ),
        )


        # Ammo text.
        ammo_y = face_pos[1] - 30 * text_scale

        self._ammo_text_node = make_text(
            (0.8, 0.9, 1),
        )
        attach(
            self._ammo_text_node,
            (
                face_pos[0] + face_scale - 0.16,
                ammo_y,
                0,
            ),
        )

        # Status related icons.
        self.hp_icon_node = make_image(
            icon_scale,
            'powerupHealth',
            color=(1.4, 1.4, 1.4),
        )
        attach(
            self.hp_icon_node, 
            (icon_x, icon_y, 0)
        )

        # Health 
        self._hp_text_node = make_text(
            (0.1, 1, 0),
            scale=icon_label_scale,
        )
        attach(
            self._hp_text_node,
            icon_label_math()
        )
        
        icon_y += icon_scale + 0.03
        
        # Armor
        self.armor_icon_node = make_image(
            icon_scale,
            'powerupShield',
            color=(1.4, 1.4, 1.4),
        )
        attach(
            self.armor_icon_node, 
            (icon_x, icon_y, 0)
        )
        
        self._armor_text_node = make_text(
            (0.2, 0.5, 0.7),
            scale=icon_label_scale,
        )
        attach(
            self._armor_text_node,
            icon_label_math()
        )
        self._update_status_text()
        
    def _update_status_text(self):
        self._armor_text_node.text = f'{int(self.armor / 10)}%'
        self._hp_text_node.text = f'{int(self.health / 10)}%'
        if self._source.node:
            self._source.node.hurt = (
                1.0 - float(self.health) / self._max_hp
            )
    
    def _update_weapon_text(self):
        weapon = self._source._weapon
        name_node = self._weapon_text_node
        ammo_node = self._ammo_text_node
        if not weapon:
            name_node.text = ''
            ammo_node.text = ''
            return
        name_node.text = weapon.wclass.name
        ammo_node.text = f'{weapon.ammo}/{weapon.max_ammo}'
        
    def on_damage(self, amount: int):
        hp = self.health
        # Ok... allow the armor to control how much
        # damage we'll take and how much it'll take too.
        armor = self.armor
        armor_ratio = armor / (armor + hp)
        armor_damage = amount * armor_ratio
        health_damage = amount - armor_damage
        # Apply damage.
        self.armor -= armor_damage
        self.health -= health_damage
        self._update_status_text()
        if self.health <= 0:
            self._source.handlemessage(bs.DieMessage())
    
    def _set_hand_anim_tex(self, tex: str):
        tex = bs.gettexture(tex)
        source = self._source
        self._hand_node.texture = tex
    
    def update_face(self):
        doomguy = self._source
        state = 'face_' + doomguy._face_state
        texture = bs.gettexture(state)
        self.face_node.texture = texture
    
    def remove_log(self, actor: bs.NodeActor):
        self._logs.remove(actor)
        
    def log_info(self, text: str):
        if not self._source.node:
            return
        # Make a text.
        scale = 0.011
        actor = bs.NodeActor(
            bs.newnode(
                'text',
                attrs={
                    'scale': scale,
                    'shadow': 0.2,
                    'flatness': 0.8,
                    'in_world': True,
                    'text': text,
                }
            )
        )
        y = 1.2
        for _ in self._logs:
            y -= 30 * scale
        # Connect somewhere around us.
        connect_pos(
            actor.node,
            self._source.node,
            (0.32, y, 0),
        )
        end_time = 2
        # Animate it in.
        color = (1, 0, 0)
        color_x = bs.Vec3(color) * 3
        bs.animate(
            actor.node,
            'opacity',
            {
                0: 0,
                0.05: 0.9,
                0.2: 0.7,
                end_time - 0.5: 0.7,
                end_time: 0,
            }
        )
        bs.animate_array(
            actor.node,
            'color', 3,
            {
                0: color,
                0.05: color_x,
                0.2: color,
            }
        )
        self._logs.append(actor)
        bs.timer(
            end_time, 
            bs.WeakCallPartial(
                self.remove_log, 
                actor=actor
            )
        )
    
    def show_death_overlay(self):
        node = bs.newnode(
            'image',
            attrs={
                'color': (1, 0, 0),
                'fill_screen': True,
                'texture': bs.gettexture('white'),
                'in_world': False,
            }
        )
        bs.animate(
            node,
            'opacity',
            {
                0: 0,
                0.3: 0.4,
            }
        )

class WeaponInstance:
    """A weapon that the guy of doom holds."""
    def __init__(
        self, 
        weapon: Weapon, 
        source_player: bs.Player | None = None,
    ):
        self.wclass = weapon
        self.ammo = weapon.starting_ammo
        self.max_ammo = weapon.max_ammo
        self._player = source_player
        self._last_shoot_time = -99999999
    
    def spawn_bullets(
        self,
        position: tuple[float],
        velocity: tuple[float],
        rotation: tuple[float] | None = None,
    ):
        extra_bullets = self.wclass.extra_bullets
        damage = self.wclass.avg_damage
        for i in range(extra_bullets + 1):
            if self.ammo <= 0:
                continue
            this_vel = velocity
            # apply some spread if they want it
            spread = self.wclass.bullet_spread
            offset = bs.Vec3(
                random.uniform(-1, 1) * spread,
                random.uniform(-0.5, 0.5) * spread,
                random.uniform(-1, 1) * spread,
            )
            this_vel = this_vel + offset
            bullet_mesh = self.wclass.bullet_mesh
            bullet_texture = self.wclass.bullet_texture
            bullet_scale = self.wclass.bullet_scale
            bullet_class = self.wclass.bullet_type
            bullet = bullet_class(
                mesh=bullet_mesh,
                texture=bullet_texture,
                scale=bullet_scale,
                player=self._player,
            ).autoretain()
            bullet.velocity = this_vel
            bullet.node.position = position
            bullet.damage = damage
            if rotation:
                bullet.node.rotate = rotation
            damage *= 0.8
            self.ammo -= 1