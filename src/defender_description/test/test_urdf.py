"""The URDF builds, is one connected tree, and every mesh it names exists."""

import os
import xml.etree.ElementTree as ET

import pytest
import xacro

PACKAGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URDF = os.path.join(PACKAGE, 'urdf', 'defender.urdf.xacro')


@pytest.fixture(scope='module')
def robot():
    return ET.fromstring(xacro.process_file(URDF).toxml())


def test_one_tree_from_base_footprint(robot):
    links = {link.get('name') for link in robot.findall('link')}
    joints = robot.findall('joint')
    children = [j.find('child').get('link') for j in joints]
    assert len(children) == len(set(children)), 'a link has two parents'
    roots = links - set(children)
    assert roots == {'base_footprint'}
    assert len(joints) == len(links) - 1


def test_every_mesh_file_exists(robot):
    prefix = 'package://defender_description/'
    meshes = [m.get('filename') for m in robot.iter('mesh')]
    assert meshes
    for filename in meshes:
        assert filename.startswith(prefix)
        assert os.path.isfile(os.path.join(PACKAGE, filename[len(prefix):])), filename


def test_joint_counts(robot):
    kinds = [j.get('type') for j in robot.findall('joint')]
    assert kinds.count('continuous') == 8   # 6 wheels + 2 flywheels
    assert kinds.count('revolute') == 17
    mimics = {j.get('name') for j in robot.findall('joint') if j.find('mimic') is not None}
    assert mimics == {'right_rocker_joint', 'differential_joint', 'flywheel_right_joint'}


def test_every_moving_link_has_mass(robot):
    for link in robot.findall('link'):
        if link.find('visual') is not None:
            mass = float(link.find('inertial/mass').get('value'))
            assert mass > 0, link.get('name')
