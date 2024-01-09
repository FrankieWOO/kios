"""
action nodes and condition nodes that used for generating the nodes in subtrees
"""

##############################################################################
# Imports
##############################################################################

# for multiprocessing
import atexit
import multiprocessing
import multiprocessing.connection
from multiprocessing import Manager

# for abstract class
from abc import ABC, abstractmethod

# for testing
import time

# pytrees
import py_trees.common
import py_trees.console as console

# kios
from kios_utils.kios_utils import ActionPhase
from kios_utils.task import *
from kios_bt.mios_async import mios_monitor, fake_monitor
from kios_bt.data_types import ActionInstance, GroundedAction, GroundedCondition
from kios_world.world_interface import WorldInterface


##############################################################################
# Classes
##############################################################################

# * mios server address: localhost
MIOS = "127.0.0.1"


class BehaviorNode(py_trees.behaviour.Behaviour, ABC):
    """kios_bt template node."""

    def __init__(self, world_interface: WorldInterface):
        """Configure the name of the behaviour."""
        super(BehaviorNode, self).__init__(self.behavior_name)
        self.monitor = None
        self.world_interface = world_interface

    # def register_predicates(self) -> None:
    #     self.world_interface.register_predicates(self.grounded_action.effects["true"])

    # def take_effect(self):
    #     "change the predicates on the blackboard according to the set effects"
    #     self.world_interface.set_predicates(self.grounded_action.effects["true"])

    # @abstractmethod
    # def setup(self, **kwargs: int) -> None:
    #     # setup the parameters here
    #     self.logger.debug(
    #         "%s.setup()->connections to an external process" % (self.__class__.__name__)
    #     )

    # def initialise(self) -> None:
    #     # else, reset the task and start the external process
    #     self.logger.debug("%s.initialise()" % (self.__class__.__name__))
    #     # * reset the task
    #     self.task.initialize()
    #     # * launch the subprocess, start the mios skill execution
    #     self.parent_connection, self.child_connection = multiprocessing.Pipe()
    #     self.monitor = multiprocessing.Process(
    #         target=fakemonitor,
    #         args=(
    #             self.task,
    #             self.child_connection,
    #         ),
    #     )
    #     atexit.register(self.monitor.terminate)
    #     self.monitor.start()

    # def update(self) -> py_trees.common.Status:
    #     """Increment the counter, monitor and decide on a new status."""
    #     self.logger.debug("%s.update()" % (self.__class__.__name__))
    #     new_status = py_trees.common.Status.RUNNING

    #     # * check the result of the startup of the task
    #     if self.task.task_start_response is not None:
    #         if bool(self.task.task_start_response["result"]["result"]) == False:
    #             self.logger.debug("Task startup failed")
    #             new_status = py_trees.common.Status.FAILURE
    #             return new_status
    #     else:
    #         # ! this should never happen
    #         self.logger.debug("Task startup in progress")
    #         self.logger.debug("ERRORRRR")
    #         new_status = py_trees.common.Status.RUNNING
    #         return new_status

    #     # * check if the task is finished
    #     if self.parent_connection.poll():
    #         self.result = self.parent_connection.recv().pop()  # ! here only bool
    #         if self.result == True:
    #             self.logger.debug("Task finished successfully")
    #             new_status = py_trees.common.Status.SUCCESS
    #             # * exert the effects
    #             self.take_effect()
    #         else:
    #             self.logger.debug("Task finished with error")
    #             new_status = py_trees.common.Status.FAILURE
    #     return new_status

    def terminate(self, new_status: py_trees.common.Status) -> None:
        """called after execution or when interrupted."""
        # * stop the monitor process, regardless of the result
        if self.monitor is None:
            pass
            # print(self.__class__.__name__ + ": monitor is None")
        else:
            self.monitor.terminate()

        self.logger.debug(
            "%s.terminate()[%s->%s]"
            % (self.__class__.__name__, self.status, new_status)
        )


class ActionNode(BehaviorNode):
    """Demonstrates the at-a-distance style action behaviour."""

    def __init__(
        self, grounded_action: GroundedAction, world_interface: WorldInterface
    ):
        self.grounded_action = grounded_action
        """Configure the name of the behaviour."""
        action_variables = "".join(
            [f"{key}: {value}, " for key, value in grounded_action.variables.items()]
        )
        self.behavior_name = grounded_action.tag + ": " + action_variables
        super().__init__(world_interface)

        self.monitor = None

        self.register_predicates()

        self.world_interface = world_interface

        self.logger.debug("%s.__init__()" % (self.__class__.__name__))

    def register_predicates(self) -> None:
        self.world_interface.register_predicates(self.grounded_action.effects["true"])

    def take_effect(self):
        self.world_interface.set_predicates(self.grounded_action.effects["true"])

    def setup(self, **kwargs: int) -> None:
        # get the parameters from the parameter server
        self.skill_type = self.grounded_action.mios_parameters["skill_type"]
        self.skill_parameters = self.grounded_action.mios_parameters["skill_parameters"]

        # * setup the task
        self.task = Task(MIOS)
        self.task.add_skill(self.behavior_name, self.skill_type, self.skill_parameters)

        self.logger.debug("%s.setup()" % (self.__class__.__name__))

    def initialise(self) -> None:
        # else, reset the task and start the external process
        self.logger.debug("%s.initialise()" % (self.__class__.__name__))
        # * reset the task
        self.task.initialize()
        # * launch the subprocess, start the mios skill execution
        self.parent_connection, self.child_connection = multiprocessing.Pipe()
        self.monitor = multiprocessing.Process(
            target=mios_monitor,
            args=(
                self.task,
                self.child_connection,
            ),
        )
        atexit.register(self.monitor.terminate)
        self.monitor.start()

    def update(self) -> py_trees.common.Status:
        """Increment the counter, monitor and decide on a new status."""
        self.logger.debug("%s.update()" % (self.__class__.__name__))
        new_status = py_trees.common.Status.RUNNING

        # * check the result of the startup of the task
        if self.task.task_start_response is not None:
            if bool(self.task.task_start_response["result"]["result"]) == False:
                self.logger.debug("Task startup failed")
                new_status = py_trees.common.Status.FAILURE
                return new_status
        else:
            # ! this should never happen
            self.logger.debug("Task startup is still being processed.")
            self.logger.error("Lag in task startup process. pls check.")
            new_status = py_trees.common.Status.RUNNING
            return new_status

        # * check if the task is finished
        if self.parent_connection.poll():
            self.result = self.parent_connection.recv().pop()  # ! here only bool
            if self.result == True:
                self.logger.debug("Task finished successfully")
                new_status = py_trees.common.Status.SUCCESS
                # * exert the effects
                self.take_effect()
            else:
                self.logger.debug("Task finished with error")
                new_status = py_trees.common.Status.FAILURE
        return new_status

    # def terminate(self, new_status: py_trees.common.Status) -> None:
    #     """called after execution or when interrupted."""
    #     # * stop the monitor process, regardless of the result
    #     if self.monitor is None:
    #         self.logger.info(self.__class__.__name__ + ": monitor is None")
    #     else:
    #         self.monitor.terminate()

    #     self.logger.debug(
    #         "%s.terminate()[%s->%s]"
    #         % (self.__class__.__name__, self.status, new_status)
    #     )


class ConditionNode(BehaviorNode):
    """abstract condition node."""

    def __init__(
        self, grounded_condition: GroundedCondition, world_interface: WorldInterface
    ):
        self.grounded_condition = grounded_condition
        """Configure the name of the behaviour."""
        self.behavior_name = grounded_condition.tag
        super().__init__(world_interface)

        self.world_interface = world_interface
        self.logger.debug("%s.__init__()" % (self.__class__.__name__))

    def register_predicates(self) -> None:
        self.world_interface.register_predicates(
            {self.grounded_condition.name: self.grounded_condition.variables}
        )

    def setup(self, **kwargs: int) -> None:
        # register the predicates on the blackboard here
        self.register_predicates()
        self.logger.debug(
            "%s.setup()->register the predicates" % (self.__class__.__name__)
        )

    def initialise(self) -> None:
        self.logger.debug("%s.initialise()" % (self.__class__.__name__))
        # * may implement some observing actions here
        # nothing to do here

    def update(self) -> py_trees.common.Status:
        """Increment the counter, monitor and decide on a new status."""
        self.logger.debug("%s.update()" % (self.__class__.__name__))
        new_status = py_trees.common.Status.SUCCESS

        result = self.world_interface.check_condition(self.grounded_condition)

        if result == True:
            new_status = py_trees.common.Status.SUCCESS
        else:
            new_status = py_trees.common.Status.FAILURE

        return new_status

    # def terminate(self, new_status: py_trees.common.Status) -> None:
    #     """called after execution or when interrupted."""
    #     # nothing to do here

    #     self.logger.debug(
    #         "%s.terminate()[%s->%s]"
    #         % (self.__class__.__name__, self.status, new_status)
    #     )


# !  discarded
class ToolPick(ActionNode):
    """BBToolPick behaviour."""

    def __init__(self, objects_: list):
        """Configure the name of the behaviour."""

        self.objects_ = {
            "target": objects_[0],
        }

        self.node_name = "ToolPick"
        self.target_name = objects_[0]
        super(ToolPick, self).__init__()

        self.logger.debug("%s.__init__()" % (self.__class__.__name__))

    # ! you must override this
    def set_effects(self) -> None:
        self.effects = {
            "inTool": self.objects_["target"],
        }

    # ! you must override this
    def setup(self, **kwargs: int) -> None:
        # get the parameters from the parameter server
        # ! test, parameters given
        self.skill_type = "BBGripperForce"
        self.skill_parameters = {
            "skill": {
                "objects": {"Pick": self.objects_["target"]},
                "time_max": 30,
                # "action_context": {
                #     "action_name": "BBPick",
                #     "action_phase": "TOOL_PICK",  # Adjusted for Python enum style
                # },
                "MoveAbove": {
                    "dX_d": [0.2, 0.2],
                    "ddX_d": [0.2, 0.2],
                    "DeltaX": [0, 0, 0, 0, 0, 0],
                    "K_x": [1500, 1500, 1500, 600, 600, 600],
                },
                "MoveIn": {
                    "dX_d": [0.2, 0.2],
                    "ddX_d": [0.1, 0.1],
                    "DeltaX": [0, 0, 0, 0, 0, 0],
                    "K_x": [1500, 1500, 1500, 600, 600, 600],
                },
                "GripperForce": {
                    "width": 0.016,
                    "speed": 1,
                    "force": 120,
                    "K_x": [1500, 1500, 1500, 100, 100, 100],
                    "eps_in": 0,  # 0.016
                    "eps_out": 0.022,  # 0.038
                },
                "Retreat": {
                    "dX_d": [0.2, 0.2],
                    "ddX_d": [0.1, 0.1],
                    "DeltaX": [0, 0, 0, 0, 0, 0],
                    "K_x": [1500, 1500, 1500, 600, 600, 600],
                },
            },
            "control": {"control_mode": 0},
            "user": {
                "env_X": [0.01, 0.01, 0.002, 0.05, 0.05, 0.05],
                "env_dX": [0.001, 0.001, 0.001, 0.005, 0.005, 0.005],
                "F_ext_contact": [3.0, 2.0],
            },
        }

        # * setup the task
        self.task = Task(MIOS)
        self.task.add_skill("bbskill", self.skill_type, self.skill_parameters)

        self.logger.debug("%s.setup()" % (self.__class__.__name__))


class ActionNodeTest(ActionNode):
    def __init__(
        self, grounded_action: GroundedAction, world_interface: WorldInterface
    ):
        super().__init__(grounded_action, world_interface)

    def register_predicates(self) -> None:
        self.world_interface.register_predicates(self.grounded_action.effects["true"])

    def take_effect(self):
        self.world_interface.set_predicates(self.grounded_action.effects["true"])

    def setup(self, **kwargs: int) -> None:
        # get the parameters from the parameter server
        self.skill_type = self.grounded_action.mios_parameters["skill_type"]
        self.skill_parameters = self.grounded_action.mios_parameters["skill"]

        # * setup the task
        self.task = Task(MIOS)
        self.task.add_skill(self.behavior_name, self.skill_type, self.skill_parameters)

        self.logger.debug("%s.setup()" % (self.__class__.__name__))

    def initialise(self) -> None:
        # else, reset the task and start the external process
        self.logger.debug("%s.initialise()" % (self.__class__.__name__))
        # * reset the task
        self.task.initialize()
        # * launch the subprocess, start the mios skill execution
        self.parent_connection, self.child_connection = multiprocessing.Pipe()
        self.monitor = multiprocessing.Process(
            target=fake_monitor,
            args=(
                self.task,
                self.child_connection,
            ),
        )
        atexit.register(self.monitor.terminate)
        self.monitor.start()

    def update(self) -> py_trees.common.Status:
        """Increment the counter, monitor and decide on a new status."""
        self.logger.debug("%s.update()" % (self.__class__.__name__))
        new_status = py_trees.common.Status.RUNNING

        # * check the result of the startup of the task
        if self.task.task_start_response is not None:
            if bool(self.task.task_start_response["result"]["result"]) == False:
                self.logger.debug("Task startup failed")
                new_status = py_trees.common.Status.FAILURE
                return new_status
        else:
            # ! this should never happen
            self.logger.debug("Task startup is still being processed.")
            self.logger.error("Lag in task startup process. pls check.")
            new_status = py_trees.common.Status.RUNNING
            return new_status

        # * check if the task is finished
        if self.parent_connection.poll():
            self.result = self.parent_connection.recv().pop()  # ! here only bool
            if self.result == True:
                self.logger.debug("Task finished successfully")
                new_status = py_trees.common.Status.SUCCESS
                # * exert the effects
                self.take_effect()
            else:
                self.logger.debug("Task finished with error")
                new_status = py_trees.common.Status.FAILURE
        return new_status


##############################################################################
# Main
##############################################################################


def main() -> None:
    """Entry point for the demo script."""

    py_trees.logging.level = py_trees.logging.Level.DEBUG

    action = ActionNode(name="Action")
    action.setup()
    try:
        for _unused_i in range(0, 12):
            action.tick_once()
            time.sleep(0.5)
        print("\n")
    except KeyboardInterrupt:
        pass
