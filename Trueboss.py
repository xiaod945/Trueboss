import os
import configparser
import vgamepad as vg
import time
import subprocess
import socket
import pyaudio
import numpy as np

# pyinstaller --onefile --add-binary "E:\anaconda3\Lib\site-packages\vgamepad\win\vigem\client\x64\ViGEmClient.dll;." Trueboss.py

# 配置文件相关
CONFIG_FILE = 'config.ini'
DEFAULT_CONFIG = {
    'Delays': {
        'delay_firewall': '10',
        'delay_loading': '12',
        'delay_offline_online': '20',
    },
    'Loop': {
        'iterations': '100',
    },
    'Character': {
        # 1=富兰克林, 2=麦克, 3=崔佛
        'choice': '1',
    }
}

def create_default_config(path: str):
    """生成默认配置文件"""
    config = configparser.ConfigParser()
    config.read_dict(DEFAULT_CONFIG)
    with open(path, 'w', encoding='utf-8') as f:
        config.write(f)
    print(f"未找到配置文件，已生成默认配置：{path}")

def load_config(path: str) -> configparser.ConfigParser:
    """读取配置文件，格式错误时回退到默认配置"""
    config = configparser.ConfigParser()
    try:
        config.read(path, encoding='utf-8')
        # 检查必要的 section 和 option
        for section, opts in DEFAULT_CONFIG.items():
            if not config.has_section(section):
                raise ValueError(f"缺少节: {section}")
            for option in opts:
                if not config.has_option(section, option):
                    raise ValueError(f"节[{section}]缺少项: {option}")
        print(f"已加载配置文件：{path}")
    except Exception as e:
        print(f"读取配置文件失败 ({e})，使用默认配置")
        config.read_dict(DEFAULT_CONFIG)
    return config

def get_config_int(config: configparser.ConfigParser, section: str, option: str, default: int) -> int:
    """安全获取整型配置，格式错误时使用默认值"""
    try:
        val = config.getint(section, option)
        return val
    except Exception:
        print(f"配置项 [{section}]->{option} 无效，使用默认值 {default}")
        return default

# 1. 配置文件存在性检查 & 加载
if not os.path.exists(CONFIG_FILE):
    create_default_config(CONFIG_FILE)

config = load_config(CONFIG_FILE)

# 2. 从配置中读取参数
delay_firewall = get_config_int(config, 'Delays', 'delay_firewall', 10)
delay_loading = get_config_int(config, 'Delays', 'delay_loading', 12)
delay_offline_online = get_config_int(config, 'Delays', 'delay_offline_online', 20)
t = get_config_int(config, 'Loop', 'iterations', 100)
character = get_config_int(config, 'Character', 'choice', 1)
if character not in (1, 2, 3):
    print("角色选择超出范围，已重置为默认（富兰克林）")
    character = 1

print(f"""运行参数：
  1. 断网检测延迟 = {delay_firewall} 秒
  2. 下云后延迟   = {delay_loading} 秒
  3. 线下上线延迟 = {delay_offline_online} 秒
  4. 循环次数     = {t}
  5. 角色        = {'富兰克林' if character == 1 else '麦克' if character == 2 else '崔佛'}
""")

# 创建音频实例
p = pyaudio.PyAudio()
# 获取输出设备
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    if device_info.get('name', '').find('CABLE Output') != -1:
        if device_info.get('hostApi', '') == 0:
            print(device_info)
            index = i
# 设备选择
# index = int(input("请输入设备序号: "))
print("已选择", index, "号")

# 音频参数
FORMAT = pyaudio.paInt16  # 16-bit采样格式
CHANNELS = 2
RATE = 44100  # 采样率
CHUNK = 1024  # 每次读取的帧数
THRESHOLD = 2.8  # 响度阈值（根据实际情况调整）
TIMEOUT = 35  # 超时时间（秒）

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


# 主逻辑
r = 0
try:
    for _ in range(t):
        # 删除旧的防火墙规则
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True)

        # 接电话/挂电话 3 次
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, 0.1)
            time.sleep(0.1)

        # 进入菜单并导航（原有操作）
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, 0.1)
        time.sleep(0.5)
        for _ in range(5):
            press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST, 0.05)
            time.sleep(0.03)
        time.sleep(1.5)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)
        time.sleep(0.2)
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH, 0.1)
        time.sleep(0.2)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)
        time.sleep(0.3)
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH, 0.1)
        time.sleep(0.2)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)
        time.sleep(0.2)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)
        time.sleep(0.2)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, 0.1)

        # 断网
        time.sleep(delay_firewall)
        ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
        subprocess.run(
            f'netsh advfirewall firewall add rule '
            f'dir=out action=block protocol=TCP '
            f'remoteip="{ip},192.81.241.171" '
            f'name="仅阻止云存档上传"',
            shell=True
        )
        print("已断网，开始检测音频")

        # 检测音频响度
        start_time = time.time()
        while True:
            if time.time() - start_time > TIMEOUT:
                print("超时，未检测到超过阈值的音频")
                break
            stream = p.open(
                format=FORMAT,
                channels=1,
                rate=RATE,
                input=True,
                input_device_index=index,
                frames_per_buffer=CHUNK,
            )
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio_data ** 2)) * 100 + 1e-10
            print(f"\r当前 RMS: {rms:.3f}", end='')
            stream.close()
            if rms > THRESHOLD:
                print(f"\n检测到响度超过阈值: {rms:.3f} > {THRESHOLD}")
                break

        # 下云后延迟
        time.sleep(delay_loading)

        # 切线下流程
        print("切线下中…")
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.1)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, 0.1)
            time.sleep(0.1)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        gamepad.update()
        time.sleep(1.5)
        # 依据角色摇杆
        if character == 1:
            right_joystick(0, 1)
        elif character == 2:
            right_joystick(-1, 0)
        else:
            right_joystick(1, 0)
        gamepad.update()
        time.sleep(0.5)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)
        gamepad.update()
        gamepad.reset()
        gamepad.update()
        time.sleep(0.3)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.2)
        time.sleep(0.3)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, 0.2)

        # 线下到线上延迟
        time.sleep(delay_offline_online)
        r += 1
        print(f"已完成 {r} 次\n")

except KeyboardInterrupt:
    print(f"\n已完成 {r} 次，检测到用户中断，正在清理防火墙规则…")
    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True)
    print("防火墙规则已删除，程序安全退出！")
    p.terminate()