#Basic operations for MAX77958
import time
from smbus import SMBus
import math 
bus = SMBus(1)


###############################################
############## List of Registers###############
###############################################
DEVICE_ID    = 0x0
DEVICE_REV   = 0x1 
FW_REV       = 0x2
FW_SUB_VER   = 0x3
UIC_INT      = 0x4
CC_INT       = 0x5
PD_INT       = 0x6
ACTION_INT   = 0x7
USBC_STATUS1 = 0x8
USBC_STATUS2 = 0x9
BC_STATUS    = 0xA
DP_STATUS    = 0xB
CC_STATUS0   = 0xC
CC_STATUS1   = 0xD
PD_STATUS0   = 0xE
PD_STATUS1   = 0xF
UIC_INT_M    = 0x10
CC_INT_M     = 0x11
PD_INT_M     = 0x12
ACTION_INT_M = 0x13
#Registers 0x21-0x71 are used for opcode programming and data reading
SW_RESET     = 0x80
I2C_CNFG     = 0xE0


###############################################
############### List of Opcodes ###############
###############################################
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
    # PPS variables
    pps_voltage = 0x0000 # used to keep track of the current pps voltage
    pps_voltage_min = 0x0000 # TODO remove before final release. used as a starting point for the pps value when pps mode is enabled
    pps_voltage_max = 0X0000 # TODO remove before final release. used as an ending point to make sure there isn't excessive heating on MAX17330 while debugging 
    pps_operating_current = 0x00 # init value denotes that there is no current limit and that it defaults to max current

    # PDO Source variables (Power Delivery Objects) up to 7 can be present on a PD Source device
    curr_pdo_src_selected = 0 # this needs to be set to the correct PDO src for the type of charging desired
    pdo_src_num = 0 # keeps track of up to 8 Power Delivery Source Objects. This is charger specific and will vary depending on the selected charger
    pdo_src_full_details = [0,0,0,0,0,0,0,0] # holds full PDO decriptors for each PDO broadcast from compatible USB PD Charger 
    pdo_src_type         = [0,0,0,0,0,0,0,0] # From Bits 31-30 from PDO: 00b Fixed Supply, 01b Battery, 10b Variable supply, 11b ??????????Reserved
    pdo_src_max_voltage = [0,0,0,0,0,0,0,0] # From Bits 29-20 in PDO: Note: This will be different for a fixed supply PDO compared to APDO src
    pdo_src_min_voltage = [0,0,0,0,0,0,0,0] # From Bits 19-10 in PDO: This is always the min voltage for APDO or set voltage for fixed PDO src
    pdo_src_max_current = [0,0,0,0,0,0,0,0] # From Bits  9-0  in PDO: This is sifferent for Battery supply PDO
    
    apdo_pps_src_max_voltage = [0,0,0,0,0,0,0,0] # From Bits 24-17 in APDO: Note: This will be different for a fixed supply PDO compared to APDO src
    apdo_pps_src_min_voltage = [0,0,0,0,0,0,0,0] # From Bits 15-8  in APDO: This is always the min voltage for APDO or set voltage for fixed PDO src
    apdo_pps_src_max_current = [0,0,0,0,0,0,0,0] # From Bits  6-0  in APDO: This is sifferent for Battery supply PDO

    # converted variables for use with program
    conv_pdo_src_max_voltage = [0x000,0x0,0x0,0x0,0x0,0x0,0x0,0x0]# Converted from 50mV units into the respective 20mV increments supported by PD 3.0/MAX77958 for this program
    conv_pdo_src_min_voltage = [0x000,0x0,0x0,0x0,0x0,0x0,0x0,0x0]# Converted from 50mV units into the respective 20mV increments supported by PD 3.0/MAX77958 for this program
    conv_pdo_src_max_current = [0x000,0x0,0x0,0x0,0x0,0x0,0x0,0x0]# Converted from 10mA units into the respective 50mA increments supported by PD 3.0/MAX77958 for this program
    # conv_apdo_pps_src_max_voltage = [0x000,0x0,0x0,0x0,0x0,0x0,0x0,0x0]# Converted from 50mV units into the respective 20mV increments supported by PD 3.0/MAX77958 for this program
    # conv_apdo_pps_src_min_voltage = [0x000,0x0,0x0,0x0,0x0,0x0,0x0,0x0]# Converted from 50mV units into the respective 20mV increments supported by PD 3.0/MAX77958 for this program
    # conv_apdo_pps_src_max_current = [0x000,0x0,0x0,0x0,0x0,0x0,0x0,0x0]# Converted from 10mA units into the respective 50mA increments supported by PD 3.0/MAX77958 for this program

    #def __init__(self,SID=0x27):
    def __init__(self,SID=0x25):
        try:
            bus.write_byte(0x25,0x0)
            self.connected = True
        except:
            self.connected = False
        self.SID=SID
        print("SID = {}".format(hex(self.SID)))

    def r(self,reg_addr,length=1,SID=0):
        if SID==0:
            SID=self.SID
        if length == 1:
            return bus.read_byte_data(SID,reg_addr)
        else:
            return bus.read_i2c_block_data(SID,reg_addr,length)

    def w(self,reg_addr,data,length=1,SID=0):
        if SID==0:
            SID=self.SID
        if (length==1) or (type(data) is not list):
            bus.write_byte_data(SID,reg_addr,data)
            # print("SINGLE")
        else:
            bus.write_i2c_block_data(SID,reg_addr,data)
            # print("BLOCK")
    
    # def write_opcode(self,code,data):
    #     dout = []
    #     if not type(data) is list:
    #         dout.append(data)
    #     else:
    #         dout = data
    #     if len(dout)< 32:                
    #         dout += (32- len(dout))*[0]
    #     self.w(0x21,code)
    #     for x in range(len(dout)):
    #         self.w(0x22+x,dout[x])
    
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
        # self.w(0x41,0x00)
     
    
    def read_opcode(self,code,length=32):
        # data=[]
        data = self.r(0x51, length)
        rx_code = data[0]
        
        if code != rx_code:
            print("Expected {} : Received {}".format(hex(code), hex(rx_code)))
            return data
        
        # for x in range(0x52,0x72):
        #     data.append(self.r(x))
        return data
    
    ''' 
    def read_opcode(self,code):
        #self.w(0x51,code)
        data=[]
        for x in range(0x51,0x72):
            data.append(self.r(x))
        return data
    '''
    '''
    def read_opcode(self,code):
        self.r(0x51) #,code)

        time.sleep(0.25)
        data=[]
        for x in range(0x52,0x72):
            data.append(self.r(x))
        return data
    '''
    def reset_MAX77958(self):
        self.write_reg(SW_RESET,0x0F) # When AP writes 0x0F registers are reset

    def set_qc9v(self):
        self.write_opcode(0x4,0x35)
        print("QC9V")

    def set_qc5v(self):
        self.write_opcode(0x4,0x0f)
        print("QC5V")

    def read_reg(self,reg_addr,length=1):
        data=[]
        data=self.r(reg_addr,length)
        return data

    def read_all_int_regs(self):
        data=[]
        data=self.read_reg(UIC_INT,4) # read all 4 interrupt registers
        return data
    
    def write_reg(self,reg_addr,data,length=1):
        self.w(reg_addr,data,length)
    
    '''
    NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW
    '''
    def get_current_src_cap(self):
        # write the opcode to begin receiving data
        self.write_opcode(Current_Src_Cap_Opcode,0x00)

        time.sleep(0.01)
        # get a response 
        dout=[]
        dout = self.read_opcode(Current_Src_Cap_Opcode)
        # print("Returned DATA from reading OPCODE 0x30")
        # for x in range(len(dout)):
        #     print(format(hex(dout[x])))
        time.sleep(0.01)

        return dout

    def erase_pdo_src_variables(self): 
        # Clear prev stored values for all PDO src variables
        self.pdo_src_num = 0
        self.pdo_src_full_details = [0,0,0,0,0,0,0,0]
        self.pdo_src_type         = [0,0,0,0,0,0,0,0] 
        self.pdo_src_max_voltage  = [0,0,0,0,0,0,0,0]
        self.pdo_src_min_voltage  = [0,0,0,0,0,0,0,0]
        self.pdo_src_max_current  = [0,0,0,0,0,0,0,0]
        self.conv_pdo_src_max_voltage = [0,0,0,0,0,0,0,0]
        self.conv_pdo_src_min_voltage = [0,0,0,0,0,0,0,0]
        self.conv_pdo_src_max_current = [0,0,0,0,0,0,0,0]

        self.apdo_pps_src_max_voltage = [0,0,0,0,0,0,0,0]
        self.apdo_pps_src_min_voltage = [0,0,0,0,0,0,0,0] 
        self.apdo_pps_src_max_current = [0,0,0,0,0,0,0,0]

    
    def configure_pdo_src_variables(self):
        # Clear prev stored values for all PDO src variables
        self.erase_pdo_src_variables()
        # Get new pdo information to store
        din = []
        print(format(bin(len(din))))
        din = self.get_current_src_cap()


        
        time.sleep(0.1)

        # Store information in the variables
        self.pdo_src_num = din[1] & 0x07                # Bitwise AND ret data from addr 0x52 with to get bits [2:0] to set total PDOs available from source
        self.curr_pdo_src_selected = (din[1] & 0x38)>>3 # Bitwise AND ret data from addr 0x52 with 0x38 and shift to get bits [5:3] which denote currently selected PDO from source
        print("current pdo selected",self.curr_pdo_src_selected)
        # TODO remove after done debugging Load details in for each available src PDO
        print("Loading PDO info into variables")
        for n in range(self.pdo_src_num):
            self.pdo_src_full_details[n] = din[n*4 + 2] | (din[n*4 + 3] << 8) | (din[n*4 + 4] << 16) | (din[n*4 + 5] << 24) # load contents of PDO into full detail                        print("Max Voltage")
            print("Full PDO deets")
            print("PDO INDEX = ",n)
            print(format(hex(self.pdo_src_full_details[n])))
            self.pdo_src_type[n]         = (self.pdo_src_full_details[n] & 0xC0000000) >> 30 # take bits [31:30] and isolate them 
            self.pdo_src_max_voltage[n]  = ((self.pdo_src_full_details[n] & 0x3FF00000) >> 20) # take bits [29:20] and isolate them 
            self.pdo_src_min_voltage[n]  = ((self.pdo_src_full_details[n] & 0x000FFC00) >> 10) # take bits [19:10] and isolate them 
            self.pdo_src_max_current[n]  = ((self.pdo_src_full_details[n] & 0x000003FF)) # take bits [9:0] and isolate them 
            # convert them for easier use with this program
            self.conv_pdo_src_max_voltage[n] = math.floor(self.pdo_src_max_voltage[n] * 5.0 / 2.0) # 50mV to 20mV increments
            self.conv_pdo_src_min_voltage[n] = math.floor(self.pdo_src_min_voltage[n] * 5.0 / 2.0) # 50mV to 20mV increments
            self.conv_pdo_src_max_current[n] = math.floor(self.pdo_src_max_current[n] / 5.0) # 10mA to 50mA increments

            self.apdo_pps_src_max_voltage[n] = ((self.pdo_src_full_details[n] & 0x01FE0000) >> 17) # take bits [24:17] and isolate them 
            self.apdo_pps_src_min_voltage[n] = ((self.pdo_src_full_details[n] & 0x0000FF00) >> 8)  # take bits [15:8] and isolate them 
            self.apdo_pps_src_max_current[n] = ((self.pdo_src_full_details[n] & 0x0000007F)) # take bits [6:0] and isolate them 

            # print("Max Voltage")
            # print(format(hex(self.pdo_src_max_voltage[n])))
            # print(format(hex(self.conv_pdo_src_max_voltage[n])))
            # print("Min Voltage")
            # print(format(hex(self.pdo_src_min_voltage[n])))
            # print(format(hex(self.conv_pdo_src_min_voltage[n])))
            # print("Current")
            # print(format(hex(self.pdo_src_max_current[n])))
            # print(format(hex(self.conv_pdo_src_max_current[n])))

            print("Max Voltage PPS")
            print(self.apdo_pps_src_max_voltage[n]," = {}mV",self.apdo_pps_src_max_voltage[n]*100)
            print("Min Voltage PPS")
            print(self.apdo_pps_src_min_voltage[n]," = {}mV",self.apdo_pps_src_min_voltage[n]*100)
            print("Current PPS")
            print(self.apdo_pps_src_max_current[n]," = {}mA",self.apdo_pps_src_max_current[n]*50)

            # print("Max Voltage")
            # print(self.pdo_src_max_voltage[n]," = {}mV",self.pdo_src_max_voltage[n]*50)
            # print(self.conv_pdo_src_max_voltage[n]," = {}mV",self.conv_pdo_src_max_voltage[n]*20)
            # print("Min Voltage")
            # print(self.pdo_src_min_voltage[n]," = {}mV",self.pdo_src_min_voltage[n]*50)
            # print(self.conv_pdo_src_min_voltage[n]," = {}mV",self.conv_pdo_src_min_voltage[n]*20)
            # print("Current")
            # print(self.pdo_src_max_current[n]," = {}mA",self.pdo_src_max_current[n]*10)
            # print(self.conv_pdo_src_max_current[n]," = {}mA",self.conv_pdo_src_max_current[n]*50)

            time.sleep(0.1)


        # Load in the currently selected APDO details into the PPS variables

        return

    # TODO def select_pdo_src(self, pdo_idx):    # should be a very high level helper function 

    # find indices where there is a pps capable device
    # return -1 if there is no capanble APDO src for PPS mode
    def find_pps_capable_pdo(self):
        dout = []
        for n in range(self.pdo_src_num):
            if self.pdo_src_type[n] == 0x03:  # PPS devices always have the ID of 0x3 for the bits [31-30] of APDO
                dout.append(n) #PDO objects are indexed at 0x01 not 0x00
                print("APDO found ",n)
        if len(dout) == 0:
            return -1
        else:
            return dout

    # TODO def get_current_src_cap(self):
        
    ##############################################################################################################################
    # TODO fix the return value structure
    # @function set_pps() will configure the MAX77958 to setup and initialize the PPS mode to pass a voltage to a MAX17330 for charging
    # @return -3 = wrong range is selected for programmed current
    ##############################################################################################################################
    def set_APDO_SrcCap_Request(self, REQ_APDO_POS, OUTPUT_VOLTAGE_LOW, OUTPUT_VOLTAGE_HIGH, OPERATING_CURRENT=0x00):
        '''
        desired_pps_voltage = (OUTPUT_VOLTAGE_LOW & 0xFF) | ((OUTPUT_VOLTAGE_HIGH & 0xFF) << 8)

        print("HEEEERRRREEE")
        print("desired_pps_voltage value = {}".format(hex(desired_pps_voltage)))
        print("conv_pdo_src_max_voltage value = {}".format(hex(self.conv_pdo_src_max_voltage[REQ_APDO_POS])))
        print("conv_pdo_src_min_voltage value = {}".format(hex(self.conv_pdo_src_min_voltage[REQ_APDO_POS])))

        # check and see if the requested APDO postion value is valid
        if self.pdo_src_type[REQ_APDO_POS] < 0x01:
            return -1 #selected PDO is not capable of APDO

        # check and see if the voltage function input is in an invalid range of 0-20V
        if OUTPUT_VOLTAGE_HIGH > 0x03:
            return -2
        elif OUTPUT_VOLTAGE_HIGH == 0x03 and OUTPUT_VOLTAGE_LOW > 0xE8:
            return -2

        # verify that the desired voltage is within APDO selected 
        desired_pps_voltage = (OUTPUT_VOLTAGE_LOW & 0xFF) | ((OUTPUT_VOLTAGE_HIGH & 0xFF) << 8)

        if desired_pps_voltage > self.conv_pdo_src_max_voltage[REQ_APDO_POS]:
            return -3 # Voltage MSB & LSB need to be changed to reflect the min supported PDO min voltage
        elif desired_pps_voltage < self.conv_pdo_src_min_voltage[REQ_APDO_POS]:
            return -4 # Voltage MSB & LSB need to be changed to reflect the max supported PDO max voltage
            
        # check and see if the current function input is not at either max operating current or in range of 50-6200mA
        if OPERATING_CURRENT >= 0x7D:
            return -5
        '''

        # If it makes it here, then it means everything is valid
        self.pps_voltage_min = self.apdo_pps_src_min_voltage[REQ_APDO_POS] * 5 # multiply by 5 because this is stored in multiples of 20mV instead of 100mV like pps APDO stores it
        self.pps_voltage_max = self.apdo_pps_src_max_voltage[REQ_APDO_POS] * 5 # multiply by 5 because this is stored in multiples of 20mV instead of 100mV like pps APDO stores it
        self.pps_operating_current = OPERATING_CURRENT
        self.pps_voltage = (OUTPUT_VOLTAGE_LOW & 0xFF) | ((OUTPUT_VOLTAGE_HIGH & 0xFF) << 8)
        self.curr_pdo_src_selected = REQ_APDO_POS
        
        dout=[]
        dout.append(REQ_APDO_POS + 1)  #PDO objects are indexed at 0x01 instead of 0x00
        dout.append(OUTPUT_VOLTAGE_LOW)
        dout.append(OUTPUT_VOLTAGE_HIGH)
        dout.append(OPERATING_CURRENT)

        # write the data to the set_pps opcode 
        self.write_opcode(APDO_SrcCap_Request_Opcode, dout)
                
        time.sleep(0.01)

        din=[]
        # get a response 
        din = self.read_opcode(APDO_SrcCap_Request_Opcode)
        return din[1] #return the status of the PPS from the second byte of returned data
    '''
    NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW NEW
    '''
    ##############################################################################################################################
    # @function update_pps_voltage() helper function called by the decrement/increment pps voltage function
    # @return 0 = PPS Off
    # @return 1 = PPS On
    # @return 6 = DP Configured State
    ##############################################################################################################################
    def update_pps_voltage(self):
        dout = self.set_APDO_SrcCap_Request(self.curr_pdo_src_selected, self.pps_voltage & 0x00FF, ((self.pps_voltage & 0xFF00) >> 8), self.pps_operating_current)
        return dout
        '''
        ENABLE = 0x01
        dout=[]
        dout.append(self.c)
        dout.append(self.pps_voltage & 0x00FF)
        dout.append((self.pps_voltage & 0xFF00) >> 8)
        dout.append(self.pps_operating_current)

        # write the data to the set_pps opcode at 
        self.write_opcode(Set_PPS_Opcode, dout)

        din=[]
        # get a response 
        din = self.read_opcode(Set_PPS_Opcode)
        return din[1] #return the status of the PPS from the second byte of returned data
        '''

    ##############################################################################################################################
    # @function set_pps() will configure the MAX77958 to setup and initialize the PPS mode to pass a voltage to a MAX17330 for charging
    # @param ENABLE is a byte that is either value 1 to enable PPS or value 0 to disable it
    # @param DEFAULT_OUTPUT_VOLTAGE_LOW is the lower byte of data for the voltage from 0x00 to 0xFF
    # @param DEFAULT_OUTPUT_VOLTAGE_HIGH is the higher byte of data for the voltage from 0x00 to 0xFF
    # @param DEFAULT_OPERATING_CURRENT is the byte of information to describe current from 0x00 to 0x7D
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
        elif ENABLE == 0:
            self.pps_voltage = 0x00  # reset this value to zero upon turning off PPS functionality
        
        # check and see if the voltage function input is in an invalid range of 0-20V
        if DEFAULT_OUTPUT_VOLTAGE_HIGH > 0x03:
            return -2
        elif DEFAULT_OUTPUT_VOLTAGE_HIGH == 0x03 and DEFAULT_OUTPUT_VOLTAGE_LOW > 0xE8:
            return -2

        # keep track of pps_voltage based on input parameters after verification
        self.pps_voltage = (DEFAULT_OUTPUT_VOLTAGE_LOW & 0xFF) | ((DEFAULT_OUTPUT_VOLTAGE_HIGH & 0xFF) << 8)

        # check and see if the current function input is not at either max operating current or in range of 50-6200mA
        if DEFAULT_OPERATING_CURRENT >= 0x7D:
            return -3
        
        dout=[]
        dout.append(ENABLE)
        dout.append(DEFAULT_OUTPUT_VOLTAGE_LOW)
        dout.append(DEFAULT_OUTPUT_VOLTAGE_HIGH)
        dout.append(DEFAULT_OPERATING_CURRENT)

        # write the data to the set_pps opcode 
        self.write_opcode(Set_PPS_Opcode, dout)
        
        # time.sleep(0.5)
        
        din=[]
        # get a response 
        din = self.read_opcode(Set_PPS_Opcode)
        return din[1] #return the status of the PPS from the second byte of returned data
    '''
    ##############################################################################################################################
    # @function update_pps_voltage() helper function called by the decrement/increment pps voltage function
    # @return 0 = PPS Off
    # @return 1 = PPS On
    # @return 6 = DP Configured State
    ##############################################################################################################################
    def update_pps_voltage(self):
        ENABLE = 0x01
        dout=[]
        dout.append(ENABLE)
        dout.append(self.pps_voltage & 0x00FF)
        dout.append((self.pps_voltage & 0xFF00) >> 8)
        dout.append(self.pps_operating_current)

        # write the data to the set_pps opcode at 
        self.write_opcode(Set_PPS_Opcode, dout)
        #self.write_opcode(APDO_SrcCap_Request_Opcode, dout)

        din=[]
        # get a response 
        din = self.read_opcode(Set_PPS_Opcode)
        #din = self.read_opcode(APDO_SrcCap_Request_Opcode)
        return din[1] #return the status of the PPS from the second byte of returned data
    '''

    ##############################################################################################################################
    # @function increment_pps_voltage() will increment the pps voltage setting by one hex valur = 10mV higher than before
    # @return -1 = PPS voltage = pps_voltage_max. already at maximum value allowable by user set value
    # @return 0 = PPS Off
    # @return 1 = PPS On
    # @return 6 = DP Configured State
    ##############################################################################################################################
    def increment_pps_voltage(self):
        if self.pps_voltage == self.pps_voltage_max:    # TODO Remove after done debugging. to make sure not above maximum threshold for charging
            return -1
        # increment value of the PPS voltage and update the value
        self.pps_voltage += 0x01
        din = self.update_pps_voltage()
        return din #return the status of the PPS 

    ##############################################################################################################################
    # @function decrement_pps_voltage() will increment the pps voltage setting by one hex valur = 10mV higher than before
    # @return -1 = PPS voltage = pps_voltage_min. already at minimum value allowable by user set value
    # @return 0 = PPS Off
    # @return 1 = PPS On
    # @return 6 = DP Configured State
    ##############################################################################################################################
    def decrement_pps_voltage(self):
        if self.pps_voltage == self.pps_voltage_min:    # TODO Remove after done debugging. check to make sure not below minimum threshold for charging
            return -1

        # increment value of the PPS voltage and update the value
        self.pps_voltage -= 0x01
        din = self.update_pps_voltage()
        return din #return the status of the PPS 

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

    

##############################################################################################################################################################
##############################################################################################################################################################
##############################################################################################################################################################
##############################################################################################################################################################
##############################################################################################################################################################
##############################################################################################################################################################
##############################################################################################################################################################
##############################################################################################################################################################
'''
u=MAX77958(SID=0x27)
while(1):
    time.sleep(1)
    u.set_qc5v()
    time.sleep(1)
    u.set_qc9v()
'''

