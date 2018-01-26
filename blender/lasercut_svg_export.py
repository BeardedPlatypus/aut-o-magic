"""
Export two dimensional objects in blender to SVG files, to be laser cut.
"""

# ------------------------------------------------------------------------------
# Libraries
import math
import sys

import svgwrite

import bpy
import mathutils
import bmesh


# ------------------------------------------------------------------------------
# Author information
__author__ = "Maarten Tegelaers"
__copyright__ = "Copyright 2018, Maarten Tegelaers"

__license__ = "All Rights Reserved"
__version__ = "0.1"
__status__ = "development"


# ------------------------------------------------------------------------------
# Units
def construct_unit_dict(units_per_inch: float) -> dict:
    '''
    Construct the unit dictionary to translate specified units to svg units.

    :param units_per_inch: The number of pixels per inch.

    The following units are defined
    px: 1
    pt: 1.25
    pc: 15
    in: units_per_inch | 90 according to svg spec, 96 for Inkscape
    mm: units_per_inch / 25.4
    cm: units_per_inch / 2.54
    '''
    return { "px": 1.00
           , "pt": 1.25
           , "pc": 15.0
           , "in": units_per_inch
           , "mm": units_per_inch / 25.4
           , "cm": units_per_inch / 2.54
           }


# ------------------------------------------------------------------------------
# Classes
class VertexInternal(object):
    '''
    Two dimensional Vertex class used to represent points of the exported
    outline.
    '''
    def __init__(self, index: int, x: float, y: float):
        """
        Construct a new VertexInternal with the specified index and coordinates

        :param index: The unique index of this new VertexInternal
        :param x: The x-coordinate of this new VertexInternal
        :param y: The y-coordinate of this new VertexInternal

        :returns: A new VertexInternal with the specified parameters
        """
        self._index = index
        self._x = x
        self._y = y

    @property
    def x(self) -> float:
        """ The x-coordinate of this VertexInternal. """
        return self._x

    @property
    def y(self) -> float:
        """ The y-coordinate of this VertexInternal. """
        return self._y

    @property
    def index(self) -> float:
        """ The unique index of this VertexInternal. """
        return self._index

    def rotate_by(self, angle: float):
        """
        Rotate the coordinates of this VertexInternal by the specified angle.

        :param angle: The angle by which this VertexInternal should be rotated.
        """
        self._x = self.x * math.cos(angle) - self.y * math.sin(angle)
        self._y = self.x * math.sin(angle) + self.y * math.cos(angle)

    def distance_to(self, vert) -> float:
        """
        Calculate the distance from this VertexInternal to the specified
        VertexInternal.

        :param vert: The other VertexInternal

        :returns: The distance from this VertexInternal to vert
        """
        x_dif = vert.x - self.x
        y_dif = vert.y - self.y
        return math.sqrt(x_dif * x_dif + y_dif * y_dif)

    def __eq__(self, other):
        if isinstance(other, VertexInternal):
            return self.index == other.index
        return False

    def __str__(self):
        return "VertexInternal: x: {} | y: {}".format(self.x, self.y)


class Outline(object):
    """
    The Outline holds a set of VertexInternal objects which specify the
    a closed path.
    """
    def __init__(self, verts: list):
        self._verts = verts

    @property
    def verts(self) -> list:
        """
        Return a copy of the VertexInternal objects which specify the path
        of this Outline
        """
        return self._verts


# ------------------------------------------------------------------------------
# Math support functions
def skew_symmetric_matrix(v: mathutils.Vector) -> mathutils.Matrix:
    """
    Get the skew symmetric matrix based upon the specified vector

    :param v: The vector with which the skew symmetric matrix is constructed

    :returns: The skew symmetric matrix constructed with v
    """
    return mathutils.Matrix(([    0, -v.z,  v.y],
                             [  v.z,    0, -v.x],
                             [ -v.y,  v.x,    0]))


def calculate_angle(shared_vert: VertexInternal,
                    other_vert_a: VertexInternal,
                    other_vert_b: VertexInternal) -> float:
    """
    Calculate the angle between the vectors shared_vert | other_vert_a
    and shared_vert | other_vert_b

    :param shared_vert: The VertexInternal shared by the two vectors
    :param other_vert_a: The VertexInternal corresponding with the end point
                         of one of the vectors.
    :param other_vert_b: The VertexInternal corresponding with the end point
                         of the other vector.

    :returns: The angle between the specified vectors in radians.
    """
    vec_a = (other_vert_a.x - shared_vert.x,
             other_vert_a.y - shared_vert.y)
    vec_b = (other_vert_b.x - shared_vert.x,
             other_vert_b.y - shared_vert.y)
    len_a = math.sqrt(vec_a[0] * vec_a[0] + vec_a[1] * vec_a[1])
    len_b = math.sqrt(vec_b[0] * vec_b[0] + vec_b[1] * vec_b[1])

    dot_product = vec_a[0] * vec_b[0] + vec_a[1] * vec_b[1]
    angle = math.acos(dot_product / (len_a * len_b))
    return angle


def get_rotation_matrix_from_normal(normal : mathutils.Vector):
    """
    Construct the rotation matrix to rotate the specified normal vector
    onto the (0.0, 0.0, 1.0) vector

    :param normal: The normal vector used to construct the rotation matrix

    :returns: The rotation matrix to align the normal vector with the z-axis.
    """
    vec_z = mathutils.Vector((0.0, 0.0, 1.0))
    c = normal.dot(vec_z)

    if fuzzy_equals(c, 1) or fuzzy_equals(c, -1):
        return mathutils.Matrix.Identity(3)

    v = normal.cross(vec_z)

    v_skew = skew_symmetric_matrix(v)
    R = mathutils.Matrix.Identity(3) + v_skew + (v_skew * v_skew * (1.0 / 1.0 + c))
    return R


def get_rotation_quaternion_from_normal(normal : mathutils.Vector):
    """
    Construct the rotation quaternion to rotate the specified normal vector
    onto the (0.0, 0.0, 1.0) vector

    :param normal: The normal vector used to construct the rotation quaternion

    :returns: The rotation quaternion to align the normal with the z-axis
    """
    vec_z = mathutils.Vector((0.0, 0.0, 1.0))
    theta = normal.angle(vec_z) # angle
    axis  = normal.cross(vec_z) # axis
    axis.normalize()

    sin_theta = math.sin(theta / 2.0)
    q_rot = mathutils.Quaternion((math.cos(theta / 2.0),
                                  axis.x * sin_theta,
                                  axis.y * sin_theta,
                                  axis.z * sin_theta))

    q_norm = mathutils.Quaternion((0.0, normal.x, normal.y, normal.z))
    rot = q_rot * q_norm * q_rot.conjugated()

    print(normal)
    print(axis)
    print(mathutils.Vector((rot.x, rot.y, rot.z)))

    return q_rot



def fuzzy_equals(a: float, b: float) -> bool:
    """
    Compare float a and float b on equality

    :param a: one of the floats to be compared
    :param b: the other float to be compared

    :returns: True if a==b False otherwise
    """
    return abs(a - b) <= sys.float_info.epsilon


# ------------------------------------------------------------------------------
# Select objects to be exported
def get_selected_objects(only_selected : bool,
                         with_substring : str):
    '''
    Get all objects within the scene that should be exported according to
    the settings.

    :param only_selected: If True limit the objects to be exported to those
                          selected within Blender.
    :param with_substring: If True only export objects where the name starts
                           with the specified substring.

    :returns: A set of mesh objects to be exported
    '''
    result = []
    #objects = bpy.data.scenes[0].objects
    objects = bpy.data.objects

    for obj in objects:
        if (obj.type == 'MESH'
            and (not only_selected or obj.select)
            and (not with_substring or str(obj.name).startswith(with_substring))):
            result.append(obj)
    return result


# ------------------------------------------------------------------------------
# Construct outline out of the selected objects
def _to_vert_internal(vertex, index, rotation_matrix, height):
    vec2d = rotation_matrix * vertex.co

    if not fuzzy_equals(vec2d.z, height):
        raise Exception("Height not equal")
    return VertexInternal(index, vec2d.x, vec2d.y)


def _to_vert_internal_quaternion(vertex, index, rotation_quaternion, height):
    q_v = mathutils.Quaternion((0.0, vertex.co.x, vertex.co.y, vertex.co.z))
    rot = rotation_quaternion * q_v * rotation_quaternion.conjugated()
    return VertexInternal(index, rot.x, rot.y)

def get_outlines(obj) -> list:
    """
    Get the outlines within the specified object.

    :param obj: The object from which the outlines should be extracted

    :returns: A list of Outlines that correspond with the outlines of the
              specified object.
    """
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.edges.index_update() # update internal indices to be correct

    if len(mesh.faces) <= 0:
        raise Exception("No Data")

    # determine rotation of the faces based on a normal (assuming the object is
    # flat, this should not cause any problems)
    mesh.faces.ensure_lookup_table()
    mesh.edges.ensure_lookup_table()


    normal_raw = mesh.faces[0].normal
    normal = mathutils.Vector((normal_raw[0], normal_raw[1], normal_raw[2]))
    #rotation_matrix = get_rotation_matrix_from_normal(normal)
    #rotation_matrix = mathutils.Matrix.Identity(3)
    q_rot = get_rotation_quaternion_from_normal(normal)

    # determine relevant edges
    relevant_edges = list(edge for edge in mesh.edges if len(edge.link_faces) == 1)
    relevant_edge_ids = list(edge.index for edge in relevant_edges)

    # construct separate outlines
    result = []

    height = 0.0# (rotation_matrix * relevant_edges[0].verts[0].co).z
    index = 0

    while relevant_edges:
        # Construct first element of the outline
        first_element = relevant_edges.pop()
        first_element_id = relevant_edge_ids.pop()

        # Construct first two Vertices
        prev_vertex_internal = _to_vert_internal_quaternion(first_element.verts[0],
                                                            index,
                                                            q_rot,
                                                            #rotation_matrix,
                                                            height)
        index += 1
        cur_vertex_internal = _to_vert_internal_quaternion(first_element.verts[1],
                                                           index,
                                                           q_rot,
                                                           #rotation_matrix,
                                                           height)
        index += 1

        verts = [prev_vertex_internal,]

        cur_vertex = first_element.verts[1]
        while True:
            has_finished = False
            next_edge = None

            for edge in cur_vertex.link_edges:
                if edge.index == first_element_id:
                    has_finished = True
                    break
                if edge.index in relevant_edge_ids:
                    next_edge = edge
                    break

            if has_finished:
                break
            if not next_edge:
                raise Exception("No next edge found")

            if cur_vertex == next_edge.verts[0]:
                next_vertex = next_edge.verts[1]
            else:
                next_vertex = next_edge.verts[0]

            next_vertex_internal = _to_vert_internal_quaternion(next_vertex,
                                                                index,
                                                                q_rot,
                                                                #rotation_matrix,
                                                                height)
            # only update index if vertex is acceppted

            #angle = calculate_angle(cur_vertex_internal,
            #                        prev_vertex_internal,
            #                        next_vertex_internal)

            if True:
            #if not fuzzy_equals(angle, math.pi):
                verts.append(cur_vertex_internal)
                index += 1

                prev_vertex_internal = cur_vertex_internal
                cur_vertex_internal = next_vertex_internal

            relevant_edges.remove(edge)
            relevant_edge_ids.remove(next_edge.index)
            cur_vertex = next_vertex

        # check if current vertex internal can be added
        #angle = calculate_angle(cur_vertex_internal,
        #                        prev_vertex_internal,
        #                        verts[0])
        #if not fuzzy_equals(angle, math.pi):
        #    verts.append(cur_vertex_internal)

        # check if first vertex internal can be deleted
        #angle = calculate_angle(verts[0],
        #                        verts[1],
        #                        verts[-1])

        if False:
        #if fuzzy_equals(angle, math.pi):
            verts = verts[1:]

        result.append(Outline(verts))
    return result


def write_obj_to_svg(outlines, padding, file_name, document_settings, unit_size, do_rotate = True):
    """
    Construct an SVG drawing from the specified outline, padding and document_settings and write it
    to file_name.

    :param outlines: The outlines of the object that should be written away.
    :param padding: The padding in pixels that should be added. Specified as x-neg, x-pos, y-neg and y-pos.
    :param file_name: The file name to which the svg drawing is written.
    :param document_settings: The document settings of the svg. This should contain at least stroke, stroke-width,
                              debug and profile.
    :param unit_size: The unit size of each user unit in pixels.
    :param do_rotate: If true rotate the svg drawing such that the longest edge is up.
    """
    # Calculate rotation
    if do_rotate:
        # calculate longest edge
        longest_edge_size = 0.0
        longest_edge = None

        for outline in outlines:
            verts = outline.verts
            for i in range(len(verts)):
                size_edge = verts[i].distance_to(verts[i - 1])
                if size_edge > longest_edge_size:
                    longest_edge_size = size_edge
                    longest_edge = (verts[i], verts[i - 1])

        #TODO check the math of this
        angle = math.acos((longest_edge[0].y - longest_edge[1].y) / longest_edge_size)

        # Update all vertices
        for outline in outlines:
            for vert in outline.verts:
                vert.rotate_by(angle)

    # Calculate translation, padding, document size
    min_x = +math.inf
    min_y = +math.inf
    max_x = -math.inf
    max_y = -math.inf
    for outline in outlines:
        for vert in outline.verts:
            if vert.x < min_x:
                min_x = vert.x
            if vert.x > max_x:
                max_x = vert.x
            if vert.y < min_y:
                min_y = vert.y
            if vert.y > max_y:
                max_y = vert.y

    document_size_x = padding["x-neg"] + (max_x - min_x) * unit_size + padding["x-pos"]
    document_size_y = padding["y-neg"] + (max_y - min_y) * unit_size + padding["y-pos"]

    translation_x = padding["x-neg"] - min_x * unit_size
    translation_y = padding["y-neg"] - min_y * unit_size

    # Build the svg drawing with svgwrite
    dwg = svgwrite.Drawing(filename=file_name,
                           size=(document_size_x, document_size_y),
                           profile=document_settings["profile"],
                           debug=document_settings["debug"])

    # Construct path_cmds as specified by the SVG spec: https://www.w3.org/TR/SVG/paths.html
    path_cmd = ""

    for outline in outlines:
        verts = outline.verts
        path_cmd += "M {}, {} ".format(verts[0].x * unit_size + translation_x,
                                       verts[0].y * unit_size + translation_y)

        for vert in verts[1:]:
            path_cmd += "L {}, {} ".format(vert.x * unit_size + translation_x,
                                           vert.y * unit_size + translation_y)
        path_cmd += "Z "

    path = dwg.add(dwg.path(d=path_cmd,
                            stroke=document_settings["stroke"],
                            stroke_width=document_settings["stroke-width"],
                            fill=document_settings["fill"],
                            fill_opacity=document_settings["fill-opacity"]))

    # Save the drawing
    dwg.save()


if __name__ == '__main__':
    unit_dict = construct_unit_dict(96.0)
    objects = get_selected_objects(only_selected=False,
                                   with_substring="LC")

    for obj in objects:
        object_outline = get_outlines(obj)
        write_obj_to_svg(outlines=object_outline,
                         padding={"x-neg":1.0 * unit_dict["cm"],
                                  "x-pos":1.0 * unit_dict["cm"],
                                  "y-neg":1.0 * unit_dict["cm"],
                                  "y-pos":1.0 * unit_dict["cm"]},
                         file_name="{}.svg".format(obj.name[4:]),
                     document_settings={"profile": "tiny",
                                        "debug": True,
                                        "stroke": "black",
                                        "stroke-width": 1.0,
                                        "fill": "white",
                                        "fill-opacity": 0.0},
                     unit_size=unit_dict["cm"],
                     do_rotate=False)

