#Basic operations for MAX77818
import time
from smbus2 import SMBus
bus = SMBus(1)

class MAX77818:
    def __init__(self,top=0x66,chg=0x69,fg=0x36):
        try:
            bus.write_byte(0x36,0x0)
            self.connected = True
        except:
            self.connected = False
        if (self.r(0xbd) & 0xC >>2) == 3:
            self.unlocked = True
            print("Self.unlocked = {}".format(self.unlocked))
        else:
            self.unlocked = False
        self.top=top
        self.chg=chg
        self.fg=fg

    def r(self,reg_addr,l=1,slave=0x69):
        if l == 1:
            return bus.read_byte_data(slave,reg_addr)
        else:
            return bus.read_i2c_block_data(slave,reg_addr,l)
    def w(self,addr,data,l=1,slave=0x69):
        if (l==1) or (type(data) is not list):
            bus.write_byte_data(slave,addr,data)
        else:
            bus.write_i2c_block_data(slave,addr,data)
    def rw(self,reg,s=0x36):
        data=bus.read_word_data(s,reg)
        return data
    def set_lock(self,lock):
        lock_reg = self.r(0xbd)
        if lock in ["unlock", "Unlock","U",'u',0,True]:
            self.w(0xbd,(lock_reg&0xF3)|0xC)
            self.unlocked = True
        else:
            self.w(0xbd,lock_reg&0xF3)
            self.unlocked = False
    def set_cv(self,voltage):
        #locks = self.unlocked
        #if not self.unlocked:
        self.set_lock('unlock')
        chg_cnfg_04 = self.r(0xbb)
        if type(voltage) is float or type(voltage) is int:
            if voltage < 4.33999:
                v = max(0,int(((voltage * 1000) - 3650)/25))
            elif voltage < 4.34999:
                v = 0x1C
            else:
                v = min(0x2b,max(0x1D,0x1D+int(((voltage * 1000) - 4350)/25)))            
        elif voltage in ['up', 'Up', 'UP', 'u','U']:
            v = min((chg_cnfg_04 & 0x3F)+1, 0x2B)
        elif voltage in ['d', 'down','Down','D']:
            v = max((chg_cnfg_04&0x3F)-1, 0x0)
        else:
            v = min(0x2B,max(0,int(voltage,16)))
        print("Voltage = {}, hex = {}".format(voltage,hex(v)))
        self.w(0xbb,(chg_cnfg_04 & 0xC0)|v)
        #self.set_lock(locks)

    def set_cc(self,curr):
        locks = self.unlocked
        if not self.unlocked:
            self.set_lock('unlock')
        chg_cnfg_02 = self.r(0xb9)
        if type(curr) is float or type(curr) is int:
            if curr < 4.0:  #Amps to mA
                curr = curr * 1000.0
            c = min(max(0,int(curr/50)),0x3f)
        else:
            try:
                curr = int(curr,16)
                c = min(max(0,int(curr)),0x3f)
            except:
                print("Invalid CC value")
        self.w(0xb9,((chg_cnfg_02 & 0xC0)| c))
        self.set_lock(locks)

    def set_input_lim(self,curr):
        if type(curr) is float or type(curr) is int:
            if curr < 6.0:  #Amps to mA
                curr = curr * 1000.0
            c = min(max(0,int(curr/33)),0x7f)
        else:
            try:
                curr = int(curr,16)
                c = min(max(0,int(curr)),0x7f)
            except:
                print("Invalid input current limit value")
        #print("Current = {}     Reg = {}".format(curr, hex(c)))
        self.w(0xC0, c)
    def set_mode(self,mode):
        chg_cnfg_00 = self.r(0xb7)
        self.w(0xb7,(chg_cnfg_00 & 0xF0 )| min(0xF,mode))
    def show_chg_details(self):
        dtls0=self.r(0xb3)
        dtls1=self.r(0xb4)
        dtls2=self.r(0xb5)
        if dtls0 & 0x60 == 0x60:
            print("MAX77818 VBUS Valid")
        if dtls0 & 0x1 == 1:
            print("MAX77818 BATT Presence detected")
         
        print("CHG_DTLS = "+"   ".join(map(hex,[dtls0,dtls1,dtls2]))) 
    def get_chg_stat(self):
        data=self.r(0xb4)
        return data&0xF
