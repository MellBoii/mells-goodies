"""Boulet"""
import bascenev1 as bs
import random
from mell.factory import MellFactory, BulletHitMessage
from bascenev1lib.gameutils import SharedObjects
from bascenev1lib.actor.bomb import Blast

class Bullet(bs.Actor):
    override_bullet_hit = False
    def __init__(
        self, 
        scale: float,
        mesh: str = 'bomb',
        texture: str = 'white',
        player: bs.Player | None = None,
    ):
        super().__init__()
        self.damage = 0
        self.velocity = (0, 0, 0)
        mf = MellFactory.get()
        shared = SharedObjects.get()
        self._player = player
        self.node = bs.newnode(
            'prop',
            delegate=self,
            attrs={
                'body': 'sphere',
                'mesh': bs.getmesh(mesh),
                'color_texture': bs.gettexture(texture),
                'body_scale': scale,
                'mesh_scale': scale - 0.3,
                'gravity_scale': 0.001,
                'shadow_size': scale - 0.6,
                'materials': (mf.bullet_material, shared.object_material),
            }
        )
        # Ok; let's tell the activity to tell us to
        # tick when it wants to.
        self.getactivity().add_tick_callback(
            bs.WeakCallPartial(self.do_tick)
        )
        self.post_init()
    
    def post_init(self):
        pass
    
    def on_hit_do(self):
        raise ValueError('_override_bullet_hit was passed but didn\'t override _on_hit_do')
    
    def do_tick(self):
        if not self.node:
            return
        vel = self.velocity
        nvel = self.node.velocity
        pos = self.node.position
        x, y, z = vel
        # fmcl
        if x or y or z:
            self.node.handlemessage(
                'impulse',
                pos[0], pos[1], pos[2],
                vel.x, vel.y, vel.z,
                100,
                100,
                0,
                1,
                vel.x, vel.y, vel.z,
            )
    
    def exists(self):
        return bool(self.node)
    
    def handlemessage(self, msg):
        if isinstance(msg, BulletHitMessage):
            try:
                node = bs.getcollision().opposingnode
            except:
                node = None
            if not node or not self.node:
                return
            damage = self.damage
            # Alright, hit the other node.
            # OR; do a callback if we have it.
            if self.override_bullet_hit:
                self.on_hit_do(node)
            else:
                node.handlemessage(
                    bs.HitMessage(
                        pos=self.node.position,
                        velocity=self.node.velocity,
                        radius=0,
                        magnitude=damage,
                        velocity_magnitude=damage,
                        hit_type='bullet',
                        source_player=self._player,
                    )
                )
                self.handlemessage(bs.DieMessage())
        elif isinstance(msg, bs.DieMessage):
            if self.node:
                # Emit some sparks for more effect.
                bs.emitfx(
                    position=self.node.position,
                    velocity=self.node.velocity,
                    count=random.randrange(5, 10),
                    scale=0.7,
                    spread=0.01,
                    chunk_type='spark',
                )
                self.node.delete()
            self.getactivity().remove_tick_callback(
                bs.WeakCallPartial(self.do_tick)
            )
        elif isinstance(msg, bs.OutOfBoundsMessage):
            self.handlemessage(bs.DieMessage())
        else:
            return super().handlemessage(msg)
        return None


class RocketBullet(Bullet):
    override_bullet_hit = True
    def on_hit_do(self, node: bs.Node):
        Blast(
            position=self.node.position,
            velocity=self.node.velocity,
            blast_radius=2.1,
            source_player=self._player
        ).autoretain()
        self.handlemessage(bs.DieMessage())

class GrenadeBullet(Bullet):
    override_bullet_hit = True
    def post_init(self):
        self.node.gravity_scale = 0.8
        bs.timer(0.1, self._reset_velocity)
    
    def _reset_velocity(self):
        self.velocity = bs.Vec3(0, 0, 0)
        
    def on_hit_do(self, node: bs.Node):
        bs.timer(2, bs.WeakCallPartial(self._explode))
        
    def _explode(self):
        if not self.node:
            return
        Blast(
            position=self.node.position,
            velocity=self.node.velocity,
            blast_type='tnt',
            blast_radius=2.5,
            source_player=self._player
        ).autoretain()
        self.handlemessage(bs.DieMessage())
        