import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, Float32


FRONT_HALF_ANGLE_DEG = 20.0
STOP_DISTANCE_M = 0.5


class SafetyBrakeNode(Node):

    def __init__(self):
        super().__init__('safety_brake_node')

        self.declare_parameter('front_half_angle_deg', FRONT_HALF_ANGLE_DEG)
        self.declare_parameter('stop_distance_m', STOP_DISTANCE_M)

        self._half_angle = math.radians(
            self.get_parameter('front_half_angle_deg').value
        )
        self._stop_dist = self.get_parameter('stop_distance_m').value

        self._current_speed = 0.0

        self.create_subscription(LaserScan, '/scan', self._scan_cb, 10)
        self.create_subscription(Odometry, '/localization/odom', self._odom_cb, 10)

        self._pub_stop = self.create_publisher(Bool, '/safety/stop_required', 10)
        self._pub_dist = self.create_publisher(Float32, '/safety/min_front_distance', 10)

        self.get_logger().info(
            f'safety_brake_node started | '
            f'front ±{FRONT_HALF_ANGLE_DEG:.0f}° | '
            f'stop < {STOP_DISTANCE_M} m'
        )

    def _odom_cb(self, msg: Odometry):
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        self._current_speed = math.hypot(vx, vy)

    def _scan_cb(self, msg: LaserScan):
        min_dist = self._min_front_distance(msg)

        stop_required = (min_dist < self._stop_dist)

        stop_msg = Bool()
        stop_msg.data = stop_required
        self._pub_stop.publish(stop_msg)

        dist_msg = Float32()
        dist_msg.data = float(min_dist)
        self._pub_dist.publish(dist_msg)

        if stop_required:
            self.get_logger().warn(
                f'STOP: front obstacle at {min_dist:.3f} m '
                f'(speed={self._current_speed:.2f} m/s)',
                throttle_duration_sec=0.5,
            )

    def _min_front_distance(self, msg: LaserScan) -> float:
        """Return minimum range in the forward ±half_angle sector."""
        angle = msg.angle_min
        min_dist = float('inf')

        for r in msg.ranges:
            if abs(angle) <= self._half_angle:
                if msg.range_min <= r <= msg.range_max and math.isfinite(r):
                    if r < min_dist:
                        min_dist = r
            angle += msg.angle_increment

        return min_dist if math.isfinite(min_dist) else msg.range_max


def main(args=None):
    rclpy.init(args=args)
    node = SafetyBrakeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
