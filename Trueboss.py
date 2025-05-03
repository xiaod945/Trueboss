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
import winreg
from datetime import datetime

# pyinstaller --onefile  --add-binary "C:\Users\1\AppData\Local\Programs\Python\Python312\Lib\site-packages\vgamepad\win\vigem\client\x64\ViGEmClient.dll;."  --add-data "ViGEmBus_1.22.0_x64_x86_arm64.exe;."  --add-data "VBCABLE;VBCABLE"  --add-data "cloudsavedata.dat;."  --add-data "pc_settings.bin;." --add-data "SoundVolumeView.exe;." --icon=app.ico  Trueboss.py


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
delay_firewall = 20              # 固定断网延迟（默认20秒）
delay_loading = 30               # 下云后延迟（默认30秒）
delay_offline_online = 40        # 线上切线下延迟（默认40秒）
button_hold_delay = 0.2          # 其他按键按下持续时间(60FPS可设置0.05)
button_release_delay = 1         # 其他松开按键后等待时间(60FPS可设置0.4)
button_hold_delay2 = 0.11        # 在线下打开主菜单按到在线选项时每次按键的按下持续时间(60FPS可设置0.03)
button_release_delay2 = 0.15     # 在线下打开主菜单按到在线选项时每次松开按键后等待时间(60FPS可设置0.04)
button_release_delay3 = 1.5      # 按下设置键后的等待时间(60FPS可设置0.5)

# 音频相关配置
[Audio]
format = 8                   # 2=32-bit,4=24-bit,8=16-bit  采样格式 
channels = 2                 # 声道
rate = 44100                 # 采样率
chunk = 1024                 # 每次读取的帧数
threshold = 2.5              # 响度阈值
audio_timeout = 120          # 超时时间（秒）

# 杂项相关配置
[Miscset]
cutnetworkset = 0               # 0:固定时间检测下云都断网 1:检测到下云才断网
endset = 0                      # 0:最后一次断网回线下 1:最后一次不断网回线下 2:九十秒后关机 3:切换角色再来一轮结束后联网关机(必须使用战局锁)
run_mode = 0                    # 0:首次运行禁止GTA联网 1:直接开始循环取货

# 循环次数配置
[Loop]
iterations = 100                # 总循环次数（默认100次）

# 角色选择（1=富兰克林, 2=麦克, 3=崔佛）
[Character]
choice = 2                      # 默认角色：麦克(序章没有富兰克林)
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
    print("\n" + "=" * 60)
    logger.info("扣 1 查看最新使用文档回车跳过")
    print("=" * 60)
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


def get_install_dir(version):
    """根据游戏版本从注册表获取安装目录"""
    if version == 'GTA V':
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Rockstar Games\Grand Theft Auto V"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Rockstar Games\Grand Theft Auto V"),
        ]
    elif version == 'GTAV Enhanced':
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Rockstar Games\GTA V Enhanced"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Rockstar Games\GTAV Enhanced"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Rockstar Games\GTA V Enhanced"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Rockstar Games\GTAV Enhanced"),
        ]
    else:
        raise ValueError("Invalid version")

    value_names = ["InstallFolder", "InstallFolderSteam", "InstallFolderEpic", "InstallDir"]

    for hive, subkey in reg_paths:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                for value_name in value_names:
                    try:
                        value, _ = winreg.QueryValueEx(key, value_name)
                        if value:
                            return Path(value)
                    except FileNotFoundError:
                        continue
        except FileNotFoundError:
            continue
    return None


def configure_gtav_settings():
    """
    功能说明：
    1) 回车 — 跳过操作
    2) 输入 1 — 修改（生成 startup.meta，备份并应用画质模板，备份并处理 Profiles 文件夹）
    3) 输入 2 — 恢复（删除 startup.meta，从备份还原 settings.xml 和 Profiles 文件夹）

    修改/恢复前，会自动检测正在运行的 GTA5.exe / GTA5_Enhanced.exe，以决定操作目录；
    如均未运行，则提示用户二选一。

    操作完成后，可选择自动结束相关进程（使新配置生效），或由用户手动重启游戏。
    """
    choice = input("是否将游戏改为最低画质生成随机战局锁备份并删除存档，回车跳过；1: 修改画质；2: 恢复原状）：").strip()
    if choice == '':
        return
    if choice not in ('1', '2'):
        logger.warning("无效选项，退出。")
        return

    # —— 根据运行中的进程或用户输入决定目录 —— #
    running = {p.info['name'] for p in psutil.process_iter(['name'])}
    if 'GTA5.exe' in running:
        subdir = "GTA V"
        exe_name = 'GTA5.exe'
    elif 'GTA5_Enhanced.exe' in running:
        subdir = "GTAV Enhanced"
        exe_name = 'GTA5_Enhanced.exe'
    else:
        fb = input("未检测到运行中的 GTA5，请输入 1 修改传承版，2 修改增强版：").strip()
        if fb == '1':
            subdir = "GTA V"
            exe_name = 'GTA5.exe'
        elif fb == '2':
            subdir = "GTAV Enhanced"
            exe_name = 'GTA5_Enhanced.exe'
        else:
            logger.warning("无效输入，退出。")
            return

    # 获取游戏安装目录
    if exe_name in running:
        for proc in psutil.process_iter(['name', 'exe']):
            if proc.info['name'] == exe_name:
                install_dir = Path(proc.info['exe']).parent
                break
    else:
        install_dir = get_install_dir(subdir)
        if install_dir is None:
            logger.error("无法从注册表获取游戏安装目录。")
            return

    # 构造路径
    data_dir = install_dir / 'x64' / 'data'
    startup_file = data_dir / 'startup.meta'
    base_path = Path.home() / "Documents" / "Rockstar Games" / subdir
    profiles_dir = base_path / "Profiles"
    profiles_backup = base_path / "Profiles_backup"
    settings_file = base_path / "settings.xml"
    backup_file = base_path / "settings_backup.xml"

    if subdir == "GTA V":
        template = """<Settings>
  <version value="27" />
  <configSource>SMC_AUTO</configSource>
  <graphics>
    <Tessellation value="0" />
    <LodScale value="0.000000" />
    <PedLodBias value="0.200000" />
    <VehicleLodBias value="0.000000" />
    <ShadowQuality value="1" />
    <ReflectionQuality value="0" />
    <ReflectionMSAA value="0" />
    <SSAO value="1" />
    <AnisotropicFiltering value="0" />
    <MSAA value="0" />
    <MSAAFragments value="0" />
    <MSAAQuality value="0" />
    <SamplingMode value="1" />
    <TextureQuality value="0" />
    <ParticleQuality value="0" />
    <WaterQuality value="0" />
    <GrassQuality value="0" />
    <ShaderQuality value="0" />
    <Shadow_SoftShadows value="0" />
    <UltraShadows_Enabled value="false" />
    <Shadow_ParticleShadows value="true" />
    <Shadow_Distance value="1.000000" />
    <Shadow_LongShadows value="false" />
    <Shadow_SplitZStart value="0.930000" />
    <Shadow_SplitZEnd value="0.890000" />
    <Shadow_aircraftExpWeight value="0.990000" />
    <Shadow_DisableScreenSizeCheck value="false" />
    <Reflection_MipBlur value="true" />
    <FXAA_Enabled value="false" />
    <TXAA_Enabled value="false" />
    <Lighting_FogVolumes value="true" />
    <Shader_SSA value="false" />
    <DX_Version value="0" />
    <CityDensity value="0.000000" />
    <PedVarietyMultiplier value="0.000000" />
    <VehicleVarietyMultiplier value="0.000000" />
    <PostFX value="0" />
    <DoF value="false" />
    <HdStreamingInFlight value="false" />
    <MaxLodScale value="0.000000" />
    <MotionBlurStrength value="0.000000" />
  </graphics>
  <system>
    <numBytesPerReplayBlock value="9000000" />
    <numReplayBlocks value="30" />
    <maxSizeOfStreamingReplay value="1024" />
    <maxFileStoreSize value="65536" />
  </system>
  <audio>
    <Audio3d value="false" />
  </audio>
  <video>
    <AdapterIndex value="0" />
    <OutputIndex value="0" />
    <ScreenWidth value="800" />
    <ScreenHeight value="600" />
    <RefreshRate value="59" />
    <Windowed value="1" />
    <VSync value="1" />
    <Stereo value="0" />
    <Convergence value="0.100000" />
    <Separation value="1.000000" />
    <PauseOnFocusLoss value="0" />
    <AspectRatio value="0" />
  </video>
  <VideoCardDescription></VideoCardDescription>
</Settings>"""

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!--l1x1c4o5o17477111111-->
<CDataFileMgr__ContentsOfDataFileXml>
	<disabledFiles />
	<includedXmlFiles itemType="CDataFileMgr__DataFileArray" />
	<includedDataFiles />
	<dataFiles itemType="CDataFileMgr__DataFile">
		<Item>
			<filename>platform:/data/cdimages/scaleform_platform_pc.rpf</filename>
			<fileType>RPF_FILE</fileType>
		</Item>
		<Item>
		<filename>platform:/data/cdimages/scaleform_frontend.rpf</filename>
			<fileType>RPF_FILE_PRE_INSTALL</fileType>
		</Item>
	</dataFiles>
	<contentChangeSets itemType="CDataFileMgr__ContentChangeSet" />
	<dataFiles itemType="CDataFileMgr__DataFile" />
	<patchFiles />
</CDataFileMgr__ContentsOfDataFileXml>"""
    else:
        template = """<Settings>
  <version value="34" />
  <configSource>SMC_AUTO</configSource>
  <graphics>
    <Tessellation value="0" />
    <LodScale value="0.000000" />
    <PedLodBias value="0.200000" />
    <VehicleLodBias value="0.150000" />
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
    <Shadow_SoftShadows value="0" />
    <UltraShadows_Enabled value="false" />
    <Shadow_ParticleShadows value="true" />
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
    <fsrQuality value="2" />
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
    <VehicleDamageCacheSize value="80" />
    <VehicleDamageTextureSize value="128" />
    <PedOverlayTextureSize value="512" />
    <PedOverlayCloseUpTextureSize value="1024" />
    <HDTextureSwapsPerFrame value="100" />
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
    <RefreshRate value="60" />
    <Windowed value="1" />
    <VSync value="0" />
    <PauseOnFocusLoss value="0" />
    <AspectRatio value="0" />
    <ReflexMode value="0" />
    <FrameLimit value="60" />
  </video>
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
</Settings>"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<CDataFileMgr__ContentsOfDataFileXml>
	<disabledFiles />
	<includedXmlFiles itemType="CDataFileMgr__DataFileArray" />
	<includedDataFiles />
	<dataFiles itemType="CDataFileMgr__DataFile">
		<Item>
			<filename>platform:/data/cdimages/scaleform_platform_pc.rpf</filename>
			<fileType>RPF_FILE</fileType>
		</Item>
		<Item>
		<filename>platform:/data/cdimages/scaleform_frontend.rpf</filename>
			<fileType>RPF_FILE_PRE_INSTALL</fileType>
		</Item>
		<Item>
		<filename>platform:/data/cdimages/scaleform_frontend_gen9.rpf</filename>
			<fileType>RPF_FILE_PRE_INSTALL</fileType>
		</Item>
		<Item>
		<filename>platform:/levels/gta5/script/script.rpf</filename>
			<fileType>RPF_FILE_PRE_INSTALL</fileType>
		</Item>
	</dataFiles>
	<contentChangeSets itemType="CDataFileMgr__ContentChangeSet" />
	<dataFiles itemType="CDataFileMgr__DataFile" />
	<patchFiles />
</CDataFileMgr__ContentsOfDataFileXml>
GTA5增强版战局锁
k7Ysh5A_41制作   转载请注明出处谢谢
https://space.bilibili.com/175659130
https://steamcommunity.com/groups/JobTP"""

    if choice == '1':
        # 处理 startup.meta 文件
        if startup_file.exists():
            logger.info("检测到已存在战局锁，不再生成。")
        else:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            xml_content += f"\n<!--{current_time}-->"
            startup_file.parent.mkdir(parents=True, exist_ok=True)
            with open(startup_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            logger.info("随机战局锁已生成。")

        # 处理 Profiles 文件夹
        if profiles_dir.exists():
            # 如果 Profiles_backup 已存在，不重复备份
            if profiles_backup.exists():
                logger.info("Profiles_backup已存在，不再备份。")
            else:
                # 备份 Profiles 文件夹到 Profiles_backup 并删除原文件夹
                shutil.move(profiles_dir, profiles_backup)
                profiles_dir.mkdir(parents=True, exist_ok=True)
                for subfolder in profiles_backup.iterdir():
                    if subfolder.is_dir():
                        # 在新的 Profiles 文件夹中创建同名子文件夹
                        new_subfolder = profiles_dir / subfolder.name
                        new_subfolder.mkdir(parents=True, exist_ok=True)
                        # 构造源路径和目标路径
                        src_cfg = subfolder / "cfg.dat"
                        dst_cfg = new_subfolder / "cfg.dat"

                        # 复制 cfg.dat 文件
                        if src_cfg.exists():
                            shutil.copy2(src_cfg, dst_cfg)
                            # print(f"已将 {src_cfg} 复制到 {dst_cfg}。")
                        else:
                            logger.warning(f"警告：{src_cfg} 不存在。")
                    else:
                        logger.warning(f"{profiles_backup} 不存在，无需处理。")

                logger.info("已备份 Profiles 文件夹到 Profiles_backup 并删除原文件夹。")

            # 创建新的 Profiles 文件夹
            profiles_dir.mkdir(parents=True, exist_ok=True)

            # 遍历 Profiles_backup 中的子文件夹
            for subfolder in profiles_backup.iterdir():
                if subfolder.is_dir():
                    # 在新的 Profiles 文件夹中创建同名子文件夹
                    new_subfolder = profiles_dir / subfolder.name
                    new_subfolder.mkdir(parents=True, exist_ok=True)

                    # 复制文件到新子文件夹
                    for file_name in ['pc_settings.bin', 'cloudsavedata.dat']:
                        src_file = Path(__file__).parent / file_name
                        if src_file.exists():
                            shutil.copy2(src_file, new_subfolder / file_name)
                            # print(f"已将 {file_name} 复制到 {new_subfolder}。")
                        else:
                            logger.error(f"警告：文件 {file_name} 不存在于程序目录。")
        else:
            logger.warning("设置文件夹不存在，无需备份。")
        # 备份并修改 settings.xml
        if not settings_file.exists():
            logger.error(f"未找到画质文件：{settings_file}")
            return
        if backup_file.exists():
            logger.info('已有备份不再生成')
        else:
            shutil.copy2(settings_file, backup_file)
            logger.info(f"已备份原画质文件到：{backup_file}")

        # 解析并修改 settings.xml（沿用原逻辑）
        tree = ET.parse(settings_file)
        root = tree.getroot()
        video_elem = root.find('VideoCardDescription')
        cpu_elem = root.find('CPUDescription')
        video_xml = ET.tostring(video_elem, encoding='unicode') if video_elem is not None else ''
        cpu_xml = ET.tostring(cpu_elem, encoding='unicode') if cpu_elem is not None else ''

        tmpl_root = ET.fromstring(template)
        parent = tmpl_root
        if video_xml:
            new_video = ET.fromstring(video_xml)
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

        new_tree = ET.ElementTree(tmpl_root)
        new_tree.write(settings_file, encoding='UTF-8', xml_declaration=True)
        logger.info("画质选项修改成功，重启游戏生效~")

    elif choice == '2':
        # 删除 startup.meta 文件
        if startup_file.exists():
            startup_file.unlink()
            logger.info("已删除生成的 startup.meta 文件。")
        else:
            logger.info("startup.meta 文件不存在，无需删除。")

        # 还原 settings.xml
        if not backup_file.exists():
            logger.error(f"未找到备份文件：{backup_file}")
            return
        shutil.copy2(backup_file, settings_file)
        backup_file.unlink()
        logger.info("已从备份还原 settings.xml 并删除了备份文件。")

        # 还原 Profiles 文件夹
        if profiles_backup.exists():
            if profiles_dir.exists():
                shutil.rmtree(profiles_dir)
            shutil.move(profiles_backup, profiles_dir)
            logger.info("已从 Profiles_backup 还原 Profiles 文件夹。")
        else:
            logger.info("Profiles_backup 不存在，无需还原。")

    # 提示关闭游戏进程
    running = {p.info['name'] for p in psutil.process_iter(['name'])}
    if exe_name in running:
        print('')
        kill_prompt = "输入 1 关闭游戏，回车跳过"
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
                        print('')
                        logger.info(f"已终止进程：{name} (PID {proc.pid})")
                    except Exception as e:
                        logger.error(f"无法终止 {name} (PID {proc.pid})：{e}")
            input('请按任意键退出程序')
            sys.exit(0)
        else:
            logger.info("请手动重启游戏使设置生效。")


# 加载配置
if not os.path.exists(CONFIG_FILE):
    create_default_config(CONFIG_FILE)
config = load_config(CONFIG_FILE)

# 加载配置参数
delay_firewall = get_config_int(config, 'Delays', 'delay_firewall', 20)
delay_loading = get_config_int(config, 'Delays', 'delay_loading', 30)
delay_offline_online = get_config_int(config, 'Delays', 'delay_offline_online', 40)
button_hold_delay = get_config_float(config, 'Delays', 'button_hold_delay', 0.2)
button_release_delay = get_config_float(config, 'Delays', 'button_release_delay', 1)
button_hold_delay2 = get_config_float(config, 'Delays', 'button_hold_delay2', 0.11)
button_release_delay2 = get_config_float(config, 'Delays', 'button_release_delay2', 0.15)
button_release_delay3 = get_config_float(config, 'Delays', 'button_release_delay3', 1.5)
t = get_config_int(config, 'Loop', 'iterations', 100)
t2 = get_config_int(config, 'Loop', 'iterations', 100)
character = get_config_int(config, 'Character', 'choice', 2)
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
    logger.warning("角色选择超出范围，已重置为默认（麦克）")
    character = 2

# 验证断网选择
if cutnetworkset not in (0, 1):
    logger.warning("断网选择超出范围，已重置为默认（0:固定时间检测下云都断网）")
    cutnetworkset = 0

print(f"""你可以修改Trueboss.ini提升效率或者增强稳定性，修改后重启软件生效
运行参数：
  0. 断网方式      = {cutnetworkset}      0:固定时间检测下云都断网 1:检测到下云才断网
  1. 固定断网延迟     = {delay_firewall} 秒
  2. 下云后延迟    = {delay_loading} 秒
  3. 线上切线下延迟 = {delay_offline_online} 秒
  4. 在线下打开主菜单按到在线选项时每次按键的按下持续时间  = {button_hold_delay2} 秒
  5. 在线下打开主菜单按到在线选项时每次松开按键后等待时间  = {button_release_delay2} 秒
  4. 按键2保持时间 = {button_hold_delay} 秒
  5. 松开2等待时间 = {button_release_delay} 秒
  6. 按键3等待时间 = {button_release_delay3} 秒
  7. 循环次数     = {t}
  8. 当前角色     = {'富兰克林' if character == 1 else '麦克' if character == 2 else '崔佛'}
  9. 音频检测阈值 = {threshold}             
  10.音频检测超时 = {audio_timeout}  秒
  11.结束方式 = {endset}   0:断网回线下 1:联网回线下 2:九十秒后关机 3:切换角色重新循环一轮联网关机
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

def _is_any_gta_running():
    """
    检查 GTA5_Enhanced.exe 或 GTA5.exe 是否在运行。
    :return: 运行的进程名列表（可能包含一个或两个），如果都未运行，则返回空列表。
    """
    gta_names = ["GTA5_Enhanced.exe", "GTA5.exe"]
    running = []
    for proc in psutil.process_iter(attrs=["name"]):
        name = proc.info["name"]
        if name in gta_names:
            if name not in running:
                running.append(name)
    return running

def set_gta_output_device(device_name: str):
    """
    将所有正在运行的 GTA5 相关进程的音频输出设备设置为 device_name。
    如果未检测到进程运行，则不做任何操作。

    :param device_name: 输出设备名称，例如 "CABLE Input"
    """
    running = _is_any_gta_running()
    if not running:
        logger.error("错误！未找到运行中的GTA5！")
        input("请确保游戏正在运行，按回车键退出程序...")
        sys.exit(1)

    svv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SoundVolumeView.exe")
    for proc_name in running:
        cmd = [
            svv,
            "/SetAppDefault",
            device_name,
            "all",
            proc_name
        ]
        subprocess.run(
            cmd,
            shell=True, stdout=subprocess.DEVNULL
        )
    logger.info(f"已将 {', '.join(running)} 的音频输出切换到 {device_name}。")

def reset_gta_to_system_default():
    """
    将所有正在运行的 GTA5 相关进程的音频输出恢复为系统默认渲染设备。
    如果未检测到进程运行，则不做任何操作。
    """
    running = _is_any_gta_running()
    if not running:
        logger.error("未找到运行中的GTA5，跳过恢复默认设备。")
        return

    svv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SoundVolumeView.exe")
    for proc_name in running:
        cmd = [
            svv,
            "/SetAppDefault",
            "DefaultRenderDevice",
            "all",
            proc_name
        ]
        subprocess.run(
            cmd,
            shell=True, stdout=subprocess.DEVNULL
        )
    logger.info(f"已将 {', '.join(running)} 的音频输出恢复为系统默认设备。")


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
    global t
    if endset == 1:
        if r < t:
            if not r == t:
                ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
                subprocess.run(
                    f'netsh advfirewall firewall add rule '
                    f'dir=out action=block protocol=TCP '
                    f'remoteip="{ip},192.81.241.171" '
                    f'name="仅阻止云存档上传"',
                    shell=True, stdout=subprocess.DEVNULL
                )
                logger.info("已断网！检测到下云音频")
        else:
            logger.info("最后一次保存不断网")
            reset_gta_to_system_default()


    elif endset == 2:
        if r < t:
            if not r == t:
                ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
                subprocess.run(
                    f'netsh advfirewall firewall add rule '
                    f'dir=out action=block protocol=TCP '
                    f'remoteip="{ip},192.81.241.171" '
                    f'name="仅阻止云存档上传"',
                    shell=True, stdout=subprocess.DEVNULL
                )
                logger.info("已断网！检测到下云音频")
        else:
            reset_gta_to_system_default()
            shutdown_computer()

    elif endset == 3:
        if r < t:
            if not r == t:
                ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
                subprocess.run(
                    f'netsh advfirewall firewall add rule '
                    f'dir=out action=block protocol=TCP '
                    f'remoteip="{ip},192.81.241.171" '
                    f'name="仅阻止云存档上传"',
                    shell=True, stdout=subprocess.DEVNULL
                )
                logger.info("已断网！检测到下云音频")
        else:
            logger.info('开始切换角色任务')
            logger.info(f"开始等delay_loading {delay_loading}秒")
            time.sleep(delay_loading)
            logger.info('执行进入管理角色操作')
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, button_release_delay3)
            time.sleep(button_release_delay3)
            press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST, button_hold_delay2)
            time.sleep(button_release_delay2)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_release_delay3)
            time.sleep(button_release_delay3)
            for _ in range(7):
                press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH, button_hold_delay)
                time.sleep(button_release_delay3)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            time.sleep(button_release_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            logger.info(f"开始等delay_offline_online {delay_offline_online}秒")
            time.sleep(delay_offline_online)
            logger.info(f"开始等delay_firewall {delay_firewall}秒")
            time.sleep(delay_firewall)
            logger.info('执行切换角色操作')
            press_dpad(gamepad, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST, button_hold_delay2)
            time.sleep(button_release_delay3)
            time.sleep(button_release_delay3)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            # time.sleep(button_release_delay)
            # subprocess.run(
            #     'netsh advfirewall firewall add rule '
            #     'dir=out action=block protocol=TCP localport=6672 '
            #     'name="仅阻止云存档上传"',
            #     shell=True,
            #     stdout=subprocess.DEVNULL
            # )
            # subprocess.run(
            #     'netsh advfirewall firewall add rule '
            #     'dir=out action=block protocol=UDP localport=6672 '
            #     'name="仅阻止云存档上传"',
            #     shell=True,
            #     stdout=subprocess.DEVNULL
            # )
            # subprocess.run(
            #     'netsh advfirewall firewall add rule '
            #     'dir=in action=block protocol=TCP localport=6672 '
            #     'name="仅阻止云存档上传"',
            #     shell=True,
            #     stdout=subprocess.DEVNULL
            # )
            # subprocess.run(
            #     'netsh advfirewall firewall add rule '
            #     'dir=in action=block protocol=UDP localport=6672 '
            #     'name="仅阻止云存档上传"',
            #     shell=True,
            #     stdout=subprocess.DEVNULL
            # )
            logger.info(f"开始等delay_firewall {delay_firewall}秒")
            time.sleep(delay_firewall)
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
                    ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
                    subprocess.run(
                        f'netsh advfirewall firewall add rule '
                        f'dir=out action=block protocol=TCP '
                        f'remoteip="{ip},192.81.241.171" '
                        f'name="仅阻止云存档上传"',
                        shell=True, stdout=subprocess.DEVNULL
                    )
                    logger.info("已断网！检测到下云音频")
                    break
            stream.close()
            logger.info(f"开始等delay_offline_online {delay_offline_online}秒")
            sleep(delay_offline_online)

            if r == t:
                if t2 == t:
                    t *= 2
                else:
                    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                                   stdout=subprocess.DEVNULL)
                    logger.info("防火墙规则已删除，程序安全退出！")
                    reset_gta_to_system_default()
                    shutdown_computer()
    else:
        if r < t:
            if not r == t:
                ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
                subprocess.run(
                    f'netsh advfirewall firewall add rule '
                    f'dir=out action=block protocol=TCP '
                    f'remoteip="{ip},192.81.241.171" '
                    f'name="仅阻止云存档上传"',
                    shell=True, stdout=subprocess.DEVNULL
                )
                logger.info("已断网！检测到下云音频")
        else:
            logger.info("已断网！检测到最后一轮")
            reset_gta_to_system_default()


def cutnetwork2():
    if endset == 1:
        if r < t:
            if not r == t:
                ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
                subprocess.run(
                    f'netsh advfirewall firewall add rule '
                    f'dir=out action=block protocol=TCP '
                    f'remoteip="{ip},192.81.241.171" '
                    f'name="仅阻止云存档上传"',
                    shell=True, stdout=subprocess.DEVNULL
                )
                logger.info("已断网！检测到固定延时")
        else:
            logger.info("最后一次保存不断网")
    else:
        if not r == t:
            ip = get_domain_ip("cs-gta5-prod.ros.rockstargames.com")
            subprocess.run(
                f'netsh advfirewall firewall add rule '
                f'dir=out action=block protocol=TCP '
                f'remoteip="{ip},192.81.241.171" '
                f'name="仅阻止云存档上传"',
                shell=True, stdout=subprocess.DEVNULL
            )
            logger.info("已断网！检测到固定延时")


def find_gta5_process():
    """查找正在运行的GTA5进程"""
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
    logger.info("准备关闭计算机...")
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

set_gta_output_device("CABLE Input")


# 主逻辑
r = 0
start_time = time.time()
try:
    if run_mode == 0:
        # 新增初始化操作
        logger.info('执行清除断网规则')
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        logger.info("正在执行初始化流程...")
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_hold_delay)
            time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, button_release_delay3)
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
        if cutnetworkset == 1:
            logger.info(f"开始等delay_firewall {delay_firewall}秒")
            time.sleep(delay_firewall)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        else:
            logger.info(f"开始等delay_firewall {delay_firewall}秒")
            time.sleep(delay_firewall)
            cutnetwork()
        listening2()
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        logger.info(f"开始等delay_loading {delay_loading}秒")
        time.sleep(delay_loading)
        # time.sleep(10)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        time.sleep(button_release_delay3)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        gamepad.update()
        time.sleep(button_release_delay3)
        logger.info("执行切换线下人物操作")
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
        logger.info(f"开始等delay_loading {delay_loading}秒")
        time.sleep(delay_loading)
        logger.info('执行清除断网规则')
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        logger.info('假设进入了主菜单返回故事模式')
        for _ in range(2):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT, button_release_delay)
            time.sleep(button_release_delay3)
            time.sleep(button_release_delay3)
        sleep(button_release_delay3)

        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        logger.info(f"开始等delay_loading {delay_loading}秒")
        sleep(delay_loading)
        logger.info("初始化操作完成，开始主循环...")

    while r < t:
        r += 1
        logger.info('执行清除断网规则')
        subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                       stdout=subprocess.DEVNULL)
        logger.info('执行进入线上模式操作')
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_hold_delay)
            time.sleep(button_release_delay)
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, button_release_delay3)
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
            logger.info(f"开始等delay_firewall {delay_firewall}秒")
            time.sleep(delay_firewall)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        else:
            logger.info(f"开始等delay_firewall {delay_firewall}秒")
            time.sleep(delay_firewall)
            cutnetwork2()

        listening()
        press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_hold_delay)
        logger.info(f"开始等delay_loading {delay_loading}秒")
        time.sleep(delay_loading)
        logger.info("执行打断可能来的电话操作")
        for _ in range(3):
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CROSS, button_release_delay)
            press_button(gamepad, vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE, button_release_delay)
            time.sleep(button_release_delay)
        gamepad.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
        gamepad.update()
        time.sleep(button_release_delay3)
        logger.info("执行切换线下人物操作")
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
        logger.info(f"开始等delay_offline_online {delay_offline_online}秒")
        time.sleep(delay_offline_online)
        logger.info(f"已完成 {r} 次 \n")
        getRuntime()
except KeyboardInterrupt:
    logger.info(f"\n已完成 {r} 次，检测到用户中断，正在清理防火墙规则…")
    subprocess.run('netsh advfirewall firewall delete rule name="仅阻止云存档上传"', shell=True,
                   stdout=subprocess.DEVNULL)
    logger.info("防火墙规则已删除，程序安全退出！")
    reset_gta_to_system_default()
    if p.Stream.is_active == True:
        p.Stream.close()
    p.terminate()