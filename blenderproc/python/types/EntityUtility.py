from typing import Union, Optional
import numpy as np
import warnings

import bpy

from blenderproc.python.types.StructUtility import Struct
from blenderproc.python.utility.Utility import Utility, KeyFrame
from mathutils import Vector, Euler, Matrix

from typing import List


class Entity(Struct):

    def __init__(self, bpy_object: bpy.types.Object):
        super().__init__(bpy_object)

    def update_blender_ref(self, name: str):
        """ Updates the contained blender reference using the given name of the instance.

        :param name: The name of the instance which will be used to update its blender reference.
        """
        self.blender_obj = bpy.data.objects[name]

    def set_location(self, location: Union[list, Vector, np.ndarray], frame: int = None):
        """ Sets the location of the entity in 3D world coordinates.

        :param location: The location to set.
        :param frame: The frame number which the value should be set to. If None is given, the current frame number is used.
        """
        self.blender_obj.location = location
        Utility.insert_keyframe(self.blender_obj, "location", frame)

    def set_rotation_euler(self, rotation_euler: Union[list, Euler, np.ndarray], frame: int = None):
        """ Sets the rotation of the entity in euler angles.

        :param rotation_euler: The euler angles to set.
        :param frame: The frame number which the value should be set to. If None is given, the current frame number is used.
        """
        self.blender_obj.rotation_euler = rotation_euler
        Utility.insert_keyframe(self.blender_obj, "rotation_euler", frame)
    
    def set_rotation_mat(self, rotation_mat: Union[Matrix, np.ndarray], frame: int = None):
        """ Sets the rotation of the entity using a rotation matrix.

        :param rotation_mat: The 3x3 local to world rotation matrix.
        :param frame: The frame number which the value should be set to. If None is given, the current frame number is used.
        """
        self.set_rotation_euler(Matrix(rotation_mat).to_euler(), frame)

    def set_scale(self, scale: Union[list, np.ndarray, Vector], frame: int = None):
        """ Sets the scale of the entity along all three axes.

        :param scale: The scale to set.
        :param frame: The frame number which the value should be set to. If None is given, the current frame number is used.
        """
        self.blender_obj.scale = scale
        Utility.insert_keyframe(self.blender_obj, "scale", frame)

    def get_location(self, frame: int = None) -> np.ndarray:
        """ Returns the location of the entity in 3D world coordinates.

        :param frame: The frame number at which the value should be returned. If None is given, the current frame number is used.
        :return: The location at the specified frame.
        """
        with KeyFrame(frame):
            return np.array(self.blender_obj.location)

    def get_rotation(self, frame: int = None) -> np.ndarray:
        """ Returns the rotation of the entity in euler angles.

        :param frame: The frame number at which the value should be returned. If None is given, the current frame number is used.
        :return: The rotation at the specified frame.
        """
        warnings.warn("This function will be deprecated. Use get_rotation_euler() instead.")
        return self.get_rotation_euler(frame)

    def get_rotation_euler(self, frame: int = None) -> np.ndarray:
        """ Returns the rotation of the entity in euler angles.

        :param frame: The frame number at which the value should be returned. If None is given, the current frame number is used.
        :return: The rotation at the specified frame.
        """
        with KeyFrame(frame):
            return np.array(self.blender_obj.rotation_euler)
        
    def get_rotation_mat(self, frame: int = None) -> np.ndarray:
        """ Gets the rotation matrix of the entity.

        :param frame: The frame number which the value should be set to. If None is given, the current frame number is used.
        :return: The 3x3 local2world rotation matrix.
        """
        return np.array(Euler(self.get_rotation(frame)).to_matrix())
    
    def get_scale(self, frame: int = None) -> np.ndarray:
        """ Returns the scale of the entity along all three axes.

        :param frame: The frame number at which the value should be returned. If None is given, the current frame number is used.
        :return: The scale at the specified frame.
        """
        with KeyFrame(frame):
            return np.array(self.blender_obj.scale)

    def apply_T(self, transform: Union[np.ndarray, Matrix]):
        """ Apply the given transformation to the pose of the entity.

        :param transform: A 4x4 matrix representing the transformation.
        """
        self.blender_obj.matrix_world = Matrix(self.get_local2world_mat()) @ Matrix(transform)

    def set_local2world_mat(self, matrix_world: Union[np.ndarray, Matrix]):
        """ Sets the pose of the object in the form of a local2world matrix.

        :param matrix_world: A 4x4 matrix.
        """
        # To make sure matrices are always interpreted row-wise, we first convert them to a mathutils matrix.
        self.blender_obj.matrix_world = Matrix(matrix_world)

    def get_local2world_mat(self) -> np.ndarray:
        """ Returns the pose of the object in the form of a local2world matrix.

        :return: The 4x4 local2world matrix.
        """
        obj = self.blender_obj
        # Start with local2parent matrix (if obj has no parent, that equals local2world)
        matrix_world = obj.matrix_basis

        # Go up the scene graph along all parents
        while obj.parent is not None:
            # Add transformation to parent frame
            matrix_world = obj.parent.matrix_basis @ obj.matrix_parent_inverse @ matrix_world
            obj = obj.parent

        return np.array(matrix_world)

    def select(self):
        """ Selects the entity. """
        self.blender_obj.select_set(True)

    def deselect(self):
        """ Deselects the entity. """
        self.blender_obj.select_set(False)

    def clear_parent(self):
        """ Removes the object's parent and moves the object into the root level of the scene graph. """
        # Remember original object pose
        obj_pose = self.get_local2world_mat()
        self.blender_obj.parent = None
        # Make sure the object pose stays the same
        self.set_local2world_mat(obj_pose)

    def set_parent(self, new_parent: "Entity"):
        """ Sets the parent of this object.

        :param new_parent: The parent entity to set.
        """
        # If the object has already a parent object, remove it first.
        if self.blender_obj.parent is not None:
            self.clear_parent()
        self.blender_obj.parent = new_parent.blender_obj
        # Make sure the object pose stays the same => add inverse of new parent's pose to transformation chain
        self.blender_obj.matrix_parent_inverse = Matrix(new_parent.get_local2world_mat()).inverted()

    def get_parent(self) -> Optional["Entity"]:
        """ Returns the parent of the entity.

        :return: The parent.
        """
        return convert_to_entity_subclass(self.blender_obj.parent) if self.blender_obj.parent is not None else None

    def get_children(self) -> List["Entity"]:
        """ Returns the children objects.

        :return: A list of all children objects.
        """
        return convert_to_entities(self.blender_obj.children, convert_to_subclasses=True)

    def delete(self):
        """ Deletes the entity """
        bpy.ops.object.delete({"selected_objects": [self.blender_obj]})

    def is_empty(self) -> bool:
        """ Returns whether the entity is from type "EMPTY".

        :return: True, if its an empty.
        """
        return self.blender_obj.type == "EMPTY"

    def __setattr__(self, key, value):
        if key != "blender_obj":
            raise Exception(
                "The entity class does not allow setting any attribute. Use the corresponding method or directly access the blender attribute via entity.blender_obj.attribute_name")
        else:
            object.__setattr__(self, key, value)

    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.blender_obj == other.blender_obj
        return False

    def __hash__(self):
        return hash(self.blender_obj)


def create_empty(entity_name: str, empty_type: str = "plain_axes") -> "Entity":
    """ Creates an empty entity.

    :param entity_name: The name of the new entity.
    :param empty_type: Type of the newly created empty entity. Available: ["plain_axes", "arrows", "single_arrow", \
                       "circle", "cube", "sphere", "cone"]
    :return: The new Mesh entity.
    """
    if empty_type.lower() in ["plain_axes", "arrows", "single_arrow", "circle", "cube", "sphere", "cone"]:
        bpy.ops.object.empty_add(type=empty_type.upper(), align="WORLD")
    else:
        raise RuntimeError(f'Unknown basic empty type "{empty_type}"! Available types: "plain_axes".')

    new_entity = Entity(bpy.context.object)
    new_entity.set_name(entity_name)
    return new_entity


def convert_to_entities(blender_objects: list, convert_to_subclasses: bool = False) -> List["Entity"]:
    """ Converts the given list of blender objects to entities

    :param blender_objects: List of blender objects.
    :param convert_to_subclasses: If True, each blender object will be wrapped into a entity subclass based on the type of object.
    :return: The list of entities.
    """
    if not convert_to_subclasses:
        return [Entity(obj) for obj in blender_objects]
    else:
        return [convert_to_entity_subclass(obj) for obj in blender_objects]


def convert_to_entity_subclass(blender_object: bpy.types.Object) -> "Entity":
    """ Converts the given blender object into our respective wrapper class.

    :param blender_object: The blender object.
    :return: The wrapped object.
    """
    if blender_object.type == 'MESH':
        from blenderproc.python.types.MeshObjectUtility import MeshObject
        return MeshObject(blender_object)
    elif blender_object.type == 'LIGHT':
        from blenderproc.python.types.LightUtility import Light
        return Light(blender_obj=blender_object)
    else:
        return Entity(blender_object)


def delete_multiple(entities: List[Union["Entity"]]):
    """ Deletes multiple entities at once

    :param entities: A list of entities that should be deleted
    """
    bpy.ops.object.delete({"selected_objects": [e.blender_obj for e in entities]})
