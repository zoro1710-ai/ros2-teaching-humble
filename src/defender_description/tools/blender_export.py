"""Turn the Defender Blender model into URDF meshes and numbers.

Run it from the repository root with Blender 4.x (no window opens):

    blender -b path/to/Defender_Asembled.blend \
        --python src/defender_description/tools/blender_export.py

It writes, inside src/defender_description/:

    meshes/<link>__<colour>.stl     one mesh per link and colour, in metres,
                                    already placed in that link's own frame
    urdf/defender_generated.xacro   joint positions, link sizes, colours and
                                    one "visuals_<link>" macro per link

Change the CAD, run this again, and the URDF follows. The numbers are measured,
not typed. What IS hand-written is the tables below: which CAD part belongs to
which link, and where each joint pivots. That is the engineering judgement,
and it is what students should read.

About the model:
    * Units are millimetres (Blender says metres, but a 400 m robot is unlikely).
    * The robot faces -X in Blender. ROS wants +X forward, so everything is
      turned 180 degrees about Z on the way out.
    * Left and right copies of the suspension and wheels are stored as ONE
      mesh. Faces are sorted into left/right by which side of MID_Y they are.
"""

import os
import struct

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)
MESH_DIR = os.path.join(PACKAGE, 'meshes')
GENERATED = os.path.join(PACKAGE, 'urdf', 'defender_generated.xacro')

MM = 0.001        # model units -> metres
MID_Y = 50.0      # the model's left/right mirror plane, mm
TRI_BUDGET = 90000  # triangles for the whole robot; keeps RViz fast, git small

# ---------------------------------------------------------------------------
# Colours. CAD material name -> URDF colour name. Anything unlisted is 'metal'.
# ---------------------------------------------------------------------------
RGBA = {
    'dark': '0.12 0.12 0.14 1.0',
    'white': '0.85 0.85 0.85 1.0',
    'red': '0.80 0.05 0.05 1.0',
    'blue': '0.10 0.25 0.80 1.0',
    'orange': '1.00 0.45 0.05 1.0',
    'metal': '0.60 0.60 0.62 1.0',
}
COLOURS = {
    'Body_Black': 'dark', 'black.001': 'dark', 'black.002': 'dark',
    'black.003': 'dark', 'ZED2': 'dark', 'Lens': 'dark', 'Glass': 'dark',
    'GLOW': 'dark',
    'White_Body': 'white',
    'RED': 'red', 'Bull Eye': 'red',
    'Servo': 'blue', 'Darts': 'blue', 'Stepper.001': 'blue',
    'Darts.001': 'orange',
    'Stepper': 'metal',
}

# ---------------------------------------------------------------------------
# Which CAD part belongs to which link.
# ---------------------------------------------------------------------------
# Parts that belong to one link as a whole.
WHOLE = {
    'base_link': [
        'TOP1.002', 'TOP1.003', '1x_frame', '1x_bottom.003', '1x_bottom.004',
        'Cube.013', '1x_differential_mount', 'cover_ab', 'BASE_FULL.002',
        'camera_cover.002', 'Bull_Head_Low_Poly_QR_cover',
        # The three platform servo bodies are bolted to the chassis.
        'Stabilised - Tower-Pro-MG90S-1.001', 'Stabilised - Tower-Pro-MG90S-1.002',
        'Stabilised - Tower-Pro-MG90S-1.003',
    ],
    'zed2_camera': ['ZED2', 'Text'],
    'differential': ['1x_large_bevel_gear'],
    # The stepper hangs under the levelling plate and turns the turret above it.
    'platform': [
        'Platform_Top_Base', '28BYJ-48_Stepper.001', 'Circle.028',
        'joint_m.001', 'joint_m.002', 'joint_m.003',
        'joint_m_under.001', 'joint_m_under.002', 'joint_m_under.003',
        'ball_j.001', 'ball_j.002', 'ball_j.003',
    ],
    'turret': [
        'Top', 'Top.002', 'Circle.007', 'Circle.023',
        'MountBase.001', 'MountBase.002', 'MountBase.003', 'MountBase.004',
        'MountBase.005', 'Cube.009', 'Cube.011', 'Cube.012',
        'Ammo', 'Ammo-Side1', 'Ammo-Side1.001', 'AmmoClip', 'Ammo_ClipHead',
        'Ammo_Loader', 'Barrel', 'GA12-N20 Motor', 'GA12-N20 Motor.001',
    ],
    'flywheel_left': ['Ammo_Propeller'],
    'flywheel_right': ['Ammo_Propeller.001'],
    # Each levelling servo turns a horn + arm. The push-rods really hang between
    # arm and platform (a closed loop, which URDF cannot express), so they ride
    # on the arm here: exact at zero, slightly off when the arm moves.
    'platform_servo_front_left': [
        'Servo_Horn.001', 'arm12.001', 'arm12_rv_kakutei.001', 'arm2m.001', 'arm2m_ab.001'],
    'platform_servo_rear': [
        'Servo_Horn.002', 'arm12.002', 'arm12_rv_kakutei.002', 'arm2m.002', 'arm2m_ab.002'],
    'platform_servo_front_right': [
        'Servo_Horn.003', 'arm12.003', 'arm12_rv_kakutei.003', 'arm2m.003', 'arm2m_ab.003'],
}

# Parts stored as one mesh holding both the left and the right copy.
SPLIT = {
    'rocker': [
        '1x_1xm_top_arm_front', '1x_1xm_top_arm_back', '1x_1xm_top_arm_coupler',
        '1x_1xm_small_bevel_gear', '2x_end_stop',
        '6x_gear_servo.003',  # the rear wheel's steering servo
    ],
    'bogie': [
        '2x_arm_lower.002',
        '6x_gear_servo', '6x_gear_servo.001', '6x_gear_servo.002',  # front + middle
    ],
}

# Wheel pods, found by their Blender x position. The fork turns (steer);
# tyre and rim also spin (wheel). Names are matched without the .001 suffix.
WHEEL_X = {'front': 25.0, 'middle': 186.0, 'rear': 370.0}
STEER_PARTS = ['6x_gear', '6x_motor_mount_coupler', 'Bottom',
               'Wheel_LeftPart_Fin', 'Wheels_Right_Part_Fin']
SPIN_PARTS = ['Tyre_Fin', 'Rim_Fin']
SIDES = ('left', 'right')  # ROS left = Blender y < MID_Y (the model faces -X)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def to_ros(p):
    """Blender point in mm -> base-aligned ROS axes in metres (turn 180 about Z)."""
    return Vector((-p[0] * MM, -p[1] * MM, p[2] * MM))


def side_of(y):
    return 'left' if y < MID_Y else 'right'


def world_verts(name, side=None):
    obj = bpy.data.objects[name]
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if side is not None:
        points = [p for p in points if side_of(p.y) == side]
    return points


def centre(points):
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    return (lo + hi) / 2, lo, hi


def base_name(name):
    return name.split('.')[0]


def pod_of(name):
    x = centre(world_verts(name))[0].x
    return min(WHEEL_X, key=lambda pod: abs(WHEEL_X[pod] - x))


# ---------------------------------------------------------------------------
# 1. Decide which (link, side) every face goes to.
# ---------------------------------------------------------------------------
def assignments():
    """Yield (object name, link or None, side or None) for every CAD part."""
    for link, names in WHOLE.items():
        for name in names:
            yield name, link, None
    for kind, names in SPLIT.items():
        for name in names:
            yield name, kind, 'split'
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        if base_name(obj.name) in STEER_PARTS:
            yield obj.name, pod_of(obj.name) + '_steer', 'split'
        elif base_name(obj.name) in SPIN_PARTS:
            yield obj.name, pod_of(obj.name) + '_wheel', 'split'


def link_name(kind, side):
    """Name a split link: rocker + left -> left_rocker, front_wheel -> front_left_wheel."""
    if kind in ('rocker', 'bogie'):
        return '%s_%s' % (side, kind)
    pod, part = kind.split('_')
    return '%s_%s_%s' % (pod, side, part)


# ---------------------------------------------------------------------------
# 2. Where every link frame sits (Blender mm) and who its parent is.
# ---------------------------------------------------------------------------
def frames():
    """Return {link: (parent, pivot in Blender mm)}."""
    top = bpy.data.objects['Top'].matrix_world.translation
    platform_z = centre(world_verts('joint_m.001'))[0].z  # the ball-joint plane
    base = Vector((top.x, MID_Y, 120.0))  # under the turret, at rocker height
    f = {'base_link': (None, base)}

    for side in SIDES:
        rocker_y = centre(world_verts('1x_1xm_top_arm_coupler', side))[0].y
        bogie_y = centre(world_verts('2x_arm_lower.002', side))[0].y
        # Pivots: circle-fitted to the bearing holes in the arms.
        f['%s_rocker' % side] = ('base_link', Vector((275.0, rocker_y, 120.0)))
        f['%s_bogie' % side] = ('%s_rocker' % side, Vector((105.0, bogie_y, 67.0)))
        for pod in WHEEL_X:
            gear = [n for n in ('6x_gear', '6x_gear.001', '6x_gear.003') if pod_of(n) == pod][0]
            tyre = [n for n in ('Tyre_Fin', 'Tyre_Fin.001', 'Tyre_Fin.002') if pod_of(n) == pod][0]
            carrier = '%s_rocker' % side if pod == 'rear' else '%s_bogie' % side
            f['%s_%s_steer' % (pod, side)] = (carrier, centre(world_verts(gear, side))[0])
            f['%s_%s_wheel' % (pod, side)] = (
                '%s_%s_steer' % (pod, side), centre(world_verts(tyre, side))[0])

    f['differential'] = ('base_link', centre(world_verts('1x_large_bevel_gear'))[0])
    platform = Vector((top.x, top.y, platform_z))
    f['platform_roll'] = ('base_link', platform)
    f['platform'] = ('platform_roll', platform)
    f['turret'] = ('platform', Vector((top.x, top.y, 172.8)))  # top of the plate
    for side, name in (('left', 'Ammo_Propeller'), ('right', 'Ammo_Propeller.001')):
        f['flywheel_' + side] = ('turret', centre(world_verts(name))[0])
    c, lo, _ = centre(world_verts('Barrel'))
    f['muzzle'] = ('turret', Vector((lo.x, c.y, c.z)))
    for link, horn in (('platform_servo_front_left', 'Servo_Horn.001'),
                       ('platform_servo_rear', 'Servo_Horn.002'),
                       ('platform_servo_front_right', 'Servo_Horn.003')):
        f[link] = ('base_link', bpy.data.objects[horn].matrix_world.translation.copy())
    c, lo, _ = centre(world_verts('ZED2'))
    f['zed2_camera'] = ('base_link', Vector((lo.x, c.y, c.z)))
    return f


def servo_axis(horn):
    """Servo axis in ROS: the horn's thin local Y, flipped so + lifts the arm."""
    axis = -bpy.data.objects[horn].matrix_world.to_3x3().col[1].normalized()
    return to_ros(axis / MM).normalized()


# ---------------------------------------------------------------------------
# 3. Build, simplify and write one mesh per (link, colour).
# ---------------------------------------------------------------------------
def collect_faces(frame_table):
    """Return {(link, colour): (vertices, faces, area)} in each link's own frame."""
    groups = {}
    seen = set()
    for name, kind, split in assignments():
        seen.add(name)
        obj = bpy.data.objects[name]
        world = obj.matrix_world
        points = [world @ v.co for v in obj.data.vertices]
        for poly in obj.data.polygons:
            y = sum(points[i].y for i in poly.vertices) / len(poly.vertices)
            link = link_name(kind, side_of(y)) if split else kind
            origin = to_ros(frame_table[link][1])
            slot = obj.material_slots[poly.material_index] if obj.material_slots else None
            colour = COLOURS.get(slot.material.name if slot and slot.material else '', 'metal')
            verts, faces, area = groups.setdefault((link, colour), ([], [], [0.0]))
            start = len(verts)
            verts.extend(to_ros(points[i]) - origin for i in poly.vertices)
            faces.append(list(range(start, start + len(poly.vertices))))
            corners = [points[i] for i in poly.vertices]
            area[0] += sum(((corners[k] - corners[0]).cross(corners[k + 1] - corners[0])).length
                           for k in range(1, len(corners) - 1)) / 2

    missing = [o.name for o in bpy.context.scene.objects
               if o.type == 'MESH' and o.data.polygons and o.name not in seen]
    if missing:
        raise SystemExit('These CAD parts are not assigned to a link: %s' % missing)
    return groups


def simplify(verts, faces, ratio):
    """Merge the duplicate corners, then collapse to ratio of the triangles."""
    mesh = bpy.data.meshes.new('tmp')
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new('tmp', mesh)
    bpy.context.scene.collection.objects.link(obj)
    weld = obj.modifiers.new('weld', 'WELD')
    weld.merge_threshold = 1e-6
    if ratio < 1.0:
        collapse = obj.modifiers.new('collapse', 'DECIMATE')
        collapse.ratio = ratio
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    result = evaluated.to_mesh()
    result.calc_loop_triangles()
    tris = [tuple(result.vertices[i].co.copy() for i in t.vertices)
            for t in result.loop_triangles]
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)
    return tris


def write_stl(path, tris):
    with open(path, 'wb') as f:
        f.write(b'defender_description, made by tools/blender_export.py'.ljust(80))
        f.write(struct.pack('<I', len(tris)))
        for a, b, c in tris:
            normal = (b - a).cross(c - a)
            if normal.length > 0:
                normal.normalize()
            f.write(struct.pack('<12fH', *normal, *a, *b, *c, 0))


# ---------------------------------------------------------------------------
# 4. Write the numbers for the xacro.
# ---------------------------------------------------------------------------
def fmt(v):
    return ' '.join('%.5f' % (x + 0.0) for x in v)


def write_generated(frame_table, visuals, boxes):
    lines = [
        '<?xml version="1.0"?>',
        '<!--',
        '  GENERATED by tools/blender_export.py from Defender_Asembled.blend.',
        '  Do not edit: change the CAD or the script, and run it again.',
        '',
        '  <link>_origin   joint position, relative to the parent link (m)',
        '  inertia_<link>  inertia of a box the size of the link; you give the mass',
        '  visuals_<link>  every mesh of that link, with its colour',
        '-->',
        '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">',
        '',
    ]
    for name, rgba in RGBA.items():
        lines.append('  <material name="%s"><color rgba="%s"/></material>' % (name, rgba))
    lines.append('')

    for link, (parent, pivot) in frame_table.items():
        if parent is None:
            continue
        offset = to_ros(pivot) - to_ros(frame_table[parent][1])
        lines.append('  <xacro:property name="%s_origin" value="%s"/>' % (link, fmt(offset)))
    ground = -(frame_table['base_link'][1].z - centre(world_verts('Tyre_Fin'))[1].z) * MM
    lines.append('  <xacro:property name="base_footprint_z" value="%.5f"/>' % ground)

    for link, horn in (('platform_servo_front_left', 'Servo_Horn.001'),
                       ('platform_servo_rear', 'Servo_Horn.002'),
                       ('platform_servo_front_right', 'Servo_Horn.003')):
        lines.append('  <xacro:property name="%s_axis" value="%s"/>'
                     % (link, fmt(servo_axis(horn))))

    # Differential: rocker turns the small bevel gear, which turns the big one.
    small = centre(world_verts('1x_1xm_small_bevel_gear', 'left'))
    radius = (small[2].z - small[1].z) / 2
    lever = abs(small[0].y - MID_Y)
    lines.append('  <xacro:property name="differential_ratio" value="%.4f"/>' % (radius / lever))
    lines.append('')

    # Inertia of a solid box the size of the link. Only the mass is a guess,
    # and that is passed in from defender.urdf.xacro.
    for link in sorted(boxes):
        lo, hi = boxes[link]
        (x, y, z), mid = hi - lo, (hi + lo) / 2
        lines += [
            '  <xacro:macro name="inertia_%s" params="mass">' % link,
            '    <inertial>',
            '      <origin xyz="%s"/>' % fmt(mid),
            '      <mass value="${mass}"/>',
            '      <inertia ixx="${mass * %.4e}" ixy="0" ixz="0"' % ((y * y + z * z) / 12),
            '               iyy="${mass * %.4e}" iyz="0"' % ((x * x + z * z) / 12),
            '               izz="${mass * %.4e}"/>' % ((x * x + y * y) / 12),
            '    </inertial>',
            '  </xacro:macro>',
        ]
    lines.append('')

    for link in sorted(visuals):
        lines.append('  <xacro:macro name="visuals_%s">' % link)
        for colour, filename in sorted(visuals[link]):
            lines += [
                '    <visual>',
                '      <geometry><mesh filename='
                '"package://defender_description/meshes/%s"/></geometry>' % filename,
                '      <material name="%s"/>' % colour,
                '    </visual>',
            ]
        lines.append('  </xacro:macro>')
    lines += ['</robot>', '']
    with open(GENERATED, 'w', newline='\n') as f:
        f.write('\n'.join(lines))


def main():
    frame_table = frames()
    groups = collect_faces(frame_table)

    # Share the triangle budget by surface area: the big chassis panels need
    # more triangles than a tiny, screw-covered servo horn does.
    counts = {key: sum(len(face) - 2 for face in f) for key, (v, f, a) in groups.items()}
    total_area = sum(a[0] for v, f, a in groups.values())

    os.makedirs(MESH_DIR, exist_ok=True)
    for old in os.listdir(MESH_DIR):
        if old.endswith('.stl'):
            os.remove(os.path.join(MESH_DIR, old))

    visuals, boxes, total = {}, {}, 0
    for (link, colour), (verts, faces, area) in sorted(groups.items()):
        # Small parts keep their shape: never go below 300 triangles.
        target = max(300, TRI_BUDGET * area[0] / total_area)
        tris = simplify(verts, faces, min(1.0, target / counts[(link, colour)]))
        filename = '%s__%s.stl' % (link, colour)
        write_stl(os.path.join(MESH_DIR, filename), tris)
        visuals.setdefault(link, []).append((colour, filename))
        points = [p for t in tris for p in t]
        lo = Vector([min(p[i] for p in points) for i in range(3)])
        hi = Vector([max(p[i] for p in points) for i in range(3)])
        if link in boxes:
            lo = Vector(map(min, lo, boxes[link][0]))
            hi = Vector(map(max, hi, boxes[link][1]))
        boxes[link] = (lo, hi)
        total += len(tris)
        print('%-40s %6d triangles' % (filename, len(tris)))

    write_generated(frame_table, visuals, boxes)
    print('%d meshes, %d triangles -> %s' % (len(groups), total, MESH_DIR))
    print('numbers -> %s' % GENERATED)


main()
