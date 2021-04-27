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

    ##############################################################################################################################
    # Function will configure the MAX77958 to setup and initialize the PPS mode to pass a voltage to a MAX17330 for charging
    # @param self is the I2C address of the MAX77958 device 
    # @param ENABLE is a byte that is either value 1 to enable PPS or value 0 to disable it
    # @param DEFAULT_OUTPUT_VOLTAGE_LOW is the lower byte of data for the voltage
    # @param DEFAULT_OUTPUT_VOLTAGE_HIGH is the higher byte of data for the voltage
    # @param DEFAULT_OPERATING_CURRENT is the byte of information to describe current 
    # @return 0 = PPS Off
    # @return 1 = PPS On
    # @return 6 = DP Configured State
    # @return -1 = invalid enable byte sent
    # @return -2 = wrong range is selected for programmed voltage 
    # @return -3 = wrong range is selected for programmed current
    ##############################################################################################################################
    def set_pps(self, ENABLE, DEFAULT_OUTPUT_VOLTAGE_LOW, DEFAULT_OUTPUT_VOLTAGE_HIGH, DEFAULT_OPERATING_CURRENT):
        pps_opcode = 0x3c

        # check and see if the enable value is a 1 or a 0 and return error if not
        if ENABLE > 0x01:
            return -1
        
        # check and see if the voltage function input is in an invalid range of 0-20V
        if DEFAULT_OUTPUT_VOLTAGE_HIGH > 0x03:
            return -2
        elif DEFAULT_OUTPUT_VOLTAGE_HIGH == 0x03 and DEFAULT_OUTPUT_VOLTAGE_LOW > 0xE8:
            return -2

        # check and see if the current function input is not at either max operating current or in range of 50-6200mA
        if DEFAULT_OPERATING_CURRENT >= 0x7D:
            return -3
        
        dout=[]
        dout.append(ENABLE)
        dout.append(DEFAULT_OUTPUT_VOLTAGE_LOW)
        dout.append(DEFAULT_OUTPUT_VOLTAGE_HIGH)
        dout.append(DEFAULT_OPERATING_CURRENT)

        # write the data to the set_pps opcode at 
        self.write_opcode(pps_opcode, dout)

        din=[]
        # get a response 
        din = self.read_opcode(pps_opcode)
        return din[1] #return the status of the PPS from the second byte of returned data

'''
u=MAX77958(SID=0x27)
while(1):
    time.sleep(1)
    u.set_qc5v()
    time.sleep(1)
    u.set_qc9v()'''