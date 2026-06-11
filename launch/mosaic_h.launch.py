import os
import launch
from launch_ros.actions import Node
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command, TextSubstitution
from ament_index_python.packages import get_package_share_directory

os.environ['RCUTILS_CONSOLE_OUTPUT_FORMAT'] = '{time}: [{name}] [{severity}]\t{message}'
# Verbose log:
#os.environ['RCUTILS_CONSOLE_OUTPUT_FORMAT'] = '{time}: [{name}] [{severity}]\t{message} ({function_name}() at {file_name}:{line_number})'

# Start as component:

def generate_launch_description():
    
    tf_imu = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments = "0 0 0 0 0 0 base_link imu".split(' ')
    )

    # Dual-antenna heading setup (ROS ENU axes: +x forward, +y left).
    # Only the DIRECTION of the main->aux baseline matters here; the driver
    # derives heading/pitch offset from it (rosaic_node.cpp:354-365). The
    # baseline LENGTH is measured by the receiver via GNSS, so the magnitudes
    # below are placeholders. Main antenna mounted at the front, Aux at the
    # rear -> baseline points backward -> heading_offset = 180 deg.
    tf_gnss = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments = "0.5 0 0 0 0 0 imu gnss_antenna".split(' ')
    )

    tf_vsm = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments = "0 0 0 0 0 0 imu vsm".split(' ')
    )

    tf_aux1 = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments = "-0.75 0 0 0 0 0 imu gnss_aux".split(' ')
    )

    default_file_name = 'mosaic_h.yaml'
    name_arg_file_name = "file_name"
    arg_file_name = DeclareLaunchArgument(name_arg_file_name,
                                          default_value=TextSubstitution(text=str(default_file_name)))
    name_arg_file_path = 'path_to_config'
    arg_file_path = DeclareLaunchArgument(name_arg_file_path,
                                          default_value=[get_package_share_directory('septentrio_gnss_driver'), '/config/', LaunchConfiguration(name_arg_file_name)])

    composable_node = ComposableNode(
        name='septentrio_gnss_driver',
        package='septentrio_gnss_driver', 
        plugin='rosaic_node::ROSaicNode',
        #emulate_tty=True,
        parameters=[LaunchConfiguration(name_arg_file_path)])

    container = ComposableNodeContainer(
        name='septentrio_gnss_driver_container',
        namespace='septentrio_gnss_driver',
        package='rclcpp_components',
        executable='component_container_isolated',
        emulate_tty=True,
        sigterm_timeout = '20',
        composable_node_descriptions=[composable_node],
        output='screen'
    )

    rtcm_bridge = Node(
        package='septentrio_gnss_driver',
        executable='rtcm_tcp_bridge.py',
        name='rtcm_tcp_bridge',
        output='screen',
    )

    return launch.LaunchDescription([
        arg_file_name,
        arg_file_path,
        container,
        rtcm_bridge,
        tf_imu,
        tf_gnss,
        tf_vsm,
        tf_aux1,
    ])
