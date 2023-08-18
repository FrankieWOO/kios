import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.qos import qos_profile_sensor_data

import asyncio
import websockets
import socket
import time
from datetime import datetime
import json

import queue

from .resource.ws_client import *

from kios_interface.msg import MiosState


class MiosReader(Node):

    udp_subscriber = ''
    # robot state variable dictionary.
    mios_state_default = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]

    def __init__(self):
        super().__init__('mios_reader')

        # declare parameters
        self.declare_parameter('power', True)

        skill_timer_group = MutuallyExclusiveCallbackGroup()

        timer_callback_group = MutuallyExclusiveCallbackGroup()
        publisher_callback_group = timer_callback_group

        # udp settings
        self.udp_ip = "localhost"
        self.udp_port = 12346
        self.skill_port = 8888

        self.skill_timer = self.create_timer(
            0.005,  # sec
            self.skill_timer_callback,
            callback_group=skill_timer_group)

        self.timer = self.create_timer(
            0.01,  # sec
            self.timer_callback,
            callback_group=timer_callback_group)

        self.publisher = self.create_publisher(
            MiosState,
            'mios_state_topic',
            10,
            callback_group=publisher_callback_group
        )

        # self.msg_queue = queue.Queue()

        self.udp_setup()

    def timer_callback(self):
        if self.check_power():
            data, addr = self.udp_subscriber.recvfrom(1024)
            self.get_logger().info("Received message: %s" % data.decode())
            mios_state = json.loads(data.decode())
            # publish msg
            msg = MiosState()
            msg.tf_f_ext_k = mios_state["TF_F_ext_K"]
            self.publisher.publish(msg)
            self.get_logger().info("Published RobotState to topic")
            print("check: ", mios_state["TF_F_ext_K"][2],
                  "sender time: ", mios_state["system_time"],
                  "receiver time: ", datetime.now())
        else:
            self.get_logger().error('Power off, timer pass ...')
            pass

    def skill_timer_callback(self):
        pass

    def udp_setup(self):
        self.get_logger().info('udp setup hit.')
        self.udp_subscriber = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_subscriber.bind((self.udp_ip, self.udp_port))

        self.skill_rcv = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)
        self.skill_rcv.bind((self.udp_ip, self.skill_port))

        self.switch_power(turn_on=True)

    def check_power(self):
        if self.has_parameter('power'):
            self.get_logger().error('CHECK POWER')
            return self.get_parameter('power').get_parameter_value().bool_value
        else:
            self.get_logger().error('PARAM MISSING: POWER!')

    def switch_power(self, turn_on: bool):
        power = rclpy.parameter.Parameter(
            'power',
            rclpy.Parameter.Type.BOOL,
            turn_on
        )
        all_new_parameters = [power]
        self.set_parameters(all_new_parameters)


def main(args=None):
    rclpy.init(args=args)

    mios_reader = MiosReader()

    executor = MultiThreadedExecutor()
    executor.add_node(mios_reader)

    executor.spin()

    mios_reader.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()