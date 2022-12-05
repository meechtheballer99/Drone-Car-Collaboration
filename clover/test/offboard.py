import rospy
import pytest
from pytest import approx
import threading
import mavros_msgs.msg
from geometry_msgs.msg import PoseStamped
from clover import srv
from math import nan

@pytest.fixture()
def node():
    return rospy.init_node('offboard_test', anonymous=True)

def test_offboard(node):
    navigate = rospy.ServiceProxy('navigate', srv.Navigate)
    get_telemetry = rospy.ServiceProxy('get_telemetry', srv.GetTelemetry)
    res = navigate()
    assert res.success == False
    assert res.message.startswith('State timeout')

    telem = get_telemetry()
    assert telem.connected == False

    state_pub = rospy.Publisher('/mavros/state', mavros_msgs.msg.State, latch=True, queue_size=1)
    state_msg = mavros_msgs.msg.State(mode='OFFBOARD', armed=True)

    def publish_state():
        r = rospy.Rate(2)
        while not rospy.is_shutdown():
            state_msg.header.stamp = rospy.Time.now()
            state_pub.publish(state_msg)
            r.sleep()

    # start publishing state
    threading.Thread(target=publish_state, daemon=True).start()
    rospy.sleep(0.5)

    telem = get_telemetry()
    assert telem.connected == False

    res = navigate()
    assert res.success == False
    assert res.message.startswith('No connection to FCU')

    state_msg.connected = True
    rospy.sleep(1)

    telem = get_telemetry()
    assert telem.connected == True

    res = navigate()
    assert res.success == False
    assert res.message.startswith('No local position')

    local_position_pub = rospy.Publisher('/mavros/local_position/pose', PoseStamped, latch=True, queue_size=1)
    local_position_msg = PoseStamped()
    local_position_msg.header.frame_id = 'map'
    local_position_msg.pose.orientation.w = 1

    def publish_local_position():
        r = rospy.Rate(30)
        while not rospy.is_shutdown():
            local_position_msg.header.stamp = rospy.Time.now()
            local_position_pub.publish(local_position_msg)
            r.sleep()

    # start publishing local position
    threading.Thread(target=publish_local_position, daemon=True).start()
    rospy.sleep(0.5)

    res = navigate()
    assert res.success == True