#!/usr/bin/env python2

import rospy
from std_srvs.srv import Empty
from geometry_msgs.msg import Twist, PoseStamped
from sensor_msgs.msg import Joy
from nav_msgs.msg import Odometry
from RVO import RVO_update, reach, compute_V_des, reach
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import SetModelState, GetModelState
import math
import tf
import numpy as np
import os
import pickle as pkl


class BoatHRVO(object):
    def __init__(self):
        self.node_name = rospy.get_name()
        rospy.loginfo("[%s] Initializing" % self.node_name)
        self.frame = "map"
        self.frame1 = "map"
        self.auto = 0
        self.num = 5

        self.reset_world = rospy.ServiceProxy('/gazebo/reset_world', Empty)
        self.reset_model = rospy.ServiceProxy(
            '/gazebo/set_model_state', SetModelState)

        # setup publisher
        self.pub_v = rospy.Publisher("/wamv1/cmd_vel_hrvo", Twist, queue_size=1)
        self.sub_p3d = rospy.Subscriber(
            "/wamv1/localization_gps_imu/odometry", Odometry, self.cb_boat_odom, queue_size=1)
        self.sub_goal = rospy.Subscriber("/wamv1/move_base_simple/goal", PoseStamped, self.cb_goal, queue_size=1)

        self.pub_v1 = rospy.Publisher("/wamv2/cmd_vel_hrvo", Twist, queue_size=1)
        self.sub_p3d1 = rospy.Subscriber(
            "/wamv2/localization_gps_imu/odometry", Odometry, self.cb_boat1_odom, queue_size=1)
        self.sub_goal1 = rospy.Subscriber("/wamv2/move_base_simple/goal", PoseStamped, self.cb_goal1, queue_size=1)
        
        
        self.pub_v2 = rospy.Publisher("/wamv3/cmd_vel_hrvo", Twist, queue_size=1)
        self.sub_p3d2 = rospy.Subscriber(
            "/wamv3/localization_gps_imu/odometry", Odometry, self.cb_boat2_odom, queue_size=1)
        self.sub_goal2 = rospy.Subscriber("/wamv3/move_base_simple/goal", PoseStamped, self.cb_goal2, queue_size=1)

        self.pub_v3 = rospy.Publisher("/wamv4/cmd_vel_hrvo", Twist, queue_size=1)
        self.sub_p3d3 = rospy.Subscriber(
            "/wamv4/localization_gps_imu/odometry", Odometry, self.cb_boat3_odom, queue_size=1)
        self.sub_goal3 = rospy.Subscriber("/wamv4/move_base_simple/goal", PoseStamped, self.cb_goal3, queue_size=1)


        self.pub_v4 = rospy.Publisher("/wamv5/cmd_vel_hrvo", Twist, queue_size=1)
        self.sub_p3d4 = rospy.Subscriber(
            "/wamv5/localization_gps_imu/odometry", Odometry, self.cb_boat4_odom, queue_size=1)
        self.sub_goal4 = rospy.Subscriber("/wamv5/move_base_simple/goal", PoseStamped, self.cb_goal4, queue_size=1)
        
        self.sub_joy = rospy.Subscriber("/joy", Joy, self.cb_joy, queue_size=1)
        # initiallize boat status
        self.boat_odom = [Odometry() for i in range(self.num)]
        self.cmd_drive = [Twist() for i in range(self.num)]
        self.yaw = [0 for i in range(self.num)]
        # initiallize HRVO environment
        self.ws_model = dict()
        # robot radius
        self.ws_model['robot_radius'] = 3
        self.ws_model['circular_obstacles'] = []
        #obstacle\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.right_start = (-57,-170)
        self.right_end = (-57,-125)
        self.left_start = (-57,-205)
        self.left_end = (-57,-230)
        self.radius = 5
        self.right_point = abs(self.right_start[1]-self.right_end[1])/self.radius
        self.right_x = abs(self.right_start[0]-self.right_end[0])/self.right_point 
        for point in range(self.right_point+1):
            #print(point)
            self.ws_model['circular_obstacles'].append((self.right_start[0]+(self.right_x*point),self.right_start[1]+(self.radius*point),self.radius))

        self.left_point = abs(self.left_start[1]-self.left_end[1])/self.radius
        self.left_x = abs(self.left_start[0]-self.left_end[0])/self.left_point 
        for point in range(self.left_point+1):
            #print(point)
            self.ws_model['circular_obstacles'].append((self.left_start[0]-(self.left_x*point),self.left_start[1]-(self.radius*point),self.radius))

        
        self.ws_model['circular_obstacles'].append((-55,-202,2))
        self.ws_model['circular_obstacles'].append((-59,-202,2))
        self.ws_model['circular_obstacles'].append((-55,-200,2))
        self.ws_model['circular_obstacles'].append((-59,-200,2))
        self.ws_model['circular_obstacles'].append((-55,-198,2))
        self.ws_model['circular_obstacles'].append((-59,-198,2))
        self.ws_model['circular_obstacles'].append((-55,-196,2))
        self.ws_model['circular_obstacles'].append((-59,-196,2))
        #////////////////
        self.ws_model['circular_obstacles'].append((-61,-198,2))
        self.ws_model['circular_obstacles'].append((-59,-196,2))

        self.ws_model['circular_obstacles'].append((-61,-196,2))
        self.ws_model['circular_obstacles'].append((-63,-195,2))

        #/////////////////////////
        self.ws_model['circular_obstacles'].append((-55,-172,2))
        self.ws_model['circular_obstacles'].append((-59,-172,2))
        self.ws_model['circular_obstacles'].append((-55,-175,3))
        self.ws_model['circular_obstacles'].append((-59,-175,3))
        self.ws_model['circular_obstacles'].append((-55,-178,3))
        self.ws_model['circular_obstacles'].append((-59,-178,2))

        ###########################################################################
        # self.ws_model['circular_obstacles'].append((-55,-166,2))
        # self.ws_model['circular_obstacles'].append((-59,-166,2))
        # self.ws_model['circular_obstacles'].append((-62,-166,1))
        # self.ws_model['circular_obstacles'].append((-61,-166,1))
        print(self.ws_model['circular_obstacles'])

        #\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        # rectangular boundary, format [x,y,width/2,heigth/2]
        self.ws_model['boundary'] = [-57,-180,50,25]

        self.position = []
        self.goal = [[0, 0] for i in range(self.num)]
        # print(self.position)
        # print(self.goal)
        self.velocity = [[0, 0] for i in range(self.num)]
        self.velocity_detect = [[0, 0] for i in range(self.num)]
        self.v_max = [1 for i in range(self.num)]

        # timer
        self.timer = rospy.Timer(rospy.Duration(0.1), self.cb_hrvo)

    def cb_hrvo(self, event):
        if self.goal[0] == [0,0] and self.goal[1]==[0,0]:
            return
        if self.auto == 0:
            return
        self.update_all()
        print(self.goal)
        v_des = compute_V_des(self.position, self.goal, self.v_max)
        self.velocity = RVO_update(
            self.position, v_des, self.velocity_detect, self.ws_model)

        for i in range(self.num):
            dis, angle = self.process_ang_dis(
                self.velocity[i][0], self.velocity[i][1], self.yaw[i])
            ##p3d 0.35 0.8
            cmd = Twist()
            cmd.linear.x = dis * 0.35
            cmd.angular.z = angle * 0.95
            if i ==3:
                cmd.linear.x = dis * 0.25
                cmd.angular.z = angle * 1.425
            self.cmd_drive[i] = cmd

        self.pub_v.publish(self.cmd_drive[0])
        self.pub_v1.publish(self.cmd_drive[1])
        self.pub_v2.publish(self.cmd_drive[2])
        self.pub_v3.publish(self.cmd_drive[3])
        self.pub_v4.publish(self.cmd_drive[4])

    def check_state(self):
        min_dis = 1e9
        done = True
        for i in range(self.num):
            p = np.array(self.position[i])
            g = np.array(self.goal[i])
            d2g = np.linalg.norm(p-g)
            done = True if d2g < 2 else False
            for k in range(i+1, self.num):
                p1 = np.array(self.position[i])
                p2 = np.array(self.position[k])
                dis = np.linalg.norm(p1-p2)
                min_dis = dis if dis < min_dis else min_dis
        return min_dis, done

    def process_ang_dis(self, vx, vy, yaw):
        dest_yaw = math.atan2(vy, vx)

        angle = dest_yaw - yaw
        if angle > np.pi:
            angle = angle-2*np.pi

        if angle < -np.pi:
            angle = angle+2*np.pi

        angle = angle/np.pi

        dis = math.sqrt(vx**2+vy**2)

        # print "pos      %2.2f, %2.2f" % (self.position[0][0], self.position[0][1])
        # print "goal     %2.2f, %2.2f" % (self.goal[0][0], self.goal[0][1])
        # print "dest_yaw %2.2f" % dest_yaw
        # print "yaw      %2.2f" % yaw
        # print "angle    %2.2f" % angle
        # print "dis      %2.2f\n" % dis

        dis = max(min(dis, 1), -1)
        angle = max(min(angle, 1), -1)

        return dis, angle

    def update_all(self):
        self.position = []
        for i in range(self.num):
            # update position
            pos = [self.boat_odom[i].pose.pose.position.x,
                   self.boat_odom[i].pose.pose.position.y]
            self.position.append(pos)

            # update orientation
            quaternion = (self.boat_odom[i].pose.pose.orientation.x,
                          self.boat_odom[i].pose.pose.orientation.y,
                          self.boat_odom[i].pose.pose.orientation.z,
                          self.boat_odom[i].pose.pose.orientation.w)
            euler = tf.transformations.euler_from_quaternion(quaternion)
            self.yaw[i] = euler[2]

            # update velocity
            self.velocity_detect[i] = [self.boat_odom[i].twist.twist.linear.x,
                                       self.boat_odom[i].twist.twist.linear.y]
    def cb_goal(self, msg):
        if msg.header.frame_id != self.frame:
            self.goal[0] = None
            return
        self.goal[0] = [msg.pose.position.x, msg.pose.position.y]

    def cb_goal1(self, msg):
        if msg.header.frame_id != self.frame:
            self.goal[1] = None
            return
        self.goal[1] = [msg.pose.position.x, msg.pose.position.y]

    def cb_goal2(self, msg):
        if msg.header.frame_id != self.frame:
            self.goal[2] = None
            return
        self.goal[2] = [msg.pose.position.x, msg.pose.position.y]

    def cb_goal3(self, msg):
        if msg.header.frame_id != self.frame:
            self.goal[3] = None
            return
        self.goal[3] = [msg.pose.position.x, msg.pose.position.y]

    def cb_goal4(self, msg):
        if msg.header.frame_id != self.frame:
            self.goal[4] = None
            return
        self.goal[4] = [msg.pose.position.x, msg.pose.position.y]
    
    def cb_joy(self, msg):
        start_button = 7
        back_button = 6

        if (msg.buttons[start_button] == 1) and not self.auto:
            self.auto = 1
            rospy.loginfo('go auto')
        elif msg.buttons[back_button] == 1 and self.auto:
            self.auto = 0
            rospy.loginfo('go manual')
    
    def cb_boat_odom(self, msg):
        self.boat_odom[0] = msg

    def cb_boat1_odom(self, msg):
        self.boat_odom[1] = msg

    def cb_boat2_odom(self, msg):
        self.boat_odom[2] = msg

    def cb_boat3_odom(self, msg):
        self.boat_odom[3] = msg

    def cb_boat4_odom(self, msg):
        self.boat_odom[4] = msg


if __name__ == "__main__":
    rospy.init_node("BoatHRVO")
    boatHRVO = BoatHRVO()
    rospy.spin()
