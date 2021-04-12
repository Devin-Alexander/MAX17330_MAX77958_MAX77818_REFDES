#Basic operations for MAX77958
import time
from smbus import SMBus
bus = SMBus(1)

class MAX77958:
    def __init__(self,SID=0x27):
        try:
            bus.write_byte(0x25,0x0)
            self.connected = True
        except:
            self.connected = False
        self.SID=SID

    def r(self,reg_addr,l=1,SID=0):
        if SID==0:
            SID=self.SID
        if l == 1:
            return bus.read_byte_data(SID,reg_addr)
        else:
            return bus.read_i2c_block_data(SID,reg_addr,l)
    def w(self,addr,data,l=1,SID=0):
        if SID==0:
            SID=self.SID
        if (l==1) or (type(data) is not list):
            bus.write_byte_data(SID,addr,data)
        else:
            bus.write_i2c_block_data(SID,addr,data)
    def write_opcode(self,code,data):
        dout = []
        if not type(data) is list:
            dout.append(data)
        else:
            dout = data
        if len(dout)< 32:                
            dout += (32- len(dout))*[0]
        self.w(0x21,code)
        for x in range(len(dout)):
            self.w(0x22+x,dout[x])
    def read_opcode(self,code):
        self.w(0x21,code)
        data=[]
        for x in range(0x51,0x72):
            data.append(self.r(x))
        return data
    def set_qc9v(self):
        self.write_opcode(0x4,0x35)
    def set_qc5v(self):
        self.write_opcode(0x4,0x0f)
'''
u=MAX77958(SID=0x27)
while(1):
    time.sleep(1)
    u.set_qc5v()
    time.sleep(1)
    u.set_qc9v()'''