import math
import bascenev1 as bs

def euler_to_quaternion(yaw, pitch, roll):
    """Transforms a (Y, X, Z) euler rotation
    to a (W, X, Y, Z) quaternion rotation."""
    yaw = math.radians(yaw)
    pitch = math.radians(pitch)
    roll = math.radians(roll)

    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    qw = cy * cp * cr + sy * sp * sr
    qx = cy * cp * sr - sy * sp * cr
    qy = sy * cp * cr + cy * sp * sr
    qz = cy * sp * cr - sy * cp * sr

    return (qw, qx, qy, qz)


def get_direction(origin_pos, point_pos):
    """Returns the closest 8-way 
    direction from origin to point."""

    if isinstance(origin_pos, tuple):
        origin_pos = bs.Vec3(origin_pos)
    if isinstance(point_pos, tuple):
        point_pos = bs.Vec3(point_pos)

    dx = point_pos.x - origin_pos.x
    dz = point_pos.z - origin_pos.z

    # Nothing to point at.
    if dx == 0 and dz == 0:
        return 'center'

    angle = math.degrees(math.atan2(dx, -dz))
    angle %= 360

    directions = (
        'up',
        'up_right',
        'right',
        'down_right',
        'down',
        'down_left',
        'left',
        'up_left',
    )

    # Each direction covers 45 degrees.
    index = int((angle + 22.5) // 45) % 8

    return directions[index]

def look_at(origin_pos, point_pos):
    """Return a quaternion that faces 
    point_pos from origin_pos."""

    if isinstance(origin_pos, tuple):
        origin_pos = bs.Vec3(origin_pos)
    if isinstance(point_pos, tuple):
        point_pos = bs.Vec3(point_pos)

    dx = point_pos.x - origin_pos.x
    dz = point_pos.z - origin_pos.z

    # Same position; there is no direction to look toward.
    if dx == 0 and dz == 0:
        return euler_to_quaternion(0, 0, 0)

    yaw = math.degrees(math.atan2(dx, dz))

    return euler_to_quaternion(
        yaw=yaw,
        pitch=0,
        roll=0,
    )

def connect_pos(
    node1: bs.Node, 
    node2: bs.Node, 
    offset: tuple[float] = (0, 0),
):
    """Given 2 nodes and optionally a offset;
    connects the first to the second's position
    with the added offset, and returns the math node used."""
    mnode = bs.newnode(
        'math',
        owner=node2,
        attrs={
            'input1': offset, 
            'operation': 'add'
        },
    )
    node2.connectattr('position', mnode, 'input2')
    mnode.connectattr('output', node1, 'position')
    return mnode