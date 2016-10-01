#! /usr/bin/env python
from __future__ import division, print_function, absolute_import
import sys
import rospy
from pap.jaco import Jaco
from pap.manager import PickAndPlaceNode
from kinova_msgs.msg import JointAngles, PoseVelocity

from std_msgs.msg import Header, Int32MultiArray, Bool
from geometry_msgs.msg import Pose, PoseStamped, Point, Quaternion
import numpy as np

import pose_action_client
import fingers_action_client

import tf

class pick_peas_class(object):
    def __init__(self):
        self.j = Jaco()
        self.listen = tf.TransformListener()
        self.current_joint_angles = [0]*6


        # self.sub3 = rospy.Subscriber('/sensor_values', Int32MultiArray,
        #                              self.callback_1, queue_size=1)

        self.cart_vel_pub = rospy.Publisher('/j2n6a300_driver/in/cartesian_velocity',
                                                            PoseVelocity, queue_size=1)

        self.obj_det_sub = rospy.Subscriber('/finger_sensor/obj_detected',
                                            Bool,
                                            self.set_obj_det)

        self.finger_m_touch_sub = rospy.Subscriber('/finger_sensor_middle/touch',
                                                    Bool,
                                                    self.set_m_touch)

        self.finger_r_touch_sub = rospy.Subscriber('/finger_sensor_right/touch',
                                            Bool,
                                            self.set_r_touch)
        self.obj_det = False
        self.m_touch = False
        self.r_touch = False

        self.joint_angles_sub = rospy.Subscriber("/j2n6a300_driver/out/joint_angles",
                                                                JointAngles, self.callback)


        # self.touch_r_sub = rospy.Subscriber("/finger_sensor_right/touch",
        #                                 Bool,
        #                                 queue_size=1)
        #
        # self.touch_l_sub = rospy.Subscriber("/finger_sensor_left/touch",
        #                                 Bool,
        #                                 queue_size=1)

    def set_obj_det(self,msg):
        self.obj_det = msg.data

    def set_m_touch(self,msg):
        self.m_touch = msg.data

    def set_r_touch(self,msg):
        self.r_touch = msg.data

    def callback(self,data):
        self.current_joint_angles[0] = data.joint1
        self.current_joint_angles[1] = data.joint2
        self.current_joint_angles[2] = data.joint3
        self.current_joint_angles[3] = data.joint4
        self.current_joint_angles[4] = data.joint5
        self.current_joint_angles[5] = data.joint6
        # print (self.current_joint_angles)


    def move_cartcmmd(self, pose_value, relative):
        pose_action_client.getcurrentCartesianCommand('j2n6a300_')
        pose_mq, pose_mdeg, pose_mrad = pose_action_client.unitParser('mq', pose_value, relative)
        poses = [float(n) for n in pose_mq]
        orientation_XYZ = pose_action_client.Quaternion2EulerXYZ(poses[3:])

        try:
            poses = [float(n) for n in pose_mq]
            result = pose_action_client.cartesian_pose_client(poses[:3], poses[3:])
        except rospy.ROSInterruptException:
            print ("program interrupted before completion")

    def move_fingercmmd(self, finger_value):
        fingers_action_client.getCurrentFingerPosition('j2n6a300_')

        finger_turn, finger_meter, finger_percent = fingers_action_client.unitParser('percent', finger_value, '-r')
        finger_number = 3
        finger_maxDist = 18.9/2/1000  # max distance for one finger in meter
        finger_maxTurn = 6800  # max thread turn for one finger

        try:
            if finger_number == 0:
                print('Finger number is 0, check with "-h" to see how to use this node.')
                positions = []  # Get rid of static analysis warning that doesn't see the exit()
                exit()
            else:
                positions_temp1 = [max(0.0, n) for n in finger_turn]
                positions_temp2 = [min(n, finger_maxTurn) for n in positions_temp1]
                positions = [float(n) for n in positions_temp2]

            print('Sending finger position ...')
            result = fingers_action_client.gripper_client(positions)
            print('Finger position sent!')

        except rospy.ROSInterruptException:
            print('program interrupted before completion')

    def pick_spoon(self):
        if self.listen.frameExists("/root") and self.listen.frameExists("/spoon_position"):
            print ("we have the spoon frame")
            self.listen.waitForTransform('/root','/spoon_position',rospy.Time(),rospy.Duration(100.0))
            t = self.listen.getLatestCommonTime("/root", "/spoon_position")
            translation, quaternion = self.listen.lookupTransform("/root", "/spoon_position", t)

            translation =  list(translation)
            quaternion = list(quaternion)
            pose_value = translation + quaternion
            # print (quaternion)
            orientation_XYZ = pose_action_client.Quaternion2EulerXYZ(quaternion)

            # self.j.gripper.open()
            #second arg=0 (absolute movement), arg = '-r' (relative movement)
            self.move_cartcmmd(pose_value, 0)

            # self.j.gripper.close()

        else:
            print ("we DONT have the frame")

    def goto_bowl(self):
        if self.listen.frameExists("/root") and self.listen.frameExists("/bowl_position"):
            self.listen.waitForTransform('/root','/bowl_position',rospy.Time(),rospy.Duration(100.0))
            # print ("we have the bowl frame")
            # t1 = self.listen.getLatestCommonTime("/root", "bowl_position")
            translation, quaternion = self.listen.lookupTransform("/root", "/bowl_position", rospy.Time(0))

            translation =  list(translation)
            quaternion = list(quaternion)
            pose_value = translation + quaternion
            #second arg=0 (absolute movement), arg = '-r' (relative movement)
            self.move_cartcmmd(pose_value, 0)
        else:
            print ("we DONT have the bowl frame")


    def goto_plate(self):
        if self.listen.frameExists("/root") and self.listen.frameExists("/plate_position"):
            self.listen.waitForTransform('/root','/plate_position',rospy.Time(),rospy.Duration(100.0))
            print ("we have the bowl frame")
            # t1 = self.listen.getLatestCommonTime("/root", "bowl_position")
            translation, quaternion = self.listen.lookupTransform("/root", "/plate_position", rospy.Time(0))

            translation =  list(translation)
            quaternion = [0.8678189045198146, 0.0003956789257977804, -0.4968799802988633, 0.0006910675928639343]
            pose_value = translation + quaternion
            #second arg=0 (absolute movement), arg = '-r' (relative movement)
            self.move_cartcmmd(pose_value, 0)

        else:
            print ("we DONT have the bowl frame")

    def move_joints(self,joints_cmd):
        jointangles = [0]*6
        current_joint_angles = [0]*6
        while current_joint_angles == [0]*6:
            current_joint_angles = self.current_joint_angles
        print(current_joint_angles)
        for i in range(6):
            jointangles[i] = current_joint_angles[i] + joints_cmd[i]

        try:
            self.j.move_joints(jointangles)
        except rospy.ROSInterruptException:
            print('program interrupted before completion')

    def lift_spoon(self):
        # self.move_fingercmmd([0, 0, 0])
        while self.r_touch != True:
            self.cmmd_cart_velo([0.02,0,0,0,0,0,1])
        self.r_touch = False
        while not(self.m_touch and self.r_touch):
            self.cmmd_cart_velo([0.02,0,0,0,0,0,1])
            # self.move_joints([0,0,0,0,0,-5])

        self.move_fingercmmd([100, 100, 100])


    def cmmd_cart_velo(self,cart_velo):
        msg = PoseVelocity(
            twist_linear_x=cart_velo[0],
            twist_linear_y=cart_velo[1],
            twist_linear_z=cart_velo[2],
            twist_angular_x=cart_velo[3],
            twist_angular_y=cart_velo[4],
            twist_angular_z=cart_velo[5])

        self.j.kinematic_control(msg)


    def searchSpoon(self):
        if self.listen.frameExists("/j2n6a300_end_effector") and self.listen.frameExists("/root"):
            # print ("we are in the search spoon fucntion")
            self.listen.waitForTransform('/j2n6a300_end_effector','/root',rospy.Time(),rospy.Duration(100.0))
            t = self.listen.getLatestCommonTime("/j2n6a300_end_effector","/root")
            translation, quaternion = self.listen.lookupTransform("/j2n6a300_end_effector","/root",t)
            matrix1=self.listen.fromTranslationRotation(translation,quaternion)
            counter=0
            rate=rospy.Rate(100)
            while not self.obj_det:
                #   print ("we are in the search spoon fucntion")
                  counter = counter + 1
                  if(counter < 200):
                    print('forward')
                    cart_velocities = np.dot(matrix1[:3,:3],np.array([0.05,0,0])[np.newaxis].T) #change in y->x, z->y, x->z
                    cart_velocities = cart_velocities.T[0].tolist()
                    self.cmmd_cart_velo(cart_velocities + [0,0,0,1])
                  else:
                    print('backwards')
                    cart_velocities = np.dot(matrix1[:3,:3],np.array([-0.05,0,0])[np.newaxis].T)
                    cart_velocities = cart_velocities.T[0].tolist()
                    self.cmmd_cart_velo(cart_velocities + [0,0,0,1])
                  rate.sleep()
                  if(counter >400):
                     counter=0

if __name__ == '__main__':
    rospy.init_node("task_1")
    # n = PickAndPlaceNode(Jaco)
    p = pick_peas_class()
    p.j.gripper.set_position([0,100,100])
    # p.move_fingercmmd((0, 0, 0))
    #
    while not (p.listen.frameExists("/root") and p.listen.frameExists("/spoon_position")): # p.listen.frameExists("bowl_position"):
        pass

    print ("Starting task. . .\n")
    p.pick_spoon()

    print ("Searching spoon. . .\n")
    p.searchSpoon()

    print ("Spoon found yay!!\n")
    print ("Lifitng the spoon. . .\n")
    p.lift_spoon()
    # # self.cmmd_cart_velo([0,0.1,0,0,0,0,1])
    #
    #
    # # p.move_cartcmmd([0,0,0.1,0,0,0,1],'-r')
    #
    # print ("Going to bowl. . .\n")
    # # p.goto_bowl()
    # print ("Bowl reached. . .\n")
    #
    # print ("Scooping the peas. . .")
    #
    # # print(joints)
    # # p.move_joints([0,0,0,0,0,-80])
    # print ("scooping done. . .")
    # # p.goto_plate()
    # rospy.spin()
