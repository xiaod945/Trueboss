import vgamepad as vg
import time
import subprocess
import socket
import pyaudio
import numpy as np
import configparser
#pyinstaller --onefile --add-binary "E:\anaconda3\envs\py312\Lib\site-packages\vgamepad\win\vigem\client\x64\ViGEmClient.dll;." Trueboss.py
#生成配置文件
config = configparser.ConfigParser()
#创建音频实例
p = pyaudio.PyAudio()
# 获取输出设备
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    if device_info.get('name', '').find('CABLE Output') != -1:
        if  device_info.get('hostApi', '') == 0:
          print("已绑定vb虚拟声卡")
          index=i
# 音频参数
FORMAT = pyaudio.paInt16  # 16-bit采样格式
CHANNELS = 2
RATE = 44100              # 采样率
CHUNK = 1024            # 每次读取的帧数
THRESHOLD = 3           # 响度阈值（根据实际情况调整）
TIMEOUT = 60           # 超时时间（秒）
        
# 创建手柄实例
gamepad = vg.VDS4Gamepad()
# 辅助函数保持不变
def press_button(gamepad, button, hold_time):
    gamepad.press_button(button=button)
    gamepad.update()
    time.sleep(hold_time)
    gamepad.release_button(button=button)
    gamepad.update()

def press_special_button(gamepad, special_button, hold_time):
    gamepad.press_special_button(special_button=special_button)
    gamepad.update()
    time.sleep(hold_time)
    gamepad.release_special_button(special_button=special_button)
    gamepad.update()

def press_dpad(gamepad, direction, hold_time):
    gamepad.directional_pad(direction=direction)
    gamepad.update()
    time.sleep(hold_time)
    gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)
    gamepad.update()
def left_joystick(x_value, y_value): #-1.0到1.0之间的浮点值
    gamepad.left_joystick_float(x_value, -y_value) 
def right_joystick(x_value, y_value):# -1.0到1.0之间的浮点值
    gamepad.right_joystick_float(x_value, -y_value)
def get_domain_ip(domain: str) -> str:
        ip = socket.gethostbyname("cs-gta5-prod.ros.rockstargames.com")
        return ip
# 获取用户输入的延迟时间
def get_delay_input(prompt, default):
    while True:
        try:
            user_input = input(f"{prompt} ") or default
            return int(user_input)
        except ValueError:
            print("请输入有效的整数！")
def cutnetwork ():
        # 设置防火墙规则（需管理员权限运行）
        ip = socket.gethostbyname("cs-gta5-prod.ros.rockstargames.com")
        subprocess.run(
        f'netsh advfirewall firewall add rule '
        f'dir=out action=block protocol=TCP '
        f'remoteip="{ip},192.81.241.171" '
        f'name="仅阻止云存档上传"',
        shell=True)
        print("断网")
def listening():
    start_time = time.time()
    while True:
        # 检查超时
         if time.time() - start_time > TIMEOUT:
          print("超时，未检测到超过阈值的音频")
          time.sleep(99999)
          break
        #创建音频流
         stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            input_device_index=index,
            frames_per_buffer=CHUNK,)

            # 读取音频数据
         data = stream.read(CHUNK, exception_on_overflow=False)
         audio_data = np.frombuffer(data, dtype=np.int16)
         audio_data = audio_data.astype(np.float32) / 32768.0  # 强制归一化
            #计算响度
         rms = np.sqrt(np.mean(audio_data**2))+1e-10
         rms=rms*100
         print(rms,f"当前rms: {rms:.3f}", end='\r')  # 实时显示

         if rms > THRESHOLD:
          print(f"\n检测到响度超过阈值: {rms:.3f} > {THRESHOLD}")
          break
        #监听收尾处理
    stream.close() 
def storymode():
            #切线下
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)#接电话
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, 0.1)#挂电话
            time.sleep(0.1)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)#角色选择器
        gamepad.update()
        time.sleep(1)
        right_joystick(0, 1)#向上小富
        gamepad.update()
        time.sleep(0.3)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)#取消角色选择器
        gamepad.update()
        gamepad.reset()
        gamepad.update()
        time.sleep(0.3)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.2)#确认切线下
        time.sleep(0.3)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, 0.2)#确认切线下 
           
print("请设置各环节延迟（直接回车使用默认值）：")
delay_firewall = get_delay_input("1. 进线上断网和检测音频延迟，默认13秒：", 13)
delay_loading = get_delay_input("2. 下云后取货的延迟，默认18秒：", 18)
delay_offline_online = get_delay_input("3. 从线上退回到线下的延迟，默认20秒：", 20)
t= get_delay_input("4. 拉货次数，默认100次", 100) #循环次数
r=0#运行次数
runtime=time.time()
try:
    # 主循环
    for _ in range(t):
        # 删除防火墙规则（循环开始时原有操作）
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True)
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)#接电话
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, 0.1)#挂电话
            time.sleep(0.1)
        # 按 OPTIONS 键，保持 0.5 秒
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, 0.1)
        time.sleep(0.5)
        # 按右方向键 5 次，每次 50 毫秒
        for _ in range(5):
            press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST, 0.05)
            time.sleep(0.05)
        time.sleep(1.5)
        # 按 CROSS 键，保持 0.2 秒
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.2)
        time.sleep(0.3)
        # 按上方向键一次，100 毫秒
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH, 0.2)
        time.sleep(0.3)
        # 按 CROSS 键，保持 0.3 秒
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.2)
        time.sleep(0.3)
        # 按下方向键一次
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH, 0.2)
        time.sleep(0.3)
        # 按 CROSS 键
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.2)
        time.sleep(0.3)
        # 按 CROSS 键，保持 0.3 秒
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.2)
        time.sleep(0.3)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, 0.2)
        #断网和检测音频的延迟
        time.sleep(delay_firewall)
        cutnetwork()
        listening()
        time.sleep(delay_loading)# 线上下云后的延迟
        storymode()
        time.sleep(delay_offline_online)# 从线上到线下的延迟
        r=r+1
        runningtime=(time.time()-runtime)
        print("\n已完成",r,"次","耗时：",runningtime)
except KeyboardInterrupt:
    print("\n已完成",r,"次，检测到用户中断，正在清理防火墙规则...")
    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True)
    print("防火墙规则已删除，程序安全退出！")



        
    
