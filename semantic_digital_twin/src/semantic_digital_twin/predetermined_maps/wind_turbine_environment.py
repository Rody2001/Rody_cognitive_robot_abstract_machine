from poetry.publishing import Publisher

from semantic_digital_twin.adapters.ros.visualization.viz_marker import (
    VizMarkerPublisher,
)
from semantic_digital_twin.semantic_annotations.semantic_annotations import (
    Table,
    Sofa,
    TrashCan,
    Fridge, CounterTop, Wall, Cabinet,
    Cupboard,
    Door,
    Desk,
    Handle,
    ShelfLayer,
    Hinge, Oven, Carrot, WindTurbineColumn, WindTurbineHead,
)
from semantic_digital_twin.world import World
import threading
import rclpy
import numpy as np
from semantic_digital_twin.datastructures.prefixed_name import PrefixedName
from semantic_digital_twin.semantic_annotations.semantic_annotations import Room, Floor
from semantic_digital_twin.spatial_types.spatial_types import (
    HomogeneousTransformationMatrix,
    Point3,
)
from semantic_digital_twin.spatial_types.derivatives import DerivativeMap
from semantic_digital_twin.world_description.connections import FixedConnection, RevoluteConnection
from semantic_digital_twin.world_description.geometry import Box, Scale, Color
from semantic_digital_twin.world_description.geometry import Cylinder
from semantic_digital_twin.world_description.shape_collection import ShapeCollection
from semantic_digital_twin.world_description.world_entity import Body
from semantic_digital_twin.spatial_types.spatial_types import Vector3
from semantic_digital_twin.world_description.degree_of_freedom import (
    DegreeOfFreedomLimits, DegreeOfFreedom,
)
from test.conftest import kitchen_environment_fixture


class WindFarmEnvironment:
    """
    Manages the Kitchen Environment world with walls, furniture, and room layouts.
    """

    def get_world(self) -> World:
        """
        Constructs and returns a new World instance, setting up its environment,
        including walls, furniture, and rooms.

        :return: A new world instance with the initialized environment.
        """
        world = World()
        root = Body(name=PrefixedName("root"))
        with world.modify_world():
            world.add_body(root)

        self._build_turbines(world)

        return world

    def _build_turbines(self, world: World):
        """
        ...

        :param world: An instance representing the environment world where walls are to be
        configured and added.

        :return: The modified world instance with configured walls and connections.
        """
        root = world.root

        turbine_1 = Box(scale=Scale(x=0.01, y=2.5, z=0.5), color=Color.RED())
        shape_geometry = ShapeCollection([turbine_1])
        turbine_1_body = Body(
            name=PrefixedName("turbine_1_body"),
            collision=shape_geometry,
            visual=shape_geometry,
        )

        root_C_turbine_1_body = FixedConnection(
            parent=root,
            child=turbine_1_body,
            parent_T_connection_expression=HomogeneousTransformationMatrix.from_xyz_rpy(
                x=1.0, y=0.0, z=5.0
            )
        )

        with world.modify_world():

            wind_turbine_1_column = WindTurbineColumn.create_with_new_cylinder_body_in_world(
                world=world,
                name=PrefixedName("wind_turbine_1_column"),
                world_root_T_self=HomogeneousTransformationMatrix.from_xyz_rpy(
                    x=0.0, y=0.0, z=7.8985
                ),
                scale=Scale(x=0.901, y=0.901, z=15.797),
            )

            wind_turbine_1_head = WindTurbineHead.create_with_new_cylinder_body_in_world(
                world=world,
                name=PrefixedName("wind_turbine_1_head"),
                world_root_T_self=HomogeneousTransformationMatrix.from_xyz_rpy(
                    x=0.0, y=0.0, z=0.0
                ),
                scale=Scale(x=0.678, y=0.678, z=1),
            )

            world.add_connection(root_C_turbine_1_body)




            return world




rclpy.init()
node = rclpy.create_node("kitchen_environment")
publisher = VizMarkerPublisher(_world=WindFarmEnvironment().get_world(), node=node)
publisher.with_tf_publisher()