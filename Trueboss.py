import ctypes
import sys
from time import sleep
import pyaudio
import os
import subprocess
import win32com.client  # 用于访问 COM 对象
import configparser
import psutil
import time
import socket
import numpy as np
import vgamepad as vg
import webbrowser

# 配置文件路径
CONFIG_FILE = 'Trueboss.ini'
DOCUMENT_URL = 'https://docs.qq.com/doc/DVFNMaUZQWVpFYnhh'

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
format = 8     # 2=32-bit,4=24-bit,8=16-bit  采样格式 
channels = 2                 # 声道
rate = 44100                 # 采样率
chunk = 1024                 # 每次读取的帧数
threshold = 2.5              # 响度阈值（根据实际情况调整）
audio_timeout = 60           # 超时时间（秒）

# 杂项相关配置
[Miscset]
cutnetworkset = 0               # 0:固定时间检测下云都断网 1:检测到下云才断网
endset = 0                      # 0:最后一次断网回线下 1:最后不断网保存
run_mode = 0                    # 0:首次运行禁止GTA联网 1:直接开始循环取货

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
    print("正在为您打开使用文档...")
    try:
        webbrowser.open(DOCUMENT_URL)
        input("按回车键继续...")
    except Exception as e:
        print(f"打开文档失败: {e}")

    if not os.path.exists(CONFIG_FILE):
        create_default_config(CONFIG_FILE)
    config = load_config(CONFIG_FILE)

def show_document_prompt():
    print("\n" + "="*40)
    print("扣1查看最新使用文档回车跳过")
    print("="*40)
    choice = input("请输入选择：").strip()
    if choice == '1':
        try:
            webbrowser.open(DOCUMENT_URL)
            input("按回车键继续...")
        except Exception as e:
            print(f"打开文档失败: {e}")
    # else:
    #     # print("已跳过文档查看")

def load_config(path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser(
        inline_comment_prefixes=('#', ';')
    )
    try:
        if not os.path.exists(path):
            raise FileNotFoundError
        config.read(path, encoding='utf-8')
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

def check_dependencies():
    """环境依赖检测"""
    try:
        admin_check = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        admin_check = False
    if not admin_check:
        print("\n错误：请以管理员权限运行此程序！")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    try:
        import vgamepad as vg
    except Exception as e:
        print("\n错误：ViGEm驱动未安装！")
        choice = input("输入 1 安装驱动，输入其他任意字符退出：")
        if choice == '1':
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            installer = os.path.join(base, "ViGEmBus_1.22.0_x64_x86_arm64.exe")
            try:
                subprocess.run([installer], check=True)
            except Exception as e:
                print(f"安装失败：{e}")
                sys.exit(1)
        else:
            sys.exit()

    p = pyaudio.PyAudio()
    cable_found = any("CABLE Output" in p.get_device_info_by_index(i).get("name", "")
                      for i in range(p.get_device_count()))
    p.terminate()
    if not cable_found:
        print("\n错误：未找到虚拟音频设备！")
        choice = input("输入 1 安装驱动，输入其他任意字符退出：")
        if choice == '1':
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            installer = os.path.join(base_path, 'VBCABLE', 'VBCABLE_Setup_x64.exe')
            try:
                subprocess.run([installer], check=True)
            except Exception as e:
                print(f"虚拟声卡安装失败：{e}")
                sys.exit(1)
        else:
            sys.exit()

def is_firewall_enabled():
    """检测 Windows 防火墙是否开启（专用和公用配置文件）"""
    try:
        # 创建防火墙管理对象
        fw_mgr = win32com.client.Dispatch("HNetCfg.FwMgr")
        policy = fw_mgr.LocalPolicy

        # 检查专用配置文件 (NET_FW_PROFILE2_PRIVATE = 1)
        private_profile = policy.GetProfileByType(1)
        private_enabled = private_profile.FirewallEnabled

        # 检查公用配置文件 (NET_FW_PROFILE2_PUBLIC = 2)
        public_profile = policy.GetProfileByType(2)
        public_enabled = public_profile.FirewallEnabled

        # 只有当专用和公用配置文件的防火墙都开启时才返回 True
        return private_enabled and public_enabled
    except Exception as e:
        print(f"检测防火墙状态失败: {e}")
        return False

def check_firewall():
    """循环检测防火墙状态，直到专用和公用配置文件都开启"""
    while not is_firewall_enabled():
        input("检测到未开启防火墙，请开启防火墙后按回车键继续...")



# 加载配置
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
format = get_config_int(config, 'Audio', 'format', 8)
channels = get_config_int(config, 'Audio', 'channels', 2)
rate = get_config_int(config, 'Audio', 'rate', 44100)
chunk = get_config_int(config, 'Audio', 'chunk', 1024)
threshold = get_config_float(config, 'Audio', 'threshold', 2.5)
audio_timeout = get_config_int(config, 'Audio', 'audio_timeout', 60)
cutnetworkset = get_config_int(config, 'Miscset', 'cutnetworkset', 0)
endset = get_config_int(config, 'Miscset', 'endset', 0)
run_mode = get_config_int(config, 'Miscset', 'run_mode', 0)

# 前置检测
check_dependencies()
show_document_prompt()
check_firewall()


if run_mode not in (0, 1):
    print("运行模式参数无效，已重置为默认值0")
    run_mode = 0

# 验证角色选择
if character not in (1, 2, 3):
    print("角色选择超出范围，已重置为默认（富兰克林）")
    character = 1

# 验证断网选择
if cutnetworkset not in (0, 1):
    print("断网选择超出范围，已重置为默认（0:固定时间检测下云都断网）")
    cutnetworkset = 0

print(f"""你可以修改Trueboss.ini提升效率或者增强稳定性，修改后重启软件生效
运行参数：
  0. 断网方式      = {cutnetworkset}   0:固定时间检测下云都断网 1:检测到下云才断网
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
  10.音频检测超时 = {audio_timeout}  秒
  11.结束方式 = {endset}   0:最后一次断网回线下 1:最后不断网保存
  12.首次断网 = {run_mode} 0:首次运行禁止GTA联网 1:直接开始循环取货
  
""")

# 创建音频实例
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    if device_info.get('name', '').find('CABLE Output') != -1:
        if device_info.get('hostApi', '') == 0:
            index = i

# 创建手柄实例
gamepad = vg.VDS4Gamepad()

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

def left_joystick(x_value, y_value):
    gamepad.left_joystick_float(x_value, -y_value)

def right_joystick(x_value, y_value):
    gamepad.right_joystick_float(x_value, -y_value)

def get_domain_ip(domain: str) -> str:
    return socket.gethostbyname(domain)

def cutnetwork():
    if endset == 1:
        if r < t:
            ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
            subprocess.run(
                f'netsh advfirewall firewall add rule '
                f'dir=out action=block protocol=TCP '
                f'remoteip="{ip},192.81.241.171" '
                f'name="仅阻止云存档上传"',
                shell=True, stdout=subprocess.DEVNULL
            )
        else:
            print("最后一次保存不断网")
    else:
        ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
        subprocess.run(
            f'netsh advfirewall firewall add rule '
            f'dir=out action=block protocol=TCP '
            f'remoteip="{ip},192.81.241.171" '
            f'name="仅阻止云存档上传"',
            shell=True, stdout=subprocess.DEVNULL
        )
def find_gta5_process():
    """新增：查找正在运行的GTA5进程"""
    valid_names = ['GTA5.exe', 'GTA5_Enhanced.exe']
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            if proc.info['name'] in valid_names and proc.info['exe']:
                print(f"找到进程：{proc.info['name']} 路径：{proc.info['exe']}")
                return proc.info['exe']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def getRuntime():
    Runtime = time.time() - start_time
    hours = int(Runtime // 3600)
    remaining_seconds = Runtime % 3600
    minutes = int(remaining_seconds // 60)
    seconds = int(remaining_seconds % 60)
    print(f"运行时间：{hours:02}:{minutes:02}:{seconds:02}\n")

def listening():
    audio_start_time = time.time()
    stream = p.open(
            format=format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=index,
            frames_per_buffer=chunk,
        )
    while True:
        if time.time() - audio_start_time > audio_timeout:
            print("超时！未检测到超过阈值的音频")
            break
        data = stream.read(chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16
                                   ).astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_data ** 2)) * 100 + 1e-10
        print(f"\r当前 RMS: {rms:.3f}", end='')
        if rms > threshold:
            print(f"\n检测到响度超过阈值: {rms:.3f} > {threshold}")
            cutnetwork()
            print("已断网！检测到下云音频")
            break
    stream.close()

def listening2():
    audio_start_time = time.time()
    stream = p.open(
            format=format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=index,
            frames_per_buffer=chunk,
        )
    while True:
        if time.time() - audio_start_time > audio_timeout:
            print("超时！未检测到超过阈值的音频")
            break
        data = stream.read(chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16
                                   ).astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_data ** 2)) * 100 + 1e-10
        print(f"\r当前 RMS: {rms:.3f}", end='')
        if rms > threshold:
            print(f"\n检测到响度超过阈值: {rms:.3f} > {threshold}")
            exe_path = find_gta5_process()
            if not exe_path:
                print("\n错误！未找到运行中的GTA5！")
                input("请确保游戏正在运行，按回车键退出程序...")
                sys.exit(1)

            cmd = f'''
                            netsh advfirewall firewall add rule 
                            name="仅阻止云存档上传" 
                            dir=out 
                            action=block 
                            program="{exe_path}" 
                            protocol=TCP 
                            enable=yes
                            '''
            subprocess.run(
                ' '.join(cmd.split()),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("已断开GTA5网络全部防止上传！")
            break
    stream.close()

# 主逻辑
r = 0
start_time = time.time()
try:
    if run_mode == 0:
        # 新增初始化操作
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        print("正在执行初始化流程...")
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_hold_delay)
            time.sleep(button_release_delay)
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
        time.sleep(button_release_delay3)
        listening2()
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(delay_loading)
        # time.sleep(10)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        gamepad.update()
        time.sleep(button_release_delay)
        print("试图切线下角色")
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
        time.sleep(delay_loading)
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        for _ in range(2):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT, button_hold_delay)
            time.sleep(button_release_delay3)
        sleep(button_release_delay3)

        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        sleep(delay_loading)
        print("初始化操作完成，开始主循环...")

    for _ in range(t):
        r += 1
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_hold_delay)
            time.sleep(button_release_delay)
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
        if cutnetworkset == 1:
            time.sleep(delay_firewall)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        else:
            time.sleep(delay_firewall)
            cutnetwork()
            print("已断网！检测到固定延时")
        listening()
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(delay_loading)
        print("发呆等电话…")
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_release_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_release_delay)
            time.sleep(button_release_delay)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        gamepad.update()
        time.sleep(button_release_delay)
        print("切线下中…")
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
        time.sleep(delay_offline_online)
        print(f"已完成 {r} 次 \n")
        getRuntime()
except KeyboardInterrupt:
    print(f"\n已完成 {r} 次，检测到用户中断，正在清理防火墙规则…")
    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                   stdout=subprocess.DEVNULL)
    print("防火墙规则已删除，程序安全退出！")
    if p.Stream.is_active == True:
        p.Stream.close()
    p.terminate()