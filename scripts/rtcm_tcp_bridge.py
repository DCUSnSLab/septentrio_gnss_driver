#!/usr/bin/env python3

import socket
import time

import rclpy
from rclpy.node import Node
from rtcm_msgs.msg import Message as RtcmMessage


class RtcmTcpBridge(Node):
    def __init__(self):
        super().__init__("rtcm_tcp_bridge")

        self.declare_parameter("host", "192.168.3.1")
        self.declare_parameter("port", 28785)
        self.declare_parameter("topic", "/rtcm")
        self.declare_parameter("connect_timeout_sec", 2.0)
        self.declare_parameter("reconnect_log_period_sec", 5.0)

        self.host = self.get_parameter("host").value
        self.port = int(self.get_parameter("port").value)
        self.topic = self.get_parameter("topic").value
        self.connect_timeout_sec = float(
            self.get_parameter("connect_timeout_sec").value
        )
        self.reconnect_log_period_sec = float(
            self.get_parameter("reconnect_log_period_sec").value
        )

        self.sock = None
        self.last_connect_log = 0.0
        self.packet_count = 0
        self.byte_count = 0

        self.subscription = self.create_subscription(
            RtcmMessage, self.topic, self.rtcm_callback, 100
        )

        self.get_logger().info(
            f"Forwarding {self.topic} RTCM messages to tcp://{self.host}:{self.port}"
        )

    def connect(self):
        if self.sock is not None:
            return True

        try:
            sock = socket.create_connection(
                (self.host, self.port), timeout=self.connect_timeout_sec
            )
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock = sock
            self.get_logger().info(f"Connected to tcp://{self.host}:{self.port}")
            return True
        except OSError as exc:
            now = time.monotonic()
            if now - self.last_connect_log >= self.reconnect_log_period_sec:
                self.last_connect_log = now
                self.get_logger().warn(
                    f"Cannot connect to tcp://{self.host}:{self.port}: {exc}"
                )
            return False

    def close_socket(self):
        if self.sock is None:
            return
        try:
            self.sock.close()
        except OSError:
            pass
        self.sock = None

    def rtcm_callback(self, msg):
        data = bytes(msg.message)
        if not data:
            return

        if not self.connect():
            return

        try:
            self.sock.sendall(data)
            self.packet_count += 1
            self.byte_count += len(data)
            if self.packet_count == 1 or self.packet_count % 100 == 0:
                self.get_logger().info(
                    f"Forwarded {self.packet_count} RTCM packets, {self.byte_count} bytes"
                )
        except OSError as exc:
            self.get_logger().warn(f"RTCM TCP write failed: {exc}; reconnecting")
            self.close_socket()

    def destroy_node(self):
        self.close_socket()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RtcmTcpBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
