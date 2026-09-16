import bascenev1 as bs
import babase as ba

def spawn_player_spaz(
    self,
    player: bs.Player,
    position: Sequence[float] = (0, 0, 0),
    angle: float | None = None,
) -> PlayerSpaz:
    """Create and wire up a player-spaz for the provided player."""
    # pylint: disable=cyclic-import
    from bascenev1._gameutils import animate
    from bascenev1._coopsession import CoopSession
    from bascenev1lib.actor.playerspaz import PlayerSpaz

    name = player.getname()
    color = player.color
    highlight = player.highlight
    testing = True

    playerspaztype = getattr(player, 'playerspaztype', PlayerSpaz)
    if not issubclass(playerspaztype, PlayerSpaz):
        playerspaztype = PlayerSpaz
    if testing:
        from mell.doomguy import DoomGuy
        playerspaztype = DoomGuy

    light_color = babase.normalized_color(color)
    display_color = babase.safecolor(color, target_intensity=0.75)
    spaz = playerspaztype(
        color=color,
        highlight=highlight,
        character=player.character,
        player=player,
        position=position,
    )

    player.actor = spaz
    assert spaz.node

    # If this is co-op and we're on Courtyard or Runaround, add the
    # material that allows us to collide with the player-walls.
    # FIXME: Need to generalize this.
    if isinstance(self.session, CoopSession) and self.map.getname() in [
        'Courtyard',
        'Tower D',
    ]:
        mat = self.map.preloaddata['collide_with_wall_material']
        assert isinstance(spaz.node.materials, tuple)
        assert isinstance(spaz.node.roller_materials, tuple)
        spaz.node.materials += (mat,)
        #spaz.node.roller_materials += (mat,)
    if not testing:
        spaz.node.name = name
        spaz.node.name_color = display_color
    spaz.connect_controls_to_player()

    # Move to the stand position and add a flash of light.
    spaz.handlemessage(
        StandMessage(
            position, angle if angle is not None else random.uniform(0, 360)
        )
    )
    self._spawn_sound.play(1, position=spaz.node.position)
    light = _bascenev1.newnode('light', attrs={'color': light_color})
    spaz.node.connectattr('position', light, 'position')
    animate(light, 'intensity', {0: 0, 0.25: 1, 0.5: 0})
    _bascenev1.timer(0.5, light.delete)
    return spaz

# ba_meta export babase.Plugin
class DoomishPlugin(ba.Plugin):
    def on_app_running(self) -> None:
        """Called when the app reaches the running state."""
        bs.GameActivity.spawn_player_spaz = spawn_player_spaz