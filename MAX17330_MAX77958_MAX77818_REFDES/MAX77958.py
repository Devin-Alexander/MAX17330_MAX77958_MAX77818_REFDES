#Basic operations for MAX77958
import time
from smbus import SMBus
bus = SMBus(1)


# List of Opcodes
BC_CTRL1_Config_Read_Opcode              = 0x01
BC_CTRL1_Config_Write_Opcode             = 0x02
Control1_Read_Opcode                     = 0x05
Control1_Write_Opcode                    = 0x06
CC_Control1_Read_Opcode                  = 0x0B
CC_Control1_Write_Opcode                 = 0x0C
CC_Control4_Read_Opcode                  = 0x11
CC_Control4_Write_Opcode                 = 0x12
GPIO_Control_Read_Opcode                 = 0x23
GPIO_Control_Write_Opcode                = 0x24
GPIO0_GPIO1_ADC_Read_Opcode              = 0x27
Get_Sink_Cap_Opcode                      = 0x2F
Current_Src_Cap_Opcode                   = 0x30
Get_Source_Cap_Opcode                    = 0x31
Src_Cap_Request_Opcode                   = 0x32
Set_Src_Cap_Opcode                       = 0x33
Read_the_Response_for_Get_Request_Opcode = 0x35
Send_Get_Response_Opcode                 = 0x36
Send_Swap_Request_Opcode                 = 0x37
Send_Swap_Response_Opcode                = 0x38
APDO_SrcCap_Request_Opcode               = 0x3A
Set_PPS_Opcode                           = 0x3C
SNK_PDO_Request_Opcode                   = 0x3E
SNK_PDO_Set_Opcode                       = 0x3F
Get_PD_Message_Opcode                    = 0x4A
Customer_Configuration_Read_Opcode       = 0x55
Customer_Configuration_Write_Opcode      = 0x56
Master_I2C_Control_Read_Opcode           = 0x85
Master_I2C_Control_Write_Opcode          = 0x86



class MAX77958:
    pps_voltage = 0x00 # used to keep track of the current pps voltage
    pps_voltage_min = 0x00 # TODO remove before final release. used as a starting point for the pps value when pps mode is enabled
    pps_voltage_max = 0x00 # TODO remove before final release. used as an ending point to make sure there isn't excessive heating on MAX17330 while debugging 
    pps_operating_current = 0x00 # denotes that there is no current limit and that it defaults to max current

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
    # @function set_pps() will configure the MAX77958 to setup and initialize the PPS mode to pass a voltage to a MAX17330 for charging
    # @param ENABLE is a byte that is either value 1 to enable PPS or value 0 to disable it
    # @param DEFAULT_OUTPUT_VOLTAGE_LOW is the lower byte of data for the voltage
    # @param DEFAULT_OUTPUT_VOLTAGE_HIGH is the higher byte of data for the voltage
    # @param DEFAULT_OPERATING_CURRENT is the byte of information to describe current 
    # @return 0 = PPS Off
    # @return 1 = PPS On
    # @return 6 = DP Configured State
    # @return -1 = invalid ENABLE byte sent
    # @return -2 = wrong range is selected for programmed voltage 
    # @return -3 = wrong range is selected for programmed current
    ##############################################################################################################################
    def set_pps(self, ENABLE, DEFAULT_OUTPUT_VOLTAGE_LOW, DEFAULT_OUTPUT_VOLTAGE_HIGH, DEFAULT_OPERATING_CURRENT):
        # check and see if the enable value is a 1 or a 0 and return error if not
        if ENABLE > 0x01:
            return -1
        elif ENABLE = 0:
            self.pps_voltage = 0x00  # reset this value to zero upon turning off PPS functionality
        else: 
            self.pps_voltage = (DEFAULT_OUTPUT_VOLTAGE_LOW & 0xFF) | ((DEFAULT_OUTPUT_VOLTAGE_HIGH & 0xFF) << 8)
        
        
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
        self.write_opcode(Set_PPS_Opcode, dout)

        din=[]
        # get a response 
        din = self.read_opcode(Set_PPS_Opcode)
        return din[1] #return the status of the PPS from the second byte of returned data

    ##############################################################################################################################
    # @function change_pps_voltage() helper function called by the decrement/increment pps voltage function
    # @return 0 = PPS Off
    # @return 1 = PPS On
    # @return 6 = DP Configured State
    ##############################################################################################################################
    def change_pps_voltage(self):
        ENABLE = 0x01

        dout=[]
        dout.append(ENABLE)
        dout.append(self.pps_voltage & 0x00FF)
        dout.append((self.pps_voltage & 0xFF00) >> 8)
        dout.append(self.pps_operating_current)

        # write the data to the set_pps opcode at 
        self.write_opcode(Set_PPS_Opcode, dout)

        din=[]
        # get a response 
        din = self.read_opcode(Set_PPS_Opcode)
        return din[1] #return the status of the PPS from the second byte of returned data


    ##############################################################################################################################
    # @function increment_pps_voltage() will increment the pps voltage setting by one hex valur = 10mV higher than before
    ##############################################################################################################################
    def increment_pps_voltage(self):
        if self.pps_voltage == self.p
        self.pps_voltage += 0x01


    ##############################################################################################################################
    # @function manual_charger_detect() will configure the MAX77958 to run manual charger detection iteration
    ##############################################################################################################################
    def manual_charger_detect(self):
        # Perform BC_CTRL1_Config_Read_Opcode 
        din=[]
        din = self.read_opcode(BC_CTRL1_Config_Read_Opcode)
        # Bitwise OR the register data with CHGDetMan bit to configure manual charger detect
        CHGDetMan = 0x02
        dout=din[1] | CHGDetMan
        # Perform BC_CTRL1_Config_Write_Opcode 
        self.write_opcode(BC_CTRL1_Config_Write_Opcode, dout)

    ##############################################################################################################################
    # @function auto_charger_detect() will configure the MAX77958 to run manual charger detection iteration
    # @param ENABLE is a byte that is either value 1 to enable auto charger detect or value 0 to disable it
    # @return -1 = invalid ENABLE byte sent
    # @return 0  = auto_charger_detect successfully configured
    ##############################################################################################################################
    def auto_charger_detect(self, ENABLE):
    # check and see if the enable value is a 1 or a 0 and return error if not
        if ENABLE > 0x01:
            return -1
        # Perform BC_CTRL1_Config_Read_Opcode 
        din=[]
        din = self.read_opcode(BC_CTRL1_Config_Read_Opcode)
        # Clear CHGDetEn bit and then Bitwise OR the register data with ENABLE to configure auto charger detect
        CHGDetManClear = 0xFE
        CHGDetManBit = ENABLE
        dout = din[1] & CHGDetManClear
        dout |= CHGDetManBit 
        # Perform BC_CTRL1_Config_Write_Opcode 
        self.write_opcode(BC_CTRL1_Config_Write_Opcode, dout)
        return 0

    

#######################################################################################################################################################################
#######################################################################################################################################################################
#######################################################################################################################################################################
#######################################################################################################################################################################
#######################################################################################################################################################################
#######################################################################################################################################################################
#######################################################################################################################################################################
#######################################################################################################################################################################

u=MAX77958(SID=0x27)
while(1):
    time.sleep(1)
    u.set_qc5v()
    time.sleep(1)
    u.set_qc9v()'''