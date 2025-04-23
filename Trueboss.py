import os
import configparser
import vgamepad as vg
import time
import subprocess
import socket
import pyaudio
import numpy as np

# pyinstaller --onefile --add-binary "E:\anaconda3\Lib\site-packages\vgamepad\win\vigem\client\x64\ViGEmClient.dll;." Trueboss.py

# 配置文件路径
CONFIG_FILE = 'Trueboss.ini'

def create_default_config(path: str):
    """生成带注释的默认配置文件"""
    default_config_content = '''
# 延迟相关配置（单位：秒）
[Delays]
delay_firewall = 15          # 断网检测延迟（默认15秒）
delay_loading = 20           # 下云后延迟（默认20秒）
delay_offline_online = 40    # 线上切线下延迟（默认40秒）
button_hold_delay = 0.1      # 按键按下持续时间（默认0.1秒）
button_release_delay = 0.5   # 松开按键后等待时间（默认0.5秒）
button_hold_delay2 = 0.11    # 按键按下持续时间（默认0.11秒）
button_release_delay2 = 0.15 # 松开按键后等待时间（默认0.15秒）
button_release_delay3 = 1.5  # 松开按键后等待时间（默认1.5秒）

# 音频相关配置
[Audio]
format = pyaudio.paInt16     # 16-bit采样格式
channels = 2                 # 声道
rate = 44100                 # 采样率
chunk = 1024                 # 每次读取的帧数
threshold = 2.5              # 响度阈值（根据实际情况调整）
audio_timeout = 35           # 超时时间（秒）

# 断网相关配置
[Cutnetwork]
cutnetworkset = 0               # 0:固定时间检测下云都断网 1:检测到下云才断网

# 循环次数配置
[Loop]
iterations = 100             # 总循环次数（默认100次）

# 角色选择（1=富兰克林, 2=麦克, 3=崔佛）
[Character]
choice = 1                   # 默认角色：富兰克林
'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(default_config_content.strip() + '\n')
    print(f"未找到配置文件，已生成默认配置：{path}")

def load_config(path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser(
        inline_comment_prefixes=('#', ';')
    )
    try:
        # 检查配置文件存在性
        if not os.path.exists(path):
            raise FileNotFoundError

        # 读取并验证配置
        config.read(path, encoding='utf-8')

        # 验证必要配置项
        required_sections = ['Delays', 'Loop', 'Character']
        for section in required_sections:
            if not config.has_section(section):
                raise ValueError(f"缺少必要配置节：[{section}]")

        return config
    except Exception as e:
        print(f"配置文件错误 ({e})，已重新生成默认配置")
        create_default_config(path)
        config.read(path, encoding='utf-8')
        return config

def get_config_int(config: configparser.ConfigParser, section: str, option: str, default: int) -> int:
    """安全获取整型配置"""
    try:
        return config.getint(section, option)
    except (ValueError, configparser.NoOptionError, configparser.NoSectionError):
        print(f"配置项 [{section}]->{option} 无效，使用默认值 {default}")
        return default


def get_config_float(config: configparser.ConfigParser, section: str, option: str, default: float) -> float:
    """安全获取浮点型配置"""
    try:
        return config.getfloat(section, option)
    except (ValueError, configparser.NoOptionError, configparser.NoSectionError):
        print(f"配置项 [{section}]->{option} 无效，使用默认值 {default}")
        return default


# 初始化配置
if not os.path.exists(CONFIG_FILE):
    create_default_config(CONFIG_FILE)
config = load_config(CONFIG_FILE)

# 加载配置参数
delay_firewall = get_config_int(config, 'Delays', 'delay_firewall', 15)
delay_loading = get_config_int(config, 'Delays', 'delay_loading', 20)
delay_offline_online = get_config_int(config, 'Delays', 'delay_offline_online', 40)
button_hold_delay = get_config_float(config, 'Delays', 'button_hold_delay', 0.1)
button_release_delay = get_config_float(config, 'Delays', 'button_release_delay', 0.5)
button_hold_delay2 = get_config_float(config, 'Delays', 'button_hold_delay2', 0.11)
button_release_delay2 = get_config_float(config, 'Delays', 'button_release_delay2', 0.15)
button_release_delay3 = get_config_float(config, 'Delays', 'button_release_delay3', 1.5)
t = get_config_int(config, 'Loop', 'iterations', 100)
character = get_config_int(config, 'Character', 'choice', 1)
format = get_config_int(config, 'Audio', 'format', pyaudio.paInt16)     
channels = get_config_int(config, 'Audio', 'channels', 2)                      
rate = get_config_int(config, 'Audio', 'rate', 44100)                     
chunk = get_config_int(config, 'Audio', 'chunk', 1024)                     
threshold = get_config_float(config, 'Audio', 'threshold', 2.8)                  
audio_timeout = get_config_int(config, 'Audio', 'timeout ', 60)                     
cutnetworkset = get_config_int(config, 'Cutnetwork', 'cutnetworkset', 0)  
# 验证角色选择
if character not in (1, 2, 3):
    print("角色选择超出范围，已重置为默认（富兰克林）")
    character = 1
# 验证断网选择
if cutnetworkset not in (0,1):
    print("断网选择超出范围，已重置为默认（0:固定时间检测下云都断网）")
    cutnetworkset = 0
print(f"""运行参数：
  0. 断网方式      = {cutnetworkset} 0:固定时间检测下云都断网 1:检测到下云才断网
  1. 断网/检测下云延迟     = {delay_firewall} 秒
  2. 下云后延迟    = {delay_loading} 秒
  3. 下线延迟 = {delay_offline_online} 秒
  4. 按键保持时间  = {button_hold_delay2} 秒
  5. 松开等待时间  = {button_release_delay2} 秒
  4. 按键2保持时间 = {button_hold_delay} 秒
  5. 松开2等待时间 = {button_release_delay} 秒
  6. 按键3等待时间 = {button_release_delay3} 秒
  7. 循环次数     = {t}
  8. 当前角色     = {'富兰克林' if character == 1 else '麦克' if character == 2 else '崔佛'}
  9. 音频检测阈值 = {threshold}             
  10. 音频检测超时 = {audio_timeout}  秒
""")

# 创建音频实例
p = pyaudio.PyAudio()
# 获取输出设备
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    if device_info.get('name', '').find('CABLE Output') != -1:
        if device_info.get('hostApi', '') == 0:
            # print(device_info)
            index = i


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


def left_joystick(x_value, y_value):  # -1.0到1.0之间的浮点值
    gamepad.left_joystick_float(x_value, -y_value)


def right_joystick(x_value, y_value):  # -1.0到1.0之间的浮点值
    gamepad.right_joystick_float(x_value, -y_value)


def get_domain_ip(domain: str) -> str:
    return socket.gethostbyname(domain)

def cutnetwork():
    ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
    subprocess.run(
            f'netsh advfirewall firewall add rule '
            f'dir=out action=block protocol=TCP '
            f'remoteip="{ip},192.81.241.171" '
            f'name="仅阻止云存档上传"',
            shell=True,stdout=subprocess.DEVNULL
        )
def getRuntime():
    Runtime = time.time() - start_time
    # 将秒转换为小时、分钟、秒
    hours = int(Runtime // 3600)
    remaining_seconds = Runtime % 3600
    minutes = int(remaining_seconds // 60)
    seconds = int(remaining_seconds % 60)
    print(f"运行时间：{hours:02}:{minutes:02}:{seconds:02}\n")
def listening():
    audio_start_time = time.time()
    while True:
      if time.time() - audio_start_time > audio_timeout:
        print("超时，未检测到超过阈值的音频")
        break
      stream = p.open(
                format=format,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=index,
                frames_per_buffer=chunk,
            )
      data = stream.read(chunk, exception_on_overflow=False)
      audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
      rms = np.sqrt(np.mean(audio_data ** 2)) * 100 + 1e-10
      print(f"\r当前 RMS: {rms:.3f}", end='')
      if rms > threshold:
        print(f"\n检测到响度超过阈值: {rms:.3f} > {threshold}")
        cutnetwork()
        print("已断网:检测音频")
        break
    stream.close()


# 主逻辑
r = 0
start_time=time.time()
try:
    for _ in range(t):
        # 删除旧的防火墙规则
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,stdout=subprocess.DEVNULL)
        # 接电话/挂电话 3 次
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_hold_delay)
            time.sleep(button_release_delay)

        # 进入菜单并导航（原有操作）
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, button_hold_delay)
        time.sleep(button_release_delay)
        for _ in range(5):
            press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST, button_hold_delay2)
            time.sleep(button_release_delay2)
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(button_release_delay)
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH, button_hold_delay)
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(button_release_delay)
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH, button_hold_delay)
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, button_hold_delay)
        # 断网
        if cutnetworkset == 1:
            time.sleep(delay_firewall)
        else:
            time.sleep(delay_firewall)
            cutnetwork()
            print("已断网:固定延时")
        # 检测音频响度
        listening()
        # 下云后延迟
        time.sleep(delay_loading)
        print("发呆等电话…")
        # 切线下流程
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_release_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_release_delay)
            time.sleep(button_release_delay)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        gamepad.update()
        time.sleep(button_release_delay)
        print("切线下中…")
        # 依据角色摇杆
        if character == 1:
            right_joystick(0, 1)
        elif character == 2:
            right_joystick(-1, 0)
        else:
            right_joystick(1, 0)
        gamepad.update()
        time.sleep(button_release_delay)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)
        gamepad.update()
        gamepad.reset()
        gamepad.update()
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, button_hold_delay)
        # 线上到线下延迟
        time.sleep(delay_offline_online)
        r += 1
        print(f"已完成 {r} 次 \n")
        getRuntime()
except KeyboardInterrupt:
    print(f"\n已完成 {r} 次，检测到用户中断，正在清理防火墙规则…")
    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,stdout=subprocess.DEVNULL)
    print("防火墙规则已删除，程序安全退出！")
    if p.Stream.is_active==True:
        p.Stream.close()
    p.terminate()
