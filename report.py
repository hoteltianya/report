#coding:utf-8
import subprocess
import socket
import paramiko,os,sys,time
import requests
import shutil
import json
import fcntl
import struct

port = 22
user = 'root'
NUM = 0
SCPNUM =0


def get_file_list(file_path):
    dir_list = os.listdir(file_path)
    if not dir_list:
        return
    else:
        # 注意，这里使用lambda表达式，将文件按照最后修改时间顺序升序排列
        # os.path.getmtime() 函数是获取文件最后修改时间
        # os.path.getctime() 函数是获取文件最后创建时间
        dir_list = sorted(dir_list,  key=lambda x: os.path.getmtime(os.path.join(file_path, x)))
        # print(dir_list)
        return dir_list


def get_host_ip():
    """
    查询本机ip地址
    :return: ip
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def ssh_scp_put(ip,port,user,password,local_file,remote_file):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, 22, 'root', password)
    a = ssh.exec_command('date')
    stdin, stdout, stderr = a
    # print(stdout.read())
    sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
    sftp.put(local_file, remote_file)

class ReportDiskInfo(object):
    def __init__(self):
        self.diskdict={}
        self.disksmartdict = {}
        


    def get_disk_list(self):
        # 使用lsscsi命令获取盘片的modle和盘符
        cmd = "lsscsi -g"
        diskilist = subprocess.getoutput(cmd).split('\n')
        for disk in diskilist:
            disk = disk.split()
            self.diskdict[disk[3]] = disk[5]
        print(self.diskdict)

    def get_disk_smartinfo(self):
        for key in self.diskdict:
            if "b3" in key or "15nm" in key:
                cmd = f"smartctl -a {self.diskdict[key]}"
                self.disksmartdict[key] = subprocess.getoutput(cmd)
        # print(self.disksmartdict)
    
    def post_info(self):
        # 将生成的文件发送到服务端
        global NUM
        global SCPNUM
        global ip
        print(NUM, SCPNUM, ip)
        
        with open(ip, 'w') as f:
            jsonfile = json.dumps(self.disksmartdict)
            f.write(jsonfile)
        rename = ip+f'-{NUM}'
        NUM = NUM + 1
        shutil.copy(ip, rename)

        try: 
            ssh_scp_put('192.168.226.80', 22, 'root', '123456', ip+f'-{SCPNUM}', f'/home/sumu/smart/{ip}-{SCPNUM}')
            SCPNUM = SCPNUM + 1
            while NUM-SCPNUM:
                ssh_scp_put('192.168.226.80', 22, 'root', '123456', ip+f'-{SCPNUM}', f'/home/sumu/smart/{ip}-{SCPNUM}')
                SCPNUM = SCPNUM + 1
        except Exception as e:
            pass



class ReportScriptInfo(object):
    def __init__(self):
        # 微信机器人的头
        self.roboturl = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a1b241da-c877-44b8-a5b4-a67dd95792fa"
        self.headers = {"Content-Type": "application/json"}
        self.scripts = {}
        self.ip = get_host_ip()
        flag = 1
        while flag:
            flag = input("请输入需要监控的脚本关键字请尽量完整，每次输一条，若无则请直接按enter：")
            if flag:
                num = eval(input("数量，你需要监控几条这样关键字的脚本："))
                self.scripts[flag] = num

    def get_script_info(self,):
        for script in self.scripts:
            cmd = f"ps -ef|grep {script}"
            if subprocess.getoutput(cmd).count("\n") < self.scripts[script] + 1:
                self.data = {"msgtype": "text",
                    "text": {"content": f"主机{self.ip}上的带有关键字{script}的脚本有至少一个停止，请检查",}}
                try:
                    r1 = requests.post(self.roboturl, headers=self.headers, json = self.data)
                except Exception as e:
                    pass

                # print(666666)




class Data2Robot(object):
    def __init__(self): 
        self.reportdisk = {}
        self.roboturl = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a1b241da-c877-44b8-a5b4-a67dd95792fa"
        self.headers = {"Content-Type": "application/json"}
        
        self.path = '/home/sumu/smart/'
        self.bakpath = '/home/sumu/baksmart/'
        self.host_disk_smart_dict = {}
        self.walistinfo = ['164', '165', '166', '167', '233', '241', '242']
    def get_new_data(self):
        # 遍历路径下的所有文件，将文件内容读取出字典，读完之后将文件移动到备份路径
        filenames = get_file_list(self.path)
        for filename in filenames:
            filepath = os.path.join(self.path, filename)
            bakpath = self.bakpath + filename
            self.host_disk_smart_dict[filename] = {}
            self.reportdisk[filename] = {}
            with open(filepath, 'r') as f:
                str_json = f.read()
                host_smartdict = json.loads(str_json)
                # print(host_smartdict)
                for disk in host_smartdict:
                    a = host_smartdict[disk].split('\n')
                    # print(disk)
                    # print(a)
                    smartlist = {}
                    for disksmart in a:
                        i = disksmart
                        if '172 Unknown_Attribute' in i:
                            smartlist['172'] = int(i.split()[-1])
                        if '5 Reallocated_Sector_Ct' in i:
                            smartlist['05'] = int(i.split()[-1])
                        if '171 Unknown_Attribute' in i:
                            smartlist['171'] = int(i.split()[-1])
                        if '160 Unknown_Attribute' in i:
                            smartlist['UNC'] = int(i.split()[-1])
                        if '12 Power_Cycle_Count' in i:
                            smartlist['12'] = int(i.split()[-1])
                        if '241 Total_LBAs_Written' in i:
                            smartlist['241'] = int(i.split()[-1])
                        if '245 Unknown_Attribute' in i:
                            smartlist['245'] = int(i.split()[-1])
                        if '195 Hardware_ECC_Recovered' in i:
                            smartlist['C3'] = int(i.split()[-1])
                        if '199 UDMA_CRC_Error_Count' in i:
                            smartlist['CRC'] = int(i.split()[-1])
                        if '164 Unknown_Attribute' in i:
                            smartlist['164'] = int(i.split()[-1])
                        if '165 Unknown_Attribute' in i:
                            smartlist['165'] = int(i.split()[-1])
                        if '166 Unknown_Attribute' in i:
                            smartlist['166'] = int(i.split()[-1])
                        if '167 Unknown_Attribute' in i:
                            smartlist['167'] = int(i.split()[-1])
                        if '242 Total_LBAs_Read' in i:
                            smartlist['242'] = int(i.split()[-1])
                        if '233 Media_Wearout_Indicator' in i:
                            smartlist['233'] = int(i.split()[-1])
                    try:
                        if smartlist['172'] > 0 \
                            or smartlist['05'] > 0\
                            or smartlist['171'] > 0\
                            or smartlist['UNC'] >0\
                            or smartlist['CRC'] > 0:
                            self.reportdisk[filename][disk] = smartlist
                    except Exception as e:
                        pass
                    with open(disk, 'a', newline='\n') as f:
                        for i in self.walistinfo:
                            f.write(f'{smartlist[i]},')
                        f.write('\n')
                    self.host_disk_smart_dict[filename][disk] = smartlist
                shutil.move(filepath, bakpath) 


    def post2robot(self):
        self.reportdata = json.dumps(self.reportdisk)
        self.data = {"msgtype": "text",
                    "text": {"content": f"{self.reportdata}",}
                    }
        try:
            r1 = requests.post(self.roboturl, headers=self.headers, json=self.data)
        except Exception as e:
            pass


def report_smartinfo():
    a = ReportDiskInfo()
    a.get_disk_list()
    a.get_disk_smartinfo()
    a.post_info()

def report2robot():
    a = Data2Robot()
    a.get_new_data()
    a.post2robot()


def main():
    # 执行的主函数，判断需要进行监控和上报哪些内容
    flag_smart = eval(input("是否要上报smart信息（是：1，否0）："))    
    flag_script = eval(input("是否需要监控脚本运行状态（是：1，否0）："))
    sleeptime = eval(input("间隔时间，每隔多少秒检查一次："))
    if flag_script:
        p1 = ReportScriptInfo()
        while 1:
            p1.get_script_info()
            if flag_smart:
                report_smartinfo()
            time.sleep(sleeptime)

    elif flag_smart:
        while 1:
            report_smartinfo()
            time.sleep(sleeptime)
    else:
        print("没有执行任何监控")

def report():
    while 1:
        report2robot()
        time.sleep(120)
        
ip = get_host_ip()
main()
# report()