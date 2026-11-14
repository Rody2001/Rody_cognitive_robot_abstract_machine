"""
The HSR drives from its start to a goal pose in the kitchen environment, in MuJoCo.

Run it from this folder::

    python demo_in_kitchen.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from typing_extensions import TYPE_CHECKING

from coraplex.demonstrations import RobotDemonstration
from coraplex.plans.context_extensions import RobotAccess
from coraplex.plans.executors import PhysicallySimulatedPlanExecutor
from coraplex.robot_plans.actions.core.navigation import NavigateAction
from coraplex.robot_plans.actions.core.robot_body import ParkArmsAction
from cramph.composites import Sequence
from cramph.statechart import Statechart
from krrood_spatial_math.spatial_types import HomogeneousTransformationMatrix, Pose
from semantic_digital_twin.collision_checking.collision_rules import (
    AllowCollisionBetweenGroups,
)
from semantic_digital_twin.predefined_maps.kitchen_environment import KitchenEnvironment
from semantic_digital_twin.robots.hsrb import HSRB
from semantic_digital_twin.semantic_annotations.semantic_annotations import Floor
from semantic_digital_twin.specifications.robots import RobotSpecification
from semantic_digital_twin.specifications.worlds import WorldSpecification

if TYPE_CHECKING:
    from coraplex.plans.executors import PlanExecutor
    from cramph.context import ContextExtension, StatechartContext
    from semantic_digital_twin.robots.robot_parts import AbstractRobot
    from semantic_digital_twin.world import World

# %% the scene


class SceneBody(StrEnum):
    """
    The names of the kitchen bodies the demonstration refers to.
    """

    SOFA = "sofa"
    """
    The sofa of the kitchen environment, which marks whether the scene is already loaded.
    """


# %% the demonstration


@dataclass
class KitchenNavigationDemonstration(RobotDemonstration):
    """
    The HSR parks its arm and drives from :attr:`robot_start` to :attr:`goal`.
    """

    used_robot: type[AbstractRobot] = HSRB
    """
    The robot that drives.
    """

    ros_node_name: str = "hsr_kitchen_navigation_demo"
    """
    Name of the node this demonstration registers.
    """

    executor_type: type[PlanExecutor] = PhysicallySimulatedPlanExecutor
    """
    The executor running the plan, which performs it in MuJoCo.
    """

    collision_avoidance: bool = True
    """
    Whether collision avoidance is added to every motion state chart of this run.
    """

    event_segmentation: bool = False
    """
    Whether the events of this run are segmented; there is nothing to segment here.
    """

    robot_start: HomogeneousTransformationMatrix = field(
        default_factory=lambda: HomogeneousTransformationMatrix.from_xyz_rpy(
            x=-0.178202, y=3.60589
        )
    )
    """
    Where the HSR stands before the plan begins.
    """

    goal_x: float = 5.0
    """
    Where the HSR drives to along the world's x axis, in meters.
    """

    goal_y: float = 5.0
    """
    Where the HSR drives to along the world's y axis, in meters.
    """

    goal_yaw: float = 0.0
    """
    Which way the HSR faces at the goal, in radians around the world's z axis.
    """

    def scene_specification(self) -> WorldSpecification:
        return WorldSpecification(world_source=KitchenEnvironment())

    def robot_specification(self) -> RobotSpecification:
        return RobotSpecification(
            semantic_annotation_type=self.used_robot,
            odometry_T_robot_start=self.robot_start,
        )

    def is_scene_populated(self, world: World) -> bool:
        return world.is_kinematic_structure_entity_in_world_by_name(SceneBody.SOFA)

    def acquire_world(self) -> World:
        """
        Obtain the world as :meth:`RobotDemonstration.acquire_world` does, in which the
        whole HSR may touch the kitchen's floors.
        """
        world = super().acquire_world()
        [robot] = world.get_semantic_annotations_by_type(self.used_robot)
        with world.modify_world():
            world.collision_manager.add_ignore_collision_rule(
                AllowCollisionBetweenGroups(
                    body_group_a=robot.bodies_with_collision,
                    body_group_b=[
                        floor.root
                        for floor in world.get_semantic_annotations_by_type(Floor)
                    ],
                )
            )
        return world

    def build_context_extensions(self, world: World) -> list[ContextExtension]:
        return [RobotAccess(world.get_semantic_annotations_by_type(self.used_robot)[0])]

    def build_statechart(self, context: StatechartContext) -> Statechart:
        robot = context.require_extension(RobotAccess).robot
        goal = Pose.from_xyz_rpy(
            x=self.goal_x,
            y=self.goal_y,
            yaw=self.goal_yaw,
            reference_frame=context.world.root,
        )
        statechart = Statechart(context=context)
        statechart.add_node(
            Sequence(
                nodes=[
                    ParkArmsAction(arms=robot.all_arms),
                    NavigateAction(target_location=goal),
                ]
            )
        )
        return statechart


def main(headless: bool = False) -> World:
    """
    Run the demonstration.

    :param headless: Whether the physics runs without a viewer.
    :return: The world the HSR drove in.
    """
    return KitchenNavigationDemonstration(headless=headless).run()


if __name__ == "__main__":
    main()
