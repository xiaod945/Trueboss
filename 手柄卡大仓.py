import vgamepad as vg
import time
import subprocess

# 创建手柄实例
gamepad = vg.VDS4Gamepad()


# 辅助函数
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


# 主循环
while True:
    # 删除防火墙规则
    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True)
    time.sleep(5)

    # 按 OPTIONS 键，保持 0.5 秒
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, 0.5)
    time.sleep(2)

    # 按右方向键 5 次，每次 50 毫秒
    for _ in range(5):
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST, 0.1)
        time.sleep(1)

    time.sleep(1)

    # 按 CROSS 键，保持 0.5 秒
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.5)
    time.sleep(1)
    # 按上方向键一次，50 毫秒
    press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH, 0.1)
    time.sleep(1)
    # 按 CROSS 键，保持 0.5 秒
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.5)
    time.sleep(1)
    # 按上方向键一次
    press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH, 0.1)
    time.sleep(1)
    # 按 CROSS 键
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.5)
    time.sleep(1)
    # 按 CROSS 键，保持 0.5 秒
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.5)
    time.sleep(5)
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, 0.5)
    #添加防火墙规则的延迟
    time.sleep(10)
    # 添加防火墙规则
    subprocess.run(
        'netsh advfirewall firewall add rule dir=out action=block protocol=TCP remoteip="192.81.241.171" name="仅阻止云存档上传"',
        shell=True)

    #从线下加载到线上的延迟
    time.sleep(60)

    # 按 OPTIONS 键，保持 0.5 秒
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, 0.5)
    time.sleep(1)

    # 按右方向键 5 次，每次 50 毫秒
    for _ in range(1):
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST, 0.1)
    time.sleep(1)
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.5)
    time.sleep(1)



    # 按上方向键 3 次，每次 50 毫秒
    for _ in range(3):
        press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH, 0.1)
        time.sleep(1)

    time.sleep(1)

    # 按 CROSS 键，保持 0.5 秒
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.5)
    time.sleep(1)
    press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, 0.5)

    #从线下到线上的延迟
    time.sleep(20)


