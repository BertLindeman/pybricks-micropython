# SPDX-License-Identifier: MIT
# Copyright (c) 2022 The Pybricks Authors

from ..drv.button import VirtualButtons
from ..drv.battery import VirtualBattery
from ..drv.led import VirtualLed
from ..drv.clock import CountingClock
from ..drv.ioport import VirtualIOPort, PortId, IODeviceTypeId

import numpy
import random
import math

from ..physics.motors import SimpleMotor as SimMotor


class VirtualMotorDriver:
    """
    Virtual motor driver chip implementation, with optionally a (simulated)
    dc motor attached to its output wires.
    """

    def __init__(self, sim_motor):
        self.sim_motor = sim_motor

    def on_coast(self, *args):
        """
        Called when ``pbdrv_motor_driver_coast()`` is called.
        """
        # For now, actuates just as 0 duty.
        self.on_set_duty_cycle(args[0], 0)

    def on_set_duty_cycle(self, *args):
        """
        Called when ``pbdrv_motor_driver_set_duty_cycle()`` is called.
        """

        # Nothing to do if there is no motor.
        if self.sim_motor is None:
            return

        # Simulate the motor up to the current time, plus 5 milliseconds.
        end_time = args[0] / 1000000 + 0.005
        u = numpy.array([args[1]])
        self.sim_motor.simulate(end_time, u)


class VirtualCounter:
    """
    Virtual counter driver implementation, with optionally a (simulated)
    dc motor with rotation sensors attached to it.
    """

    def __init__(self, sim_motor):
        self.sim_motor = sim_motor

        # Nothing left to do if there is no motor.
        if self.sim_motor is None:
            return

        # Since all counter drivers count 0 from the point where it started,
        # we need to keep track of the starting point.
        self.initial_angle, speed = self.sim_motor.get_latest_output()

    @property
    def abs_count(self):
        """
        Provides the value for ``pbdrv_counter_virtual_get_abs_count()``.
        """
        # Return 0 if there is no motor.
        if self.sim_motor is None:
            return 0

        # Return the latest available data from the simulation model.
        angle, speed = self.sim_motor.get_latest_output()

        abs_angle = angle % 360
        return abs_angle if abs_angle < 180 else abs_angle - 360

    @property
    def count(self):
        """
        Provides the value for ``pbdrv_counter_virtual_get_count()``.
        """

        # Return 0 if there is no motor.
        if self.sim_motor is None:
            return 0

        # Get the latest available data from the simulation model.
        angle, speed = self.sim_motor.get_latest_output()

        # Counter drivers count from the angle where they started.
        return angle - self.initial_angle

    @property
    def rate(self):
        """
        Provides the value for ``pbdrv_counter_virtual_get_rate()``.
        """
        # Return 0 if there is no motor.
        if self.sim_motor is None:
            return 0

        # Return the latest available data from the simulation model.
        angle, speed = self.sim_motor.get_latest_output()
        return speed


class Platform:

    # Ports and attached devices.
    PORTS = {
        PortId.A: IODeviceTypeId.TECHNIC_L_ANGULAR_MOTOR,
        PortId.B: IODeviceTypeId.NONE,
        PortId.C: IODeviceTypeId.NONE,
        PortId.D: IODeviceTypeId.NONE,
        PortId.E: IODeviceTypeId.NONE,
        PortId.F: IODeviceTypeId.NONE,
    }

    def on_poll(self, *args):
        # Push clock forward by one tick on each poll.
        self.clock[-1].tick()

    def __init__(self):

        # Initialize devices internal to the hub.
        self.battery = {-1: VirtualBattery()}
        self.button = {-1: VirtualButtons()}
        self.clock = {-1: CountingClock(start=0, fuzz=0)}
        self.led = {0: VirtualLed()}

        # Initialize all ports
        self.ioport = {}
        self.counter = {}
        self.motor_driver = {}
        self.sim_motor = {}

        for i, (port_id, type_id) in enumerate(self.PORTS.items()):
            # Initialize IO Port.
            self.ioport[port_id] = VirtualIOPort(port_id)
            self.ioport[port_id].motor_type_id = type_id

            # Initialize motor simulation model.
            self.sim_motor[i] = None
            if type_id != IODeviceTypeId.NONE:

                # Get current time.
                initial_time = self.clock[-1].microseconds / 1000000

                # Random initial motor angle with zero speed.
                initial_angle = random.randint(-180, 179)
                initial_speed = 0
                initial_state = numpy.array(
                    [
                        math.radians(initial_angle),
                        math.radians(initial_speed),
                    ]
                )

                # Initialize simulated motor.
                self.sim_motor[i] = SimMotor(t0=initial_time, x0=initial_state)

            # Initialize counter and motor drivers with the given motor.
            self.counter[i] = VirtualCounter(self.sim_motor[i])
            self.motor_driver[i] = VirtualMotorDriver(self.sim_motor[i])
