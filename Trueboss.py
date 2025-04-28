import ctypes
import sys
from time import sleep
import pyaudio
import os
import subprocess
import win32com.client
import configparser
import shutil
import xml.etree.ElementTree as ET
import psutil
from pathlib import Path
import time
import socket
import numpy as np
import webbrowser
import logging

# 配置文件路径
CONFIG_FILE = 'Trueboss.ini'
DOCUMENT_URL = 'https://docs.qq.com/doc/DVFNMaUZQWVpFYnhh'

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 日志格式
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")

# 控制台处理器（始终启用）
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def disable_quick_edit():
    """禁用控制台快速编辑模式（防止点击窗口暂停程序）"""
    if sys.platform != 'win32':
        return
    kernel32 = ctypes.windll.kernel32
    STD_INPUT_HANDLE = -10
    try:
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        mode = ctypes.c_uint32()
        # 获取当前控制台模式
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return
        # 计算新的模式（禁用快速编辑）
        new_mode = mode.value & ~0x0040  # ENABLE_QUICK_EDIT_MODE
        # 保持扩展标志位
        if (new_mode & 0x0080) == 0:  # ENABLE_EXTENDED_FLAGS
            new_mode |= 0x0080
        if new_mode != mode.value:
            kernel32.SetConsoleMode(handle, new_mode)
    except Exception as e:
        logger.error(f"警告：禁用快速编辑模式失败（{e}），点击控制台可能导致程序暂停")

disable_quick_edit()

def create_default_config(path: str):
    """生成带注释的默认配置文件"""
    default_config_content = '''
# 日志配置
[Log]
enable = 0  # 0:不记录日志 1:启用日志记录

# 延迟相关配置（单位：秒）
[Delays]
delay_firewall = 15          # 断网检测延迟（默认15秒）
delay_loading = 30           # 下云后延迟（默认30秒）
delay_offline_online = 40    # 线上切线下延迟（默认40秒）
button_hold_delay = 0.2      # 其他按键按下持续时间（默认0.2秒）(60FPS可设置0.05)
button_release_delay = 1     # 其他松开按键后等待时间（默认1秒）(60FPS可设置0.4)
button_hold_delay2 = 0.11    # 在线下打开主菜单按到在线选项时每次按键的按下持续时间（默认0.11秒）(60FPS可设置0.02)
button_release_delay2 = 0.15 # 在线下打开主菜单按到在线选项时每次松开按键后等待时间（默认0.15秒）(60FPS可设置0.03)
button_release_delay3 = 1.5  # 按下设置键后的等待时间（默认1.5秒）(60FPS可设置0.5)

# 音频相关配置
[Audio]
format = 8                   # 2=32-bit,4=24-bit,8=16-bit  采样格式 
channels = 2                 # 声道
rate = 44100                 # 采样率
chunk = 1024                 # 每次读取的帧数
threshold = 2.5              # 响度阈值（根据实际情况调整）
audio_timeout = 120          # 超时时间（秒）

# 杂项相关配置
[Miscset]
cutnetworkset = 0               # 0:固定时间检测下云都断网 1:检测到下云才断网
endset = 0                      # 0:最后一次断网回线下 1:最后一次不断网回线下 2:90秒后关机
run_mode = 0                    # 0:首次运行禁止GTA联网 1:直接开始循环取货

# 循环次数配置
[Loop]
iterations = 100                # 总循环次数（默认100次）

# 角色选择（1=富兰克林, 2=麦克, 3=崔佛）
[Character]
choice = 1                   # 默认角色：富兰克林（序章没有富兰克林）
'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(default_config_content.strip() + '\n')
    logger.warning(f"未找到配置文件，已生成默认配置：{path}")
    logger.info("正在为您打开使用文档...")
    try:
        webbrowser.open(DOCUMENT_URL)
        input("按回车键继续...")
    except Exception as e:
        logger.error(f"打开文档失败: {e}")

    if not os.path.exists(CONFIG_FILE):
        create_default_config(CONFIG_FILE)
    config = load_config(CONFIG_FILE)

def show_document_prompt():
    print("\n" + "="*60)
    logger.info("扣 1 查看最新使用文档回车跳过")
    print("="*60)
    choice = input("请输入：").strip()
    if choice == '1':
        try:
            webbrowser.open(DOCUMENT_URL)
            input("按回车键继续...")
        except Exception as e:
            logger.error(f"打开文档失败: {e}")
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
        logger.warning(f"配置文件错误 ({e})，已重新生成默认配置")
        create_default_config(path)
        config.read(path, encoding='utf-8')
        return config

def get_config_int(config: configparser.ConfigParser, section: str, option: str, default: int) -> int:
    """安全获取整型配置"""
    try:
        return config.getint(section, option)
    except (ValueError, configparser.NoOptionError, configparser.NoSectionError):
        logger.warning(f"配置项 [{section}]->{option} 无效，使用默认值 {default}")
        return default

def get_config_float(config: configparser.ConfigParser, section: str, option: str, default: float) -> float:
    """安全获取浮点型配置"""
    try:
        return config.getfloat(section, option)
    except (ValueError, configparser.NoOptionError, configparser.NoSectionError):
        logger.warning(f"配置项 [{section}]->{option} 无效，使用默认值 {default}")
        return default

# 加载配置并初始化日志
if not os.path.exists(CONFIG_FILE):
    create_default_config(CONFIG_FILE)
config = load_config(CONFIG_FILE)
enable_log = get_config_int(config, 'Log', 'enable', 0)
if enable_log == 1:
    file_handler = logging.FileHandler("Trueboss.log", mode='w')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def check_dependencies():
    """环境依赖检测"""
    try:
        admin_check = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        admin_check = False
    if not admin_check:
        logger.warning("\n错误：请以管理员权限运行此程序！")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    try:
        import vgamepad as vg
    except Exception as e:
        logger.error("\n错误：ViGEm驱动未安装！")
        choice = input("输入 1 安装驱动，输入其他任意字符退出：")
        if choice == '1':
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            installer = os.path.join(base, "ViGEmBus_1.22.0_x64_x86_arm64.exe")
            try:
                subprocess.run([installer], check=True)
            except Exception as e:
                logger.error(f"安装失败：{e}")
                sys.exit(1)
        else:
            sys.exit()

    p = pyaudio.PyAudio()
    cable_found = any("CABLE Output" in p.get_device_info_by_index(i).get("name", "")
                      for i in range(p.get_device_count()))
    p.terminate()
    if not cable_found:
        logger.error("\n错误：未找到虚拟音频设备！")
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
                logger.error(f"虚拟声卡安装失败：{e}")
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
        logger.error(f"检测防火墙状态失败: {e}")
        return False

def check_firewall():
    """循环检测防火墙状态，直到专用和公用配置文件都开启"""
    while not is_firewall_enabled():
        input("检测到未开启防火墙，请开启防火墙后按回车键继续...")

def configure_gtav_settings():
    """
    1) 回车 — 跳过操作
    2) 输入 1 — 修改（备份并应用画质模板，只保留显卡/CPU 描述）
    3) 输入 2 — 恢复（从备份还原 settings.xml）

    修改/恢复 前，会自动检测正在运行的 GTA5.exe / GTA5_Enhanced.exe，
    以决定操作目录；如均未运行，则提示用户二选一。

    操作完成后，可选择自动结束相关进程（使新配置生效），
    或由用户手动重启游戏。
    """
    choice = input("将游戏改为最低画质，回车跳过；1: 修改画质；2: 恢复原状）：").strip()
    if choice == '':
        # print("已跳过操作。")
        return
    if choice not in ('1', '2'):
        logger.warning("无效选项，退出。")
        return

    # —— 根据运行中的进程来决定目录 —— #
    running = {p.info['name'] for p in psutil.process_iter(['name'])}
    if 'GTA5.exe' in running:
        subdir = "GTAV"
    elif 'GTA5_Enhanced.exe' in running:
        subdir = "GTAV Enhanced"
    else:
        fb = input("未检测到运行中的 GTA5，请输入 1 修改传承版，2 修改增强版：").strip()
        if fb == '1':
            subdir = "GTAV"
        elif fb == '2':
            subdir = "GTAV Enhanced"
        else:
            logger.warning("无效输入，退出。")
            return

    # 构造文件路径
    base_path     = Path.home() / "Documents" / "Rockstar Games" / subdir
    settings_file = base_path / "settings.xml"
    backup_file   = base_path / "settings_backup.xml"

    if choice == '':
        return

    if choice == '1':
        # 检查原始文件是否存在
        if not settings_file.exists():
            logger.error(f"未找到画质文件：{settings_file}")
            return

        # 备份原文件
        if backup_file.exists():
            logger.info('已有备份不再生成')
        else:
            shutil.copy2(settings_file, backup_file)
            logger.info(f"已备份原画质文件到：{backup_file}")

        # 解析原 settings.xml，保留 VideoCardDescription 和 CPUDescription 节点
        tree = ET.parse(settings_file)
        root = tree.getroot()
        video_elem = root.find('VideoCardDescription')
        cpu_elem = root.find('CPUDescription')

        # 用 etree 将节点序列化为字符串，以便后续重插入
        video_xml = ET.tostring(video_elem, encoding='unicode') if video_elem is not None else ''
        cpu_xml = ET.tostring(cpu_elem, encoding='unicode') if cpu_elem is not None else ''

        # 预设的完整模板（剔除了 xml 声明，由 write 时自动加上）
        template = """
<Settings>
  <version value="34" />
  <configSource>SMC_AUTO</configSource>
  <graphics>
    <Tessellation value="0" />
    <LodScale value="0.000000" />
    <PedLodBias value="0.000000" />
    <VehicleLodBias value="0.000000" />
    <ShadowQuality value="1" />
    <ReflectionQuality value="0" />
    <SSAOType value="0" />
    <AnisotropicFiltering value="0" />
    <ResScalingType value="1" />
    <SamplingMode value="0" />
    <TextureQuality value="0" />
    <ParticleQuality value="0" />
    <WaterQuality value="0" />
    <GrassQuality value="0" />
    <ShaderQuality value="0" />
    <Shadow_SoftShadows value="1" />
    <UltraShadows_Enabled value="false" />
    <Shadow_ParticleShadows value="false" />
    <Shadow_Distance value="1.000000" />
    <Shadow_LongShadows value="false" />
    <Shadow_SplitZStart value="0.930000" />
    <Shadow_SplitZEnd value="0.890000" />
    <Shadow_aircraftExpWeight value="0.990000" />
    <Shadow_DisableScreenSizeCheck value="false" />
    <Reflection_MipBlur value="true" />
    <AAType value="0" />
    <TAA_Quality value="1" />
    <TAA_SharpenIntensity value="1.000000" />
    <fsrQuality value="4" />
    <fsrSharpen value="0.200000" />
    <fsr3Quality value="2" />
    <fsr3Sharpen value="0.800000" />
    <dlssQuality value="2" />
    <dlssSharpen value="0.800000" />
    <Lighting_FogVolumes value="false" />
    <Shader_SSA value="false" />
    <CityDensity value="0.000000" />
    <PedVarietyMultiplier value="0.000000" />
    <VehicleVarietyMultiplier value="0.000000" />
    <VehicleHeadlightDistanceMultiplier value="1.000000" />
    <PostFX value="0" />
    <DoF value="0" />
    <HdStreamingInFlight value="false" />
    <MaxLodScale value="0.000000" />
    <MotionBlurStrength value="0.000000" />
    <VehicleDamageCacheSize value="40" />
    <VehicleDamageTextureSize value="128" />
    <PedOverlayTextureSize value="256" />
    <PedOverlayCloseUpTextureSize value="512" />
    <HDTextureSwapsPerFrame value="2048" />
    <LensFlare_HalfRes value="true" />
    <LensArtefacts_HalfRes value="true" />
    <Raytracing_Enabled value="false" />
    <Raytracing_StaticBvhEnabled value="true" />
    <Raytracing_StaticBvhRadius value="256.000000" />
    <Raytracing_StaticBvhAngularThreshold value="0.750000" />
    <Raytracing_DynamicBvhEnabled value="true" />
    <Raytracing_DynamicBvhRadius value="64.000000" />
    <Raytracing_DynamicBvhAngularThreshold value="1.500000" />
    <Raytracing_HDVehicleBvhRadius value="32.000000" />
    <Raytracing_VehicleBvhRadius value="256.000000" />
    <Raytracing_TreeBvhEnabled value="true" />
    <Raytracing_TreeBvhRadius value="256.000000" />
    <Raytracing_TreeBvhAngularThreshold value="1.000000" />
    <Raytracing_TreeBvhAnimRadius value="64.000000" />
    <Raytracing_TreeBvhAnimSSThreshold value="0.200000" />
    <Raytracing_TreeBvhAxisSSThreshold value="0.030000" />
    <Raytracing_GrassBvhEnabled value="false" />
    <Raytracing_GrassBvhRadius value="96.000000" />
    <Raytracing_GrassBvhAngularThreshold value="3.000000" />
    <Raytracing_GrassBvhDensity value="1.750000" />
    <DeferredReflectionsEnabled value="false" />
    <DeferredCubeReflectionsEnabled value="false" />
    <DeferredWaterReflectionsEnabled value="false" />
    <DeferredMirrorReflectionsEnabled value="false" />
    <DeferredCubeReflectionsComputeEnabled value="false" />
    <DeferredWaterReflectionsComputeEnabled value="false" />
    <DeferredMirrorReflectionsComputeEnabled value="false" />
    <RTShadows_Enabled value="false" />
    <RTShadows_Quality value="0" />
    <RTAmbientOcclusion_Enabled value="false" />
    <RTAmbientOcclusion_Quality value="0" />
    <RTReflection_Enabled value="false" />
    <RTReflection_Quality value="0" />
    <RTIndirectDiffuse_Enabled value="false" />
    <RTIndirectDiffuse_Quality value="0" />
    <RTCharacterShadow_Enabled value="false" />
    <RTApplyAOToFillLights value="false" />
    <RTIndirectDiffuse_SecondBounce_Enabled value="false" />
    <PlayerHeadlightShadowsQuality value="0" />
    <NetPlayerHeadlightsCastShadows value="false" />
    <AllVehicleHeadlightShadowsQuality value="0" />
  </graphics>
  <system>
    <numBytesPerReplayBlock value="9000000" />
    <numReplayBlocks value="30" />
    <maxSizeOfStreamingReplay value="1024" />
    <maxFileStoreSize value="65536" />
    <forceSingleStepPhysics value="false" />
  </system>
  <audio>
    <Audio3d value="false" />
  </audio>
  <video>
    <AdapterIndex value="0" />
    <OutputIndex value="0" />
    <ScreenWidth value="1024" />
    <ScreenHeight value="768" />
    <RefreshRate value="30" />
    <Windowed value="1" />
    <VSync value="0" />
    <PauseOnFocusLoss value="0" />
    <AspectRatio value="0" />
    <ReflexMode value="0" />
    <FrameLimit value="30" />
  </video>
  <VideoCardDescription></VideoCardDescription>
  <CPUDescription></CPUDescription>
  <Presets>
    <PresetLevel value="0" />
    <BVHQuality value="0" />
    <RTShadowQuality value="0" />
    <RTReflectionQuality value="0" />
    <RTDynamicQuality value="0" />
    <RTStaticQuality value="0" />
    <RTVehicleQuality value="0" />
    <RTTreeQuality value="0" />
    <RTGrassQuality value="0" />
    <RTAOQuality value="0" />
    <RTGIQuality value="0" />
    <LightingQuality value="0" />
    <PostFXQuality value="0" />
    <ReflectionQuality value="0" />
  </Presets>
</Settings>
"""
        # 加载模板
        tmpl_root = ET.fromstring(template)

        # 将原始的描述节点插入到模板中
        parent = tmpl_root
        if video_xml:
            new_video = ET.fromstring(video_xml)
            # 移除空的占位节点
            old = tmpl_root.find('VideoCardDescription')
            if old is not None:
                parent.remove(old)
            parent.append(new_video)
        if cpu_xml:
            new_cpu = ET.fromstring(cpu_xml)
            old = tmpl_root.find('CPUDescription')
            if old is not None:
                parent.remove(old)
            parent.append(new_cpu)

        # 写回 settings.xml（包含 XML 声明）
        new_tree = ET.ElementTree(tmpl_root)
        new_tree.write(settings_file, encoding='UTF-8', xml_declaration=True)
        logger.info("画质选项修改成功,重启游戏生效~")

    elif choice == '2':
        # 恢复
        if not backup_file.exists():
            logger.error(f"未找到备份文件：{backup_file}")
            return
        # 覆盖还原
        shutil.copy2(backup_file, settings_file)
        # 删除备份文件
        try:
            backup_file.unlink()
            logger.info("已从备份还原并删除了备份文件。")
        except Exception as e:
            logger.error(f"画质文件已还原，但删除备份文件时出错：{e}")

    else:
        logger.warning("无效选项，请输入 1 或 2。")

    running = {p.info['name'] for p in psutil.process_iter(['name'])}
    if 'GTA5.exe' in running:
        kill_prompt = f"输入 1 关闭游戏，回车跳过"
    elif 'GTA5_Enhanced.exe' in running:
        kill_prompt = f"输入 1 关闭游戏，回车跳过"
    else:
        return

    kill_choice = input(kill_prompt).strip()
    if kill_choice == '1':
        target_names = {
                "GTA5.exe", "GTA5_Enhanced.exe", "SocialClubHelper.exe",
            "Launcher.exe", "RockstarService.exe", "RockstarErrorHandler.exe", "PlayGTAV.exe"
        }
        for proc in psutil.process_iter(['name']):
            name = proc.info.get('name')
            if name in target_names:
                try:
                    proc.terminate()
                    logger.info(f"已终止进程：{name} (PID {proc.pid})")
                except Exception as e:
                    logger.error(f"无法终止 {name} (PID {proc.pid})：{e}")
        input('请按任意键退出程序')
        sys.exit(0)
    else:
        logger.info("请手动重启游戏以使设置生效。")

# 加载配置
if not os.path.exists(CONFIG_FILE):
    create_default_config(CONFIG_FILE)
config = load_config(CONFIG_FILE)

# 加载配置参数
delay_firewall = get_config_int(config, 'Delays', 'delay_firewall', 15)
delay_loading = get_config_int(config, 'Delays', 'delay_loading', 30)
delay_offline_online = get_config_int(config, 'Delays', 'delay_offline_online', 40)
button_hold_delay = get_config_float(config, 'Delays', 'button_hold_delay', 0.2)
button_release_delay = get_config_float(config, 'Delays', 'button_release_delay', 1)
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
# enable = get_config_int(config, 'Log', 'enable', 0)

# 前置检测
check_dependencies()
show_document_prompt()
check_firewall()
configure_gtav_settings()

if run_mode not in (0, 1):
    logger.warning("运行模式参数无效，已重置为默认值0")
    run_mode = 0

# 验证角色选择
if character not in (1, 2, 3):
    logger.warning("角色选择超出范围，已重置为默认（富兰克林）")
    character = 1

# 验证断网选择
if cutnetworkset not in (0, 1):
    logger.warning("断网选择超出范围，已重置为默认（0:固定时间检测下云都断网）")
    cutnetworkset = 0

print(f"""你可以修改Trueboss.ini提升效率或者增强稳定性，修改后重启软件生效
运行参数：
  0. 断网方式      = {cutnetworkset}   0:固定时间检测下云都断网 1:检测到下云才断网
  1. 断网/检测下云延迟     = {delay_firewall} 秒
  2. 下云后延迟    = {delay_loading} 秒
  3. 下线延迟 = {delay_offline_online} 秒
  4. 在线下打开主菜单按到在线选项时每次按键的按下持续时间  = {button_hold_delay2} 秒
  5. 在线下打开主菜单按到在线选项时每次松开按键后等待时间  = {button_release_delay2} 秒
  4. 按键2保持时间 = {button_hold_delay} 秒
  5. 松开2等待时间 = {button_release_delay} 秒
  6. 按键3等待时间 = {button_release_delay3} 秒
  7. 循环次数     = {t}
  8. 当前角色     = {'富兰克林' if character == 1 else '麦克' if character == 2 else '崔佛'}
  9. 音频检测阈值 = {threshold}             
  10.音频检测超时 = {audio_timeout}  秒
  11.结束方式 = {endset}   0:断网回线下 1:不断网回线下 2:九十秒后关机
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
import vgamepad as vg
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
            logger.info("最后一次保存不断网")
    # elif endset == 2:
    #     if r < t:
    #         ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
    #         subprocess.run(
    #             f'netsh advfirewall firewall add rule '
    #             f'dir=out action=block protocol=TCP '
    #             f'remoteip="{ip},192.81.241.171" '
    #             f'name="仅阻止云存档上传"',
    #             shell=True, stdout=subprocess.DEVNULL
    #         )
    #     else:
    #         subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
    #                        stdout=subprocess.DEVNULL)
    #         input("GTA5手柄大仓任务完成，按任意键退出")

    elif endset == 2:
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
            shutdown_computer()
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
                logger.info(f"找到进程：{proc.info['name']} 路径：{proc.info['exe']}")
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
    logger.info(f"运行时间：{hours:02}:{minutes:02}:{seconds:02}\n")

def shutdown_computer():
    """安全关闭计算机"""
    logger.info("\n准备关闭计算机...")
    try:
        if sys.platform == 'win32':
            os.system('shutdown /s /t 90 /c "GTA5手柄大仓程序已完成任务，计算机将在90秒后关闭"')
        else:
            os.system('shutdown -h now')
        logger.info("关机命令已发送，请确保所有工作已保存！")
    except Exception as e:
        logger.error(f"发送关机命令失败: {e}")

def log_print(message):
    # 获取当前时间戳
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 格式化输出，带有时间戳和消息
    print(f"\r{timestamp} - PRINT - {message}", end='')

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
            logger.warning("超时！未检测到超过阈值的音频")
            break
        data = stream.read(chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16
                                   ).astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_data ** 2)) * 100 + 1e-10
        log_print(f"当前 RMS: {rms:.3f}")
        if rms > threshold:
            print()
            logger.info(f"检测到响度超过阈值: {rms:.3f} > {threshold}")
            cutnetwork()
            logger.info("已断网！检测到下云音频")
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
            logger.warning("超时！未检测到超过阈值的音频")
            break
        data = stream.read(chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16
                                   ).astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_data ** 2)) * 100 + 1e-10
        log_print(f"当前 RMS: {rms:.3f}")
        if rms > threshold:
            print()
            logger.info(f"检测到响度超过阈值: {rms:.3f} > {threshold}")
            exe_path = find_gta5_process()
            if not exe_path:
                logger.warning("错误！未找到运行中的GTA5！")
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
            logger.info("已断开GTA5进程网络防止上传！")
            break
    stream.close()

# 主逻辑
r = 0
start_time = time.time()
try:
    if run_mode == 0:
        # 新增初始化操作
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        logger.info("正在执行初始化流程...")
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_hold_delay)
            time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, button_hold_delay)
        time.sleep(button_release_delay3)
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
        time.sleep(button_release_delay3)
        logger.info("试图切线下角色")
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
        time.sleep(button_release_delay)
        gamepad.reset()
        # gamepad.update()
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(delay_loading)
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        for _ in range(2):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT, button_release_delay)
            time.sleep(button_release_delay3)
            time.sleep(button_release_delay3)
        sleep(button_release_delay3)

        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        sleep(delay_loading)
        logger.info("初始化操作完成，开始主循环...")

    for _ in range(t):
        r += 1
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_hold_delay)
            time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, button_hold_delay)
        time.sleep(button_release_delay3)
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
            logger.info("已断网！检测到固定延时")
        listening()
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(delay_loading)
        logger.info("发呆等电话…")
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_release_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_release_delay)
            time.sleep(button_release_delay)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        gamepad.update()
        time.sleep(button_release_delay3)
        logger.info("切线下中…")
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
        time.sleep(button_release_delay)
        gamepad.reset()
        # gamepad.update()
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SQUARE, button_hold_delay)
        time.sleep(delay_offline_online)
        logger.info(f"已完成 {r} 次 \n")
        getRuntime()
except KeyboardInterrupt:
    logger.info(f"\n已完成 {r} 次，检测到用户中断，正在清理防火墙规则…")
    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                   stdout=subprocess.DEVNULL)
    logger.info("防火墙规则已删除，程序安全退出！")
    if p.Stream.is_active == True:
        p.Stream.close()
    p.terminate()