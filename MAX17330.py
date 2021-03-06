import smbus,time

bus=smbus.SMBus(1)
#sa = 0x36
class MAX17330(object):     #object):   #Gpib in raspberry pi

    def __init__(self,sa=0x36,rsns=10,verbose=True):       #Schematic has Pin 13 for MAX17330_1, 15 for MAX17330_2
        self.verbose=verbose
        self.sa=sa
        self.sa2={0x36:0x0b,0x72:0x4f,0x32:0x0f,0x76:0x4b}[sa]
        self.rsns=rsns
        try:
            bus.write_quick(sa)
            print("Received ACK at {}".format(hex(sa)))
        except:
            print("Did not receive ACK at {}".format(hex(sa)))
        try:
            bus.write_quick(self.sa2)
            print("Received ACK at {}".format(hex(self.sa2)))
        except:
            print("Did not receive ACK at {}".format(hex(self.sa2)))

    def r(self,reg,sa,h=True):
        data=bus.read_byte_data(sa,reg)
        if h:
            return hex(data)
        else:
            return data

    def w(self,reg,data,sa):
        return bus.write_byte_data(sa,reg,data)

    def rw(self,reg,sa):
        #if l==1:
        data=bus.read_word_data(sa,reg)
        '''else:
            data=[]
            temp_data=[]
            for i in range(l):
                temp_data.append(bus.read_i2c_block_data(s,addr,l*2))
            for i in range(len(temp_data)):
                if i % 2 == 1:
                    data.append(data[i]<<8 | data[i-1])'''
        return data

    def ww(self,reg,data,sa):
        return bus.write_word_data(sa,reg,data)

    def unlock_WP(self):
        self.ww(0x61,0x0,self.sa)
        self.ww(0x61,0x0,self.sa)
    def lock_WP(self):
        prev_val = self.rw(0x61,self.sa)
        val = (prev_val & 0xFF07) | 0xF8
        self.ww(0x61,val,self.sa)
    
    def get_vcell(self):
        data=self.rw(0x1A,self.sa)
        return data * 0.000078125
    
    def get_vpckp(self):
        data = self.rw(0xdb,self.sa)
        return data * 0.0003125
    def get_ibatt(self):
        return self.twos_comp(self.rw(0x1C,self.sa))*0.15625*10/self.rsns
    def get_ichg(self):
        return self.twos_comp(self.rw(0x28,self.sa))*0.15625*10/self.rsns

    def is_dropout(self):
        data_before_stat_reg_CA_bit_clear = self.rw(0xa3,self.sa)
        old_status_reg_value = 0
        if (data_before_stat_reg_CA_bit_clear & 0x8000) >0:
            # Clearing CA bit 11 in reg 0x0000 to detect next event
            old_status_reg_value = self.rw(0x00,self.sa)
            if (old_status_reg_value & 0x0800) > 0:
                new_status_reg_value = old_status_reg_value & 0xF7FF # And with inverse of 0x0800 to clear bit
                self.ww(0x00,new_status_reg_value,self.sa)
                print()
            return True
        else:
            return False 

    def is_cp_event(self):
        data_before_stat_reg_CA_bit_clear = self.rw(0xa3,self.sa)
        old_status_reg_value = 0
        if (data_before_stat_reg_CA_bit_clear & 0x0008) >0:
            # Clearing CA bit 11 in reg 0x0000 to detect next event
            old_status_reg_value = self.rw(0x00,self.sa)
            if (old_status_reg_value & 0x0800) > 0:
                new_status_reg_value = old_status_reg_value & 0xF7FF # And with inverse of 0x0800 to clear bit
                self.ww(0x00,new_status_reg_value,self.sa)
                print()
            return True
        else:
            return False 

    def is_ct_event(self):
        data_before_stat_reg_CA_bit_clear = self.rw(0xa3,self.sa)
        old_status_reg_value = 0
        if (data_before_stat_reg_CA_bit_clear & 0x0004) >0:
            # Clearing CA bit 11 in reg 0x0000 to detect next event
            old_status_reg_value = self.rw(0x00,self.sa)
            if (old_status_reg_value & 0x0800) > 0:
                new_status_reg_value = old_status_reg_value & 0xF7FF # And with inverse of 0x0800 to clear bit
                self.ww(0x00,new_status_reg_value,self.sa)
                print()
            return True
        else:
            return False 

        

    # Used to keep track if crosscharge is enabled or not
    crosscharge_enabled = 0

    # Used to set the par_en bit to enable parallel charging feature
    def set_par_en_bit(self, value): # concerns nPackCfg Register(1B5h) 
        reg_addr = 0x1b5
        bit_mask = 0x01 << 6 # par en is the 6th bit
        reg_data_before_bit_clear = self.rw(reg_addr,self.sa)
        reg_data_after_bit_clear = reg_data_before_bit_clear & 0xFFBF # 0xFFBF is the inverse of 0x01 << 6 bits
        new_reg_data = 0
        if value is 1:
            new_reg_data = reg_data_after_bit_clear | bit_mask
            self.crosscharge_enabled = 1
        else:
            new_reg_data = reg_data_after_bit_clear
            self.crosscharge_enabled = 0
        self.ww(reg_addr,new_reg_data,self.sa)
        return True
    
    # Indicate charger presense to all batteries (even blocked batteries)
    def allow_chg_b(self): # concerns Status Register (000h)
        reg_addr = 0x000
        reg_data_before_bit_clear = self.rw(reg_addr,self.sa)
        new_reg_data = reg_data_before_bit_clear & 0xFFDF # 0xFFBF is the inverse of 0x01 << 5 bits
        self.ww(reg_addr,new_reg_data,self.sa)
        return

    # when this function is called, it returns whether or not there is a battery connected to this IC or not
    def check_bst_bit(self): # concerns Status Register (000h)  
        reg_addr = 0x000
        bit_mask = 0x01 << 3 # bst is the 3rd bit
        reg_data = self.rw(reg_addr,self.sa) & bit_mask
        if reg_data:
            return True
        else:
            return False

    def set_VChg(self,VChg):
        self.unlock_WP()
        if type(VChg)==float:
            VChg=min(127,max(-128,int(round((VChg- 4.2)/0.005,0))))
            print("VChg = {}".format(hex(VChg)))
        prev_val = self.rw(0xD9,self.sa2)
        self.ww(0xd9,((prev_val & 0xFF)|(VChg <<8)),self.sa2)
        self.lock_WP()
        return self.rw(0xD8,self.sa2)

    def set_IChg(self,IChg):
        self.unlock_WP()
        self.ww(0xdb,0xff00,self.sa2)       #Disable Step Charge
        prev_val = self.rw(0xD8,self.sa2)
        self.ww(0xd8,((prev_val & 0xFF)|(IChg <<8)),self.sa2)
        return self.rw(0xD8,self.sa2)
        self.lock_WP()

    def twos_comp(self,data):
        if data>0x7FFF:
            return data - 0xffff
        else:
            return data
    def reg_list(self):
        reg_arr=[]
        for x in range(256):
            reg_arr.append("{}:{}".format(hex(self.sa),hex(x)))
        for x in range(256):
            reg_arr.append("{}:{}".format(hex(self.sa2),hex(x)))
        return reg_arr
    def read_line(self):
        data = []
        for x in range(256):
            data.append(self.rw(x,self.sa))
        for x in range(256):
            data.append(self.rw(x,self.sa2))
        return data
    def load_RAM_ini(self,fname):
        data_arr=[]
        with open(fname,'r') as f:
            for line in f:
                if "//" in line:
                    data=line.split(" = ")
                    reg=int(data[0],16)-256
                    val=int(data[1].split("\t")[0],16)
                    if not (reg in [0xb5,0xbc,0xbd,0xbe,0xbf]):
                        self.ww(reg,val,self.sa2)
            self.ww(0xAB,self.rw(0xab,self.sa)|0x8000,self.sa)
            while(self.rw(0xab,self.sa)&0x8000 == 0x8000):
                time.sleep(0.010)
                    
