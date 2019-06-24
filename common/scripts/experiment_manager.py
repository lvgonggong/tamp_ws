#!/usr/bin/env python

'''
Description: This node
    - Publishes simulation time
    - Subscribes to all topics
    - Performs live visualization
    - Logs all data 
    - Sends shutdown signal? 
'''

import time
import numpy as np
#import matplotlib.patches as patches
import matplotlib.pyplot as plt

import rospy
from rosgraph_msgs.msg import Clock
from common.msg import PathLocal
from common.msg import Obstacles
from common.msg import Trajectory
from common.msg import State
from common.msg import StaticVehicleParams
from common.msg import DynamicVehicleParams

# adjust for high dpi screen
plt.rcParams['figure.dpi'] = 200 # default 100
plt.rcParams['figure.figsize'] = 15, 5

def getCirclePts(x,y,r,n):
    #n = nr of vertices
    t_vertices = np.arange(-np.pi, np.pi, (2*np.pi)/n)
    xpts = r*np.cos(t_vertices) + x;
    ypts = r*np.sin(t_vertices) + y;
    return xpts, ypts

def ptsFrenetToCartesian(Xc,Yc,psic,d): # todo import from somewhere else
    # inputs and outputs are np arrays
    X = Xc - d*np.sin(psic);
    Y = Yc + d*np.cos(psic);
    return X,Y  

class ExperimentManager:
    # constructor
    def __init__(self):
        
        # params
        self.dt = 0.01 # timestep of the simulation
        t_final = rospy.get_param('/t_final')
        do_liveplot = rospy.get_param('/do_liveplot')
        save_logfile = rospy.get_param('/save_logfile')
        
        # init node subs pubs
        rospy.init_node('experiment_manager', anonymous=True)
        #rospy.init_node('experiment_manager', anonymous=True, disable_signals=True)
        self.clockpub = rospy.Publisher('/clock', Clock, queue_size=10)
        
        self.pathlocalsub = rospy.Subscriber("pathlocal", PathLocal, self.pathlocal_callback)
        self.obstaclesub = rospy.Subscriber("obstacles", Obstacles, self.obstacles_callback)
        self.trajhatsub = rospy.Subscriber("trajhat", Trajectory, self.trajhat_callback)
        self.trajstarsub = rospy.Subscriber("trajstar", Trajectory, self.trajstar_callback)
        self.statesub = rospy.Subscriber("state", State, self.state_callback)
        self.staticparamsub = rospy.Subscriber("static_vehicle_params", StaticVehicleParams, self.staticparams_callback)
        self.dynamicparamsub = rospy.Subscriber("dynamic_vehicle_params", DynamicVehicleParams, self.dynamicparams_callback)
        
        # load global path
        self.loadPathGlobalFromFile()
        
        # init internal variables
        self.counter = 0 # use this to reduce plot update rate
        self.pathlocal = PathLocal()
        self.obstacles = Obstacles()
        self.trajhat = Trajectory()
        self.trajstar = Trajectory()
        self.state = State()
        self.sp = StaticVehicleParams()
        self.dp = DynamicVehicleParams()
        
        # init lists for logging
        self.tvec = []
        self.states = []
        
        if(do_liveplot):
            # init plot window
            plt.ion()    
            self.f, (self.a0, self.a1) = plt.subplots(1,2, gridspec_kw = {'width_ratios':[3, 1]})
            self.a0.axis("equal")
            self.a1.axis("equal")
            
        # Main loop
        self.t = 0 
        while (not rospy.is_shutdown()) and self.t<t_final :

            # store data from subscribed topics            
            if(save_logfile):
                self.stack_data()            
            
            # handle simtime
            self.t += self.dt
            msg = Clock()
            t_rostime = rospy.Time(self.t)
            msg.clock = t_rostime
            self.clockpub.publish(msg)
            
            if(do_liveplot):
                self.liveplot()
                slowdown_factor = 1
            else:
                slowdown_factor = 1
                               
      
            print 'simtime t =', t_rostime.to_sec()
            time.sleep(self.dt*slowdown_factor)
    
        
        print 'simulation finished'
        if(save_logfile):
            self.save_log()
    
        # send shutdown signal
        message = 'run finished, shutting down'
        print message
        rospy.signal_shutdown(message)
    
    def stack_data(self):
        
        # time vector
        self.tvec.append(self.t)
        
        # State
        state_dict = {
          "X": self.state.X,
          "Y": self.state.Y,
          "psi": self.state.psi,
          "s": self.state.s,
          "d": self.state.d,
          "deltapsi": self.state.deltapsi,
          "psidot": self.state.psidot,
          "vx": self.state.vx,
          "vy": self.state.vy,
          "ax": self.state.ax,
          "ay": self.state.ay,
          "stop": self.state.stop,
        }
        self.states.append(state_dict)
        
        # trajhat
        
        # trajstar
        
        # path local
        
    def save_log(self):        
        print 'saving logfile'
        
        # init state
        
        # vehicle params
        
        # stacked data

        # write to file
        log_filepath = rospy.get_param('/log_filepath')
        
        
        log = {
          "tvec": self.tvec,
          "pathglobal": self.pathglobal,
          "states": self.states,
        }
        
        np.save(log_filepath, log)

        
    def liveplot(self):
        tm = time.time()
        # clear figure
        self.a0.cla()
        self.a1.cla()
        
        N = len(self.trajstar.s)
        
        # plot lane lines
        nplot = int(1.0*len(self.pathlocal.s))                   
        llX, llY = ptsFrenetToCartesian(np.array(self.pathlocal.X[0:nplot]), \
                                        np.array(self.pathlocal.Y[0:nplot]), \
                                        np.array(self.pathlocal.psi_c[0:nplot]), \
                                        np.array(self.pathlocal.dub[0:nplot]) )
        
        rlX, rlY = ptsFrenetToCartesian(np.array(self.pathlocal.X[0:nplot]), \
                                        np.array(self.pathlocal.Y[0:nplot]), \
                                        np.array(self.pathlocal.psi_c[0:nplot]), \
                                        np.array(self.pathlocal.dlb[0:nplot]) )         
        self.a0.plot(llX,llY,'k') 
        self.a0.plot(rlX,rlY,'k') 
        
        # plot obstacles
        Nobs = len(self.obstacles.s)
        for i in range(Nobs):
            spt = self.obstacles.s[i]
            dpt = self.obstacles.d[i]
            # transform to cartesian
            Xcpt = np.interp(spt,self.pathlocal.s,self.pathlocal.X)
            Ycpt = np.interp(spt,self.pathlocal.s,self.pathlocal.Y)
            psicpt = np.interp(spt,self.pathlocal.s,self.pathlocal.psi_c)                 
            Xobs,Yobs = ptsFrenetToCartesian(Xcpt,Ycpt,psicpt,dpt)
            # define obstacle circle
            Robs = self.obstacles.R[i]
            Rmgnobs = self.obstacles.Rmgn[i]
            Xpts, Ypts = getCirclePts(Xobs,Yobs,Rmgnobs,20)
            self.a0.plot(Xpts, Ypts, 'r')
            Xpts, Ypts = getCirclePts(Xobs,Yobs,Robs,20)
            self.a0.plot(Xpts, Ypts, 'r')
            
        # plot trajhat
        self.a0.plot(self.trajhat.X, self.trajhat.Y, '.b')           
        
        # plot state constraint
        for k in range(N):
            slb = self.trajhat.slb[k]
            sub = self.trajhat.sub[k]
            dlb = self.trajhat.dlb[k]
            dub = self.trajhat.dub[k]
            n_intp = 3
            args = (np.linspace(sub,sub,n_intp), np.linspace(sub,slb,n_intp), np.linspace(slb,slb,n_intp), np.linspace(slb,sub,n_intp))
            spts = np.concatenate(args)
            args = (np.linspace(dub,dlb,n_intp), np.linspace(dlb,dlb,n_intp), np.linspace(dlb,dub,n_intp), np.linspace(dub,dub,n_intp))
            dpts = np.concatenate(args)
            Xcpts = np.interp(spts,self.pathlocal.s,self.pathlocal.X)
            Ycpts = np.interp(spts,self.pathlocal.s,self.pathlocal.Y)
            psicpts = np.interp(spts,self.pathlocal.s,self.pathlocal.psi_c)               
            Xpts, Ypts = ptsFrenetToCartesian(Xcpts, Ycpts, psicpts,dpts)
            self.a0.plot(Xpts,Ypts,'m')
            
        # plot trajstar
        self.a0.plot(self.trajstar.X, self.trajstar.Y, '*m')       
        
        # plot ego vehicle pose
        length_front = self.sp.lf+0.75;
        length_rear = self.sp.lr+0.75;
        width = self.sp.w;
        R = np.matrix([[np.cos(self.state.psi),   np.sin(self.state.psi)], \
                       [-np.sin(self.state.psi),  np.cos(self.state.psi)]])

        corners = np.matrix([[length_front,  width/2], \
                             [-length_rear,  width/2], \
                             [-length_rear, -width/2], \
                             [length_front, -width/2], \
                             [length_front,  width/2]])
        corners = corners*R;
        corners[:,0] = corners[:,0] + self.state.X;
        corners[:,1] = corners[:,1] + self.state.Y;
        
        self.a0.plot(corners[:,0],corners[:,1], 'k')           
        
        # plot real friction circle
        
        # plot algo friction circle
        Fxfpts, Fyfpts = getCirclePts(0,0,self.dp.mu_alg*self.dp.Fzf,100)
        self.a1.plot(Fxfpts,Fyfpts,'k')
        
        # plot trajhat forces
        self.a1.plot(self.trajhat.Fxf, self.trajstar.Fyf, 'xr')

        # plot trajstar forces
        self.a1.plot(self.trajstar.Fxf, self.trajstar.Fyf, 'xb')

        self.a1.set_xlabel('Fxf')
        self.a1.set_ylabel('Fyf')
                  
        # redraw plot
        plt.draw() 
        plt.pause(0.001)
        
        # print plot time 
        elapsed = time.time() - tm
        #print("dt = " + str(self.dt) + ", plot time = " + str(elapsed))
        #if(self.dt < elapsed):
        #    print("WARNING: plot time is larger than dt")    

    def loadPathGlobalFromFile(self):
        pathglobal_filepath = rospy.get_param('/pathglobal_filepath')
        pathglobal_npy = np.load(pathglobal_filepath)
        self.pathglobal = pathglobal_npy.item()
            
    def pathlocal_callback(self, msg):
        #print("in pathlocal callback")
        self.pathlocal = msg
    
    def obstacles_callback(self, msg):
        #print("in obstacles callback")
        self.obstacles = msg
        
    def trajhat_callback(self, msg):
        #print("in trajhat callback")
        self.trajhat = msg
        
    def trajstar_callback(self, msg):
        #print("in trajstar callback")
        self.trajstar = msg
    
    def state_callback(self, msg):
        #print("in state callback")
        self.state = msg
        
    def staticparams_callback(self, msg):
        #print("in static params callback")
        self.sp = msg
        
    def dynamicparams_callback(self, msg):
        #print("in static params callback")
        self.dp = msg
    


    
if __name__ == '__main__':
    em = ExperimentManager()
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("Shutting down")   
    
    
    
    



    
    