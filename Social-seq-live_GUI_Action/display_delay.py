import time
import numpy as np
import picklerpc
import pandas as pd
import threading
import socket

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QLabel, QLineEdit
from labels_profile import df_bhv_labels

from serialproxy import SerialCommunicator
from check_devices import remove_rpc_ip_port

class PyThreadDelay(threading.Thread):
    def __init__(self, qwidget:QLineEdit=None, ip:str=None):
        super().__init__()
        self.qwidget = qwidget
        self.ip = ip
        self.to_continue = True

    def run(self):
        # rpcclient = picklerpc.PickleRPCClient((self.ip, 8092))
        rpcclient = picklerpc.PickleRPCClient(remove_rpc_ip_port)
        while self.to_continue:
            try:
                delay:float = rpcclient.bhv_queue_get()
            except:
                rpcclient = picklerpc.PickleRPCClient(remove_rpc_ip_port)
                delay:float = rpcclient.bhv_queue_get()
            # delay_mm = ((delay+1) * 33.34)  #the stream back latency is average 1 frame
            delay_mm = ((delay) * 33.34) 
            text = 'nan' if np.isnan(delay_mm) else '{:>4} ms'.format(int(delay_mm))
            self.qwidget.setText(text)
            time.sleep(0.1)
        rpcclient.disconnect()


class PyThreadBhvLabel(threading.Thread):
    def __init__(self, qwidget:QLabel=None, ip:str=None):
        super().__init__()
        self.qwidget = qwidget
        self.ip = ip
        self.to_continue = True
        df_bhv_labels2:pd.DataFrame = df_bhv_labels.sort_values(by=['cls_id'])
        self.bhv_cluster_names = df_bhv_labels2['bhv_name'].to_list()

    def run(self):
        rpcclient = picklerpc.PickleRPCClient(remove_rpc_ip_port)

        while self.to_continue:
            try:
                bhv_int:int = rpcclient.label_int()
            except:
                rpcclient = picklerpc.PickleRPCClient(remove_rpc_ip_port)
                bhv_int:int = rpcclient.label_int()
            if bhv_int>=0:
                self.bhv_cluster_names[bhv_int]
                text = f'[{bhv_int+1}] ' + self.bhv_cluster_names[bhv_int][:30]
                self.qwidget.setText(text)

        rpcclient.disconnect()


class PyThreadStimulate(threading.Thread, QObject):
    trigger:Signal = Signal(bool)

    def __init__(self, bhv_inds:list=None, obj_serial:SerialCommunicator=None):
        threading.Thread.__init__(self)
        QObject.__init__(self)
        self.to_continue = True
        self.obj_serial = obj_serial
        self.bhv_inds = bhv_inds
        self.downcounter = 20
        
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.connect(('localhost', 20173))

    def run(self):
        # rpcclient = picklerpc.PickleRPCClient((self.ip, 8092))
        rpcclient = picklerpc.PickleRPCClient(remove_rpc_ip_port)
        print("======begin stimuli condition")
        # set the 'qwidgetstimu' font color to red

        # while self.to_continue and self.obj_serial.isValid:
        while self.to_continue:
            try:
                bhv_int:int = rpcclient.label_int()
            except:
                rpcclient = picklerpc.PickleRPCClient(remove_rpc_ip_port)
                bhv_int:int = rpcclient.label_int()
            if bhv_int in self.bhv_inds:
                self.downcounter = 20
                self.trigger.emit(True)
                self.tcp_socket.send(b'start_record')
                self.tcp_socket.recv(1024)
                if self.obj_serial is not None and self.obj_serial.isValid:
                    self.obj_serial.send_message('b')
            else:
                self.downcounter -= 1
                if self.downcounter == 0:
                    self.trigger.emit(False)
            time.sleep(0.05)
        
        print("======end stimuli")
        self.trigger.emit(False)
        rpcclient.disconnect()
