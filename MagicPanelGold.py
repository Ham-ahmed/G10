#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold')
import os
import traceback
import socket
import fcntl
import struct
import subprocess
import json
from os.path import join

plugin_name = "MagicPanelGold"
currversion = "10.0" # هذا سيكون الإصدار المحلي. سيتم مقارنته مع version.txt
descplug = "Magic Panel Gold - All in One Tool"
# تم تصحيح رابط سكريبت التحديث ليكون مباشراً
UPDATE_SCRIPT_URL = "https://raw.githubusercontent.com/Ham-ahmed/G10/refs/heads/main/MagicPanelGold-install.sh"

plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold'
if plugin_path not in sys.path:
    sys.path.append(plugin_path)

try:
    from os.path import join
    from Components.AVSwitch import AVSwitch
    from Screens.Screen import Screen
    from Screens.MessageBox import MessageBox
    from Screens.Console import Console
    from Components.Label import Label
    from Components.ActionMap import ActionMap
    from Components.Pixmap import Pixmap
    from Components.MenuList import MenuList
    from Components.ProgressBar import ProgressBar
    from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
    from enigma import eRect, loadPNG, gFont, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_VALIGN_CENTER, getDesktop, eTimer
    from enigma import loadPic

    try:
        from Plugins.Plugin import PluginDescriptor
        HAS_PLUGIN_DESCRIPTOR = True
    except ImportError:
        HAS_PLUGIN_DESCRIPTOR = False
        print("PluginDescriptor not found, will use fallback")

except ImportError as e:
    print(f"Import error in MagicPanelGold: {e}")
    HAS_PLUGIN_DESCRIPTOR = False
    try:
        from Screens.MessageBox import MessageBox
    except:
        pass

try:
    def isFHD():
        try:
            desktop = getDesktop(0)
            size = desktop.size()
            return size.width() >= 1920
        except:
            return False

    def isHD():
        try:
            desktop = getDesktop(0)
            size = desktop.size()
            return size.width() < 1920
        except:
            return True

    skin_path = os.path.join(plugin_path, "skins", "fhd" if isFHD() else "hd")
    picfold = os.path.join(plugin_path, "images")
    nss_pic = os.path.join(picfold, "noplugin.png")

    if not os.path.exists(nss_pic):
        nss_pic = resolveFilename(SCOPE_PLUGINS, "Extensions/MagicPanelGold/images/noplugin.png")

except Exception as e:
    print(f"Error determining screen resolution: {e}")
    skin_path = os.path.join(plugin_path, "skins", "hd")
    picfold = os.path.join(plugin_path, "images")
    nss_pic = os.path.join(picfold, "noplugin.png")

if not os.path.exists(picfold):
    try:
        os.makedirs(picfold)
    except:
        pass

def load_image(image_path):
    try:
        if image_path and os.path.exists(image_path):
            return image_path
        else:
            if image_path:
                alt_path = os.path.join(picfold, os.path.basename(image_path))
                if os.path.exists(alt_path):
                    return alt_path

            default_icons = [
                os.path.join(picfold, "channel.png"),
                os.path.join(picfold, "plugin.png"),
                os.path.join(picfold, "default.png")
            ]

            for icon in default_icons:
                if os.path.exists(icon):
                    return icon

            return nss_pic
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return nss_pic

def get_ip_address(ifname='eth0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', ifname[:15].encode('utf-8'))
        )[20:24])
    except:
        try:
            return os.popen('ip addr show ' + ifname).read().split("inet ")[1].split("/")[0]
        except:
            return "غير متوفر"

# ==================== الدالة المصححة لجلب موديل الجهاز ====================
def get_model():
    """
    جلب موديل الجهاز (الرسيفر) من المسارات القياسية في صور Enigma2.
    """
    try:
        # 1. الطريقة الأكثر شيوعاً: قراءة معلومات الجهاز من أمر "cat /proc/stb/info/model"
        if os.path.exists('/proc/stb/info/model'):
            with open('/proc/stb/info/model', 'r') as f:
                model = f.read().strip()
                if model:
                    return model

        # 2. محاولة من /proc/cpuinfo (مثل BOX MODEL)
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'BOX MODEL' in line or 'machine' in line:
                        parts = line.split(':')
                        if len(parts) > 1:
                            return parts[1].strip()

        # 3. محاولة من /etc/model أو /etc/boxmodel (لبعض الصور)
        for path in ['/etc/model', '/etc/boxmodel']:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    model = f.read().strip()
                    if model:
                        return model

        # 4. استخدام أمر uname -a للحصول على معلومات kernel
        uname = os.popen('uname -a').read()
        # محاولة استخراج اسم النواة أو البنية
        if 'vusolo2' in uname.lower() or 'vusolo' in uname.lower():
            return "Vu+ Solo"
        elif 'vuduo2' in uname.lower() or 'vuduo' in uname.lower():
            return "Vu+ Duo"
        elif 'vuultimo4k' in uname.lower():
            return "Vu+ Ultimo 4K"
        elif 'dm920' in uname.lower() or 'dreambox' in uname.lower():
            # محاولة أكثر تحديداً لـ Dreambox
            if os.path.exists('/proc/stb/info/model'):
                with open('/proc/stb/info/model', 'r') as f:
                    return "Dreambox " + f.read().strip()
            return "Dreambox"
        elif 'hd51' in uname.lower():
            return "HD51"
        elif 'h7' in uname.lower():
            return "H7"
        elif 'sf8008' in uname.lower():
            return "SF8008"
        else:
            # إذا لم نجد شيئاً، نعرض اسم النواة
            return uname.split()[1] if len(uname.split()) > 1 else "نموذج غير معروف"

    except Exception as e:
        print(f"Error in get_model: {e}")
        return "نموذج غير معروف"
# ===========================================================================

def get_image():
    try:
        # محاولة قراءة معلومات الصورة من /etc/issue
        if os.path.exists('/etc/issue'):
            with open('/etc/issue', 'r') as f:
                return f.read().replace('\\n', '').replace('\\l', '').strip()
        # محاولة من /etc/image-version (لبعض الصور)
        elif os.path.exists('/etc/image-version'):
            with open('/etc/image-version', 'r') as f:
                return f.read().strip()
        else:
            return "صورة غير معروفة"
    except:
        return "صورة غير معروفة"

def get_internet_status():
    try:
        if os.path.exists('/sys/class/net/wlan0/operstate'):
            with open('/sys/class/net/wlan0/operstate', 'r') as f:
                if 'up' in f.read():
                    return 'WiFi'

        if os.path.exists('/sys/class/net/eth0/operstate'):
            with open('/sys/class/net/eth0/operstate', 'r') as f:
                if 'up' in f.read():
                    return 'Ethernet'

        return "غير معروف"
    except:
        return "غير معروف"

def get_python_version():
    try:
        return sys.version.split()[0]
    except:
        return "غير معروف"

# دالة مساعدة لمقارنة الإصدارات بشكل صحيح (مثل 10.0, 10.1, 11.0)
def parse_version(version_str):
    try:
        # إزالة أي فراغات أو أحرف غير مرغوب فيها
        version_str = version_str.strip()
        # تقسيم الإصدار إلى أجزاء رقمية
        parts = []
        for part in version_str.split('.'):
            try:
                # محاولة تحويل كل جزء إلى رقم صحيح
                parts.append(int(part))
            except ValueError:
                # إذا احتوى على أحرف، نضيفه كنص (أقل أولوية)
                parts.append(part)
        return parts
    except Exception as e:
        print(f"Error parsing version {version_str}: {e}")
        return [0] # إرجاع قائمة تحتوي على صفر في حالة الخطأ

# ==================== الدالة المصححة للتحقق من التحديثات ====================
def check_for_updates(progress_callback=None):
    """
    التحقق من وجود تحديث جديد عن طريق مقارنة currversion مع version.txt من الخادم.
    تدعم مقارنة الإصدارات مثل 10.0 و 10.1 وما بعدها.
    """
    try:
        import urllib.request

        if progress_callback:
            progress_callback(0, "جاري التحقق من الإصدار...")

        version_url = "https://raw.githubusercontent.com/Ham-ahmed/G10/refs/heads/main/version.txt"

        print(f"جاري التحقق من التحديثات من: {version_url}")

        if progress_callback:
            progress_callback(30, "جاري الاتصال بالخادم...")

        response = urllib.request.urlopen(version_url, timeout=10)

        if progress_callback:
            progress_callback(60, "جاري قراءة البيانات...")

        # قراءة أحدث إصدار من الخادم
        latest_version_str = response.read().decode('utf-8').strip()
        print(f"الإصدار الحالي (محلي): {currversion}")
        print(f"الإصدار الجديد (من الخادم): {latest_version_str}")

        if progress_callback:
            progress_callback(100, "اكتمل التحقق!")

        # تحليل الإصدارات إلى قوائم للمقارنة العددية الصحيحة
        current_parts = parse_version(currversion)
        latest_parts = parse_version(latest_version_str)

        # مقارنة قوائم الإصدارات
        if latest_parts > current_parts:
            print(f"يوجد تحديث جديد: {latest_version_str} > {currversion}")
            return True, latest_version_str
        else:
            print(f"لا توجد تحديثات جديدة. الإصدار الحالي {currversion} هو الأحدث.")
            return False, latest_version_str

    except Exception as e:
        print(f"Error checking for updates: {e}")
        # في حالة حدوث خطأ (مثل عدم وجود اتصال بالإنترنت)، نعتبر أنه لا يوجد تحديث
        return False, currversion
# ===========================================================================

def check_plugin_changes(progress_callback=None):
    try:
        import urllib.request

        plugin_url = "https://raw.githubusercontent.com/Ham-ahmed/G10/refs/heads/main/MagicPanelGold.py"

        print(f"جاري التحقق من التغييرات مباشرة من البلجن: {plugin_url}")

        if progress_callback:
            progress_callback(0, "جاري التحقق من البلجن...")

        req = urllib.request.Request(plugin_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        if progress_callback:
            progress_callback(30, "جاري الاتصال بالخادم...")

        response = urllib.request.urlopen(req, timeout=20)

        if progress_callback:
            progress_callback(60, "جاري تحميل المحتوى...")

        plugin_content = response.read().decode('utf-8')

        if progress_callback:
            progress_callback(80, "جاري تحليل البلجن...")

        changes = extract_changes_from_plugin(plugin_content)
        new_features = extract_new_features_from_plugin(plugin_content)

        if progress_callback:
            progress_callback(100, "اكتمل التحليل!")

        print(f"تم تحليل البلجن: {len(changes)} تغيير و {len(new_features)} ميزة جديدة")

        return changes, new_features

    except Exception as e:
        print(f"خطأ في التحقق من التغييرات من البلجن: {e}")
        return [
            "نظام التحديث التلقائي المحسن",
            "تحسين استقرار البلجن",
            "إصلاح الأخطاء العامة"
        ], [
            "GlobalTranslatePro Grid Atv7.6-BH5.6.006 25-04-2026",
            "Sun 25-04-2026 Time 04:30:00",
        ]

def extract_changes_from_plugin(plugin_content):
    changes = []

    try:
        lines = plugin_content.split('\n')

        change_keywords = ['تحديث', 'إصلاح', 'تحسين', 'إضافة', 'تغيير', 'fix', 'update', 'imGoldve', 'add']

        for i, line in enumerate(lines):
            line_clean = line.strip()
            if any(keyword in line_clean for keyword in change_keywords):
                if line_clean.startswith('#') or '#' in line_clean:
                    change_text = extract_change_text(line_clean)
                    if change_text and change_text not in changes:
                        changes.append(change_text)

                if len(changes) >= 10:
                    break

        if not changes:
            changes = [
                "تحسين نظام التحديث التلقائي",
                "تحسين أداء واجهة المستخدم",
                "إصلاح مشاكل الاستقرار",
                "تحسين تجربة المستخدم العامة"
            ]

    except Exception as e:
        print(f"خطأ في استخراج التغييرات: {e}")
        changes = ["تحسينات عامة في استقرار النظام"]

    return changes

def extract_new_features_from_plugin(plugin_content):
    new_features = []

    try:
        lines = plugin_content.split('\n')

        feature_keywords = ['ميزة', 'جديد', 'دعم', 'feature', 'new', 'support']

        for i, line in enumerate(lines):
            line_clean = line.strip()
            if any(keyword in line_clean for keyword in feature_keywords):
                if line_clean.startswith('#') or '#' in line_clean:
                    feature_text = extract_feature_text(line_clean)
                    if feature_text and feature_text not in new_features:
                        new_features.append(feature_text)

                if len(new_features) >= 10:
                    break

        if not new_features:
            new_features = [
            "GlobalTranslatePro Grid Atv7.6-BH5.6.006 25-04-2026",
            "Sun 25-04-2026 Time 04:30:00",
            "Wed 22-04-2026 Time 04:30:00",
            ]

    except Exception as e:
        print(f"خطأ في استخراج الميزات الجديدة: {e}")
        new_features = ["تحسينات في الأداء والاستقرار"]

    return new_features

def extract_change_text(line):
    try:
        if '#' in line:
            text = line.split('#', 1)[1].strip()
        else:
            text = line.strip()

        text = text.replace('"', '').replace("'", "").strip()

        if len(text) < 8:
            return None

        return text

    except:
        return None

def extract_feature_text(line):
    try:
        if '#' in line:
            text = line.split('#', 1)[1].strip()
        else:
            text = line.strip()

        text = text.replace('"', '').replace("'", "").strip()

        if len(text) < 8:
            return None

        return text

    except:
        return None

class DownloadConfirmation(Screen):
    def __init__(self, session, plugin_name, download_url):
        Screen.__init__(self, session)
        self.plugin_name = plugin_name
        self.download_url = download_url

        self.skin = """
    <screen name="DownloadConfirmation" position="center,center" size="890,500" title="تأكيد التثبيت" backgroundColor="black">
        <widget name="message" position="20,45" size="846,350" font="Regular; 26" halign="center" valign="center" backgroundColor="background" />
        <ePixmap pixmap="skin_default/buttons/red.png" position="196,420" size="40,30" alphatest="on" />
        <ePixmap pixmap="skin_default/buttons/green.png" position="482,420" size="40,30" alphatest="on" />
        <widget name="key_red" position="241,420" size="140,30" font="Regular; 24" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
        <widget name="key_green" position="527,420" size="140,30" font="Regular; 24" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
        <widget source="global.CurrentTime" render="Label" position="656,7" size="210,33" font="Regular; 28" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
            <convert type="ClockToText">Format %H:%M:%S</convert>
        </widget>
    </screen>"""

        self["message"] = Label(_("هل تريد التثبيت %s؟\n\n : %s") % (plugin_name, download_url))
        self["key_red"] = Label(_("لا"))
        self["key_green"] = Label(_("نعم"))

        self["actions"] = ActionMap(["SetupActions", "ColorActions"],
        {
            "red": self.cancel,
            "green": self.confirm,
            "cancel": self.cancel,
            "ok": self.confirm,
        }, -1)

    def cancel(self):
        print("إغلاق نافذة التحميل - إلغاء")
        self.close(False)

    def confirm(self):
        print("تأكيد التحميل")
        self.close(True)

class UpdateConfirmation(Screen):
    def __init__(self, session, current_version, new_version):
        Screen.__init__(self, session)
        self.current_version = current_version
        self.new_version = new_version

        self.changes = []
        self.new_features = []
        self.load_changes_data()

        self.skin = """
    <screen name="UpdateConfirmation" position="center,center" size="980,560" title="تحديث جديد متوفر" backgroundColor="#10202020">
        <widget name="message" position="15,45" size="950,448" font="Regular; 26" halign="left" valign="center" foregroundColor="yellow" backgroundColor="#10101010" />
        <ePixmap pixmap="skin_default/buttons/red.png" position="196,510" size="40,30" alphatest="on" />
        <ePixmap pixmap="skin_default/buttons/green.png" position="632,510" size="40,30" alphatest="on" />
        <widget name="key_red" position="241,510" size="140,30" font="Regular; 24" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
        <widget name="key_green" position="677,510" size="140,30" font="Regular; 24" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
        <widget source="global.CurrentTime" render="Label" position="746,6" size="210,33" font="Regular; 28" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
            <convert type="ClockToText">Format %H:%M:%S</convert>
        </widget>
    </screen>"""

        message = f"🎉 يتوفر تحديث جديد!\n\nالإصدار الحالي: {current_version}\nالإصدار الجديد: {new_version}\n\n"

        if self.new_features:
            message += "🆕 الميزات الجديدة:\n"
            for feature in self.new_features[:6]:
                message += f"• {feature}\n"
            message += "\n"

        if self.changes:
            message += "📝 التغييرات:\n"
            for change in self.changes[:3]:
                message += f"• {change}\n"
            message += "\n"

        message += "هل تريد التحديث الآن؟"

        self["message"] = Label(_(message))
        self["key_red"] = Label(_("لاحقاً"))
        self["key_green"] = Label(_("تحديث الآن"))

        self["actions"] = ActionMap(["SetupActions", "ColorActions"],
        {
            "red": self.cancel,
            "green": self.confirm,
            "cancel": self.cancel,
            "ok": self.confirm,
        }, -1)

    def load_changes_data(self):
        try:
            self.changes, self.new_features = check_plugin_changes()
            print(f"تم تحميل {len(self.changes)} تغيير و {len(self.new_features)} ميزة جديدة مباشرة من البلجن")

        except Exception as e:
            print(f"خطأ في قراءة بيانات التغييرات من البلجن: {e}")
            self.changes = ["إصلاح أخطاء عامة", "تحسين الأداء"]
            self.new_features = ["تحسينات في نظام التحديث", "دعم إضافات جديدة"]

    def cancel(self):
        print("إغلاق نافذة التحديث - إلغاء")
        self.close(False)

    def confirm(self):
        print("تأكيد التحديث")
        self.close(True)

class UpdateProgress(Screen):
    skin = """
    <screen name="UpdateProgress" position="center,center" size="800,250" title="جاري البحث عن تحديثات" backgroundColor="black">
        <widget name="progress" position="100,70" size="600,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold/images/progress.png" transparent="1" />
        <widget name="label" position="100,110" size="600,40" font="Regular;26" halign="center" valign="center" />
        <ePixmap pixmap="skin_default/buttons/red.png" position="310,180" size="40,30" alphatest="on" />
        <widget name="key_red" position="355,180" size="140,30" font="Regular;24" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
        <widget source="global.CurrentTime" render="Label" position="565,5" size="210,33" font="Regular;28" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
            <convert type="ClockToText">Format %H:%M:%S</convert>
        </widget>
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["progress"] = ProgressBar()
        self["label"] = Label(_("جاري التحقق من التحديثات..."))
        self["key_red"] = Label(_("إلغاء"))

        self["actions"] = ActionMap(["SetupActions", "ColorActions"],
        {
            "red": self.cancel,
            "cancel": self.cancel,
        }, -1)

        self.onShown.append(self.start_check)
        self.update_timer = None
        self.check_complete = False

    def start_check(self):
        self.update_timer = eTimer()
        self.update_timer.callback.append(self.do_update_check)
        self.update_timer.start(100, True)

    def do_update_check(self):
        try:
            self.update_progress(0, "جاري التحقق من الاتصال بالإنترنت...")

            internet_status = get_internet_status()
            if internet_status == "غير معروف":
                self.update_progress(100, "لا يوجد اتصال بالإنترنت!")
                self.check_complete = True
                self.close_timer = eTimer()
                self.close_timer.callback.append(self.close_screen)
                self.close_timer.start(2000, True)
                return

            self.update_progress(20, "جاري التحقق من الإصدار...")

            has_update, latest_version = check_for_updates(self.update_progress)

            if has_update:
                self.update_progress(100, f"تم العثور على تحديث جديد: {latest_version}")
                self.check_complete = True
                self.close_timer = eTimer()
                self.close_timer.callback.append(self.close_with_update)
                self.close_timer.start(1500, True)
            else:
                self.update_progress(100, "لا توجد تحديثات جديدة")
                self.check_complete = True
                self.close_timer = eTimer()
                self.close_timer.callback.append(self.close_screen)
                self.close_timer.start(1500, True)

        except Exception as e:
            print(f"خطأ أثناء التحقق من التحديثات: {e}")
            self.update_progress(100, f"خطأ في التحقق: {str(e)}")
            self.check_complete = True
            self.close_timer = eTimer()
            self.close_timer.callback.append(self.close_screen)
            self.close_timer.start(2000, True)

    def update_progress(self, value, label):
        self["progress"].setValue(value)
        self["label"].setText(label)

    def close_with_update(self):
        if self.check_complete:
            self.close(True)

    def close_screen(self):
        if self.check_complete:
            self.close(False)

    def cancel(self):
        print("إلغاء التحقق عن التحديثات")
        if self.update_timer:
            self.update_timer.stop()
        self.close(False)

class ChangesNotification(Screen):
    def __init__(self, session, changes=None, new_features=None):
        Screen.__init__(self, session)

        self.changes = changes if changes else []
        self.new_features = new_features if new_features else []

        self.skin = """
    <screen name="ChangesNotification" position="center,center" size="1050,750" title="التغييرات الجديدة" backgroundColor="black">
       <widget name="message" position="22,48" size="1004,598" font="Regular; 28" itemHeight="50" halign="center" valign="top" backgroundColor="background" />
       <ePixmap pixmap="skin_default/buttons/green.png" position="357,685" size="50,40" alphatest="on" />
       <widget name="key_green" position="467,685" size="160,40" font="Regular; 30" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
       <widget source="global.CurrentTime" render="Label" position="814,6" size="210,33" font="Regular; 30" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
               <convert type="ClockToText">Format %H:%M:%S</convert>
       </widget>
       <eLabel name="OK" text="OK" position="413,685" size="50,40" font="Regular;22" halign="center" transparent="1" valign="bottom" />
       <eLabel name="Exit" text="Exit" position="248,685" size="50,40" font="Regular;22" halign="center" transparent="1" valign="bottom" />
       <ePixmap pixmap="skin_default/buttons/red.png" position="200,685" size="40,40" alphatest="on" />
    </screen>"""

        message = "📢 التغييرات الجديدة في البلجن:\n\n"

        if self.new_features:
            message += "🆕 الميزات الجديدة:\n"
            for feature in self.new_features[:8]:
                message += f"✨ {feature}\n"
            message += "\n"

        if self.changes:
            message += "📝 التغييرات:\n"
            for change in self.changes[:8]:
                message += f"🔧 {change}\n"

        if not self.changes and not self.new_features:
            message += "لا توجد تغييرات أو إضافات جديدة حالياً.\nسيتم إعلامك عند توفر تحديثات جديدة."

        self["message"] = Label(_(message))
        self["key_green"] = Label(_("موافق"))

        self["actions"] = ActionMap(["OkCancelActions"],
        {
            "ok": self.close,
            "cancel": self.close,
        }, -1)

# ==================== تم التصحيح هنا ====================
class AutoUpdateManager:
    def __init__(self, session):
        self.session = session
        self.update_checked = False
        self.last_checked_version = None
        self.update_performed = False

    def check_and_update(self):
        try:
            # إذا تم التحديث مسبقاً في هذه الجلسة، لا تفعل شيئاً
            if self.update_performed:
                print("تم إجراء التحديث مسبقاً، لن يتم التحقق مرة أخرى.")
                return

            # إذا تم التحقق مسبقاً، لا تفعل شيئاً
            if self.update_checked:
                print("تم التحقق من التحديثات مسبقاً في هذه الجلسة.")
                return

            print("بدء التحقق التلقائي من التحديثات...")

            # فتح شاشة التقدم، وعند الانتهاء سيتم استدعاء update_check_callback
            self.session.openWithCallback(
                self.update_check_callback,
                UpdateProgress
            )

        except Exception as e:
            print(f"خطأ أثناء التحقق من التحديثات: {e}")
            import traceback
            traceback.print_exc()

    def update_check_callback(self, has_update):
        try:
            # تعيين علامة بأنه تم التحقق لمنع التكرار
            self.update_checked = True

            if has_update:
                print("تم العثور على تحديث جديد، جاري عرض نافذة التأكيد...")

                # الحصول على أحدث إصدار لعرضه في نافذة التأكيد
                has_update, latest_version = check_for_updates()
                if has_update:
                    self.session.openWithCallback(
                        self.update_confirmation_callback,
                        UpdateConfirmation,
                        currversion,
                        latest_version
                    )
                else:
                    print("تعارض في حالة التحديث، لن يتم عرض نافذة التأكيد.")
            else:
                print("لا توجد تحديثات جديدة")
                # لا حاجة لفعل أي شيء

        except Exception as e:
            print(f"خطأ في معالجة نتيجة التحقق: {e}")

    def update_confirmation_callback(self, result):
        try:
            if result:
                print("المستخدم وافق على التحديث، جاري بدء التحديث...")
                # تعيين علامة بأن التحديث تم لتفعيله
                self.update_performed = True
                self.perform_auto_update()
            else:
                print("المستخدم رفض التحديث التلقائي")
        except Exception as e:
            print(f"خطأ في معالجة تأكيد التحديث: {e}")

    def perform_auto_update(self):
        try:
            print("بدء التحديث التلقائي...")

            # استدعاء سكريبت التحديث من الخادم
            self.session.openWithCallback(
                self.update_complete_callback,
                Console,
                "التحديث التلقائي لـ MagicPanelGold",
                [f"wget -q '{UPDATE_SCRIPT_URL}' -O /tmp/update_magicpanel.sh && bash /tmp/update_magicpanel.sh"]
            )

        except Exception as e:
            print(f"خطأ في التحديث التلقائي: {e}")
            self.session.open(MessageBox, f"فشل التحديث التلقائي: {str(e)}", MessageBox.TYPE_ERROR)

    def update_complete_callback(self, result=None):
        print("اكتمل التحديث التلقائي")
        self.session.open(MessageBox, "تم التحديث بنجاح! يرجى إعادة تشغيل البلجن.", MessageBox.TYPE_INFO)

    def show_changes_only(self):
        # هذه الدالة يمكن تركها كما هي، لكنها ليست جزءاً أساسياً من التصحيح
        print("عرض التغييرات الجديدة فقط...")
        try:
            changes, new_features = check_plugin_changes()
            if changes or new_features:
                self.session.open(ChangesNotification, changes, new_features)
            else:
                self.session.open(MessageBox, "لا توجد تغييرات أو إضافات جديدة حالياً.", MessageBox.TYPE_INFO)
        except Exception as e:
            print(f"خطأ في عرض التغييرات: {e}")
            self.session.open(MessageBox, f"فشل في تحميل التغييرات.\nالسبب: {str(e)}", MessageBox.TYPE_ERROR)
# =======================================================

class ChannelGridMenu(Screen):
    skin = """
    <screen name="ChannelGridMenu" position="center,center" size="1600,780" title="Magic Panel Gold - القائمة الفرعية" backgroundColor="black">
        <widget name="info" position="121,615" size="950,50" font="Regular; 32" halign="center" valign="center" foregroundColor="yellow" />
        <widget name="description" position="121,675" size="950,58" font="Regular; 26" halign="center" valign="center" foregroundColor="white" />
        <widget name="sort" position="1274,585" size="185,30" font="Regular; 26" halign="center" valign="center" backgroundColor="black" transparent="1" foregroundColor="white" />
        <widget name="key_red" position="1279,497" size="185,40" font="Regular; 30" foregroundColor="red" halign="center" valign="center" backgroundColor="black" />
        <widget name="key_yellow" position="1279,541" size="185,40" font="Regular; 30" foregroundColor="yellow" halign="center" valign="center" backgroundColor="black" />
        <widget name="pic_frame" position="113,102" size="164,110" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold/images/pic_frame2.png" zPosition="1" transparent="1" />
        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold/images/panel.png" position="0,0" size="1606,772" zPosition="-10" transparent="1" />
        <widget name="title" position="104,15" zPosition="4" size="870,54" font="Regular; 45" foregroundColor="white" backgroundColor="#40000000" transparent="1" halign="left" valign="center" />
        <ePixmap position="0,75" size="1600,5" zPosition="1" backgroundColor="red" />
        <widget name="pixmap1" position="120,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label1" position="120,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="#b8860b" />
        <widget name="pixmap2" position="320,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label2" position="320,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap3" position="520,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label3" position="520,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap4" position="720,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label4" position="720,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap5" position="920,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label5" position="920,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap6" position="120,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label6" position="120,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap7" position="320,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label7" position="320,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap8" position="520,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label8" position="520,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap9" position="720,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label9" position="720,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap10" position="920,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label10" position="920,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap11" position="120,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label11" position="120,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap12" position="320,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label12" position="320,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap13" position="520,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label13" position="520,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap14" position="720,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label14" position="720,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap15" position="920,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label15" position="920,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <ePixmap position="118,595" size="950,10" zPosition="2" backgroundColor="gold" transparent="1" />
        <ePixmap position="1275,494" size="185,40" zPosition="1" backgroundColor="red" transparent="1" />
        <ePixmap position="1274,540" size="185,40" zPosition="1" backgroundColor="green" transparent="1" />
        <widget name="key_green" position="1274,651" size="185,40" font="Regular;30" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <ePixmap position="1274,653" size="185,40" zPosition="1" backgroundColor="yellow" transparent="1" />
        <ePixmap position="1274,698" size="185,40" zPosition="1" backgroundColor="blue" transparent="1" />
        <widget name="key_blue" position="1275,696" size="185,40" font="Regular;30" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <eLabel position="120,600" size="950,2" backgroundColor="#ff9800" zPosition="1" />
        <widget name="ip_label" position="1214,116" size="300,35" font="Regular; 26" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget name="model_label" position="1214,156" size="300,35" font="Regular; 26" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget name="image_label" position="1214,195" size="361,56" font="Regular; 24" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget name="internet_status" position="1214,257" size="300,35" font="Regular; 26" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget source="global.CurrentTime" render="Label" position="1346,18" size="210,35" font="Regular; 28" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
            <convert type="ClockToText">Format %H:%M:%S</convert>
        </widget>
        <widget source="global.CurrentTime" render="Label" position="1346,47" size="210,35" font="Regular; 28" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
        <convert type="ClockToText">Format:%d.%m.%Y</convert>
        </widget>
        <eLabel backgroundColor="green" cornerRadius="3" position="1274,692" size="185,6" zPosition="11" />
        <eLabel backgroundColor="red" cornerRadius="3" position="1235,494" size="25,40" zPosition="11" />
        <eLabel backgroundColor="yellow" cornerRadius="3" position="1235,540" size="25,40" zPosition="11" />
        <eLabel backgroundColor="blue" cornerRadius="3" position="1274,737" size="185,6" zPosition="11" />
        <eLabel backgroundColor="green" cornerRadius="3" position="1177,122" size="25,25" zPosition="11" />
        <eLabel backgroundColor="red" cornerRadius="3" position="1177,162" size="25,25" zPosition="11" />
        <eLabel backgroundColor="yellow" cornerRadius="3" position="1177,202" size="25,25" zPosition="11" />
        <eLabel backgroundColor="blue" cornerRadius="3" position="1177,262" size="25,25" zPosition="11" />
        <widget name="python_version" position="1214,296" size="300,35" font="Regular; 26" halign="left" transparent="1" backgroundColor="#160000" foregroundColor="#ff8c00" />
        <eLabel name="sort_index" position="521,743" size="52,25" backgroundColor="#40000000" halign="center" valign="center" transparent="1" cornerRadius="26" font="Regular; 42" zPosition="1" text="0" foregroundColor="#40000000" />
        <widget name="sort_label" position="120,741" zPosition="4" size="394,25" font="Regular; 42" foregroundColor="#40000000" backgroundColor="#40000000" transparent="1" halign="left" valign="center" />
        <eLabel backgroundColor="#ff8c00" cornerRadius="3" position="1177,302" size="25,25" zPosition="11" />
        <ePixmap position="1534,15" size="55,55" zPosition="1" backgroundColor="blue" />
        <eLabel name="" position="1106,108" size="480,650" zPosition="-90" cornerRadius="18" backgroundColor="black" foregroundColor="black" borderWidth="2" borderColor="#10808080" />
        <eLabel text="Sort-AZ" position="1274,615" size="185,30" halign="center" font="Regular; 20" backgroundColor="green" transparent="1" valign="center" foregroundColor="green" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,595" size="25,4" zPosition="11" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,610" size="25,4" zPosition="11" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,625" size="25,4" zPosition="11" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,641" size="25,4" zPosition="11" />
        <widget name="qr" position="1175,369" size="90,90" zPosition="11" transparent="1" />
        <widget name="support_txt" position="1284,339" size="276,150" font="Regular; 23" backgroundColor="black" foregroundColor="white" transparent="1" zPosition="11" halign="left" valign="top" />
        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TranslatorProAI/images/MG.png" position="1027,15" size="55,50" zPosition="-1" transparent="1" />
    </screen>"""

    def __init__(self, session, category_name, channels_list):
        Screen.__init__(self, session)
        self.category_name = category_name
        self.channels_list = channels_list

        self.PIXMAPS_PER_PAGE = 15
        self.pos = self.get_positions()
        self.names = []
        self.pics = []
        self.urls = []
        self.titles = []
        self.descriptions = []
        self.sorted = False
        self.index = 0
        self.ipage = 1
        self.minentry = 0
        self.maxentry = 0
        self.npics = 0

        for channel in channels_list:
            if len(channel) >= 3:
                self.names.append(channel[0])
                self.urls.append(channel[1])
                self.pics.append(channel[2])
                self.descriptions.append(channel[3] if len(channel) > 3 else "لا يوجد وصف متاح")
            else:
                self.names.append("عنصر غير معروف")
                self.urls.append("")
                self.pics.append(nss_pic)
                self.descriptions.append("لا يوجد وصف متاح")

        self.titles = self.names[:]

        # إضافة جميع الـ Widgets الضرورية
        self["info"] = Label(_("اختر عنصر للتثبيت..."))
        self["description"] = Label(_(""))
        self["sort"] = Label(_("Sort A-Z"))
        self["key_red"] = Label(_("Exit"))
        self["key_yellow"] = Label(_("Update"))
        self["key_green"] = Label("")
        self["key_blue"] = Label(_("التغييرات"))
        self["cursor"] = Pixmap()
        self["pic_frame"] = Pixmap()
        self["MG"] = Pixmap()
        self["title"] = Label(f"Magic Panel Gold - {category_name}")

        self["ip_label"] = Label()
        self["model_label"] = Label()
        self["image_label"] = Label()
        self["internet_status"] = Label()
        self["python_version"] = Label()
        self["sort_label"] = Label(_("Sort A-Z"))

        # QR code and support text widgets
        self["qr"] = Pixmap()
        self["support_txt"] = Label()

        # إضافة الـ Widgets الديناميكية
        for i in range(1, self.PIXMAPS_PER_PAGE + 1):
            self["pixmap" + str(i)] = Pixmap()
            self["name_label" + str(i)] = Label()

        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"],
        {
            "ok": self.okbuttonClick,
            "cancel": self.close,
            "red": self.close,
            "yellow": self.updatePlugin,
            "blue": self.show_changes_only,
            "left": self.key_left,
            "right": self.key_right,
            "up": self.key_up,
            "down": self.key_down,
            "menu": self.list_sort,
        }, -1)

        self.onLayoutFinish.append(self.paint_screen)
        self.onLayoutFinish.append(self.update_system_info)
        self.setTitle(f"Magic Panel Gold - {category_name}")

    def update_system_info(self):
        try:
            self["ip_label"].setText("IP: " + get_ip_address())
            self["model_label"].setText("model: " + get_model())
            self["image_label"].setText("image: " + get_image())
            self["internet_status"].setText("internet_status: " + get_internet_status())
            self["python_version"].setText("python: " + get_python_version())

            # Load cursor image
            try:
                from Tools.LoadPixmap import LoadPixmap
                cursor_path = os.path.join(plugin_path, "images", "cursor.png")
                if os.path.exists(cursor_path):
                    p = LoadPixmap(path=cursor_path)
                    if p is not None:
                        self["cursor"].instance.setPixmap(p)
                        self["cursor"].show()
                else:
                    print(f"Cursor image not found at: {cursor_path}")

                # Load frame image
                frame_path = os.path.join(plugin_path, "images", "pic_frame2.png")
                if os.path.exists(frame_path):
                    p = LoadPixmap(path=frame_path)
                    if p is not None:
                        self["pic_frame"].instance.setPixmap(p)
                        self["pic_frame"].show()

                 # Load MG image
                MG_path = os.path.join(plugin_path, "images", "MG.png")
                if os.path.exists(MG_path):
                    p = LoadPixmap(path=MG_path)
                    if p is not None:
                        self["MG"].instance.setPixmap(p)
                        self["MG"].show()

                # Load QR code image
                qr_path = os.path.join(plugin_path, "images", "qrcode.png")
                if os.path.exists(qr_path):
                    p = LoadPixmap(path=qr_path)
                    if p is not None:
                        self["qr"].instance.setPixmap(p)
                        self["qr"].show()
            except Exception as e:
                print(f"Error loading images: {e}")

            # Set support text
            support_text = "Do you think this plugin is useful to you?\nSupport the creator and development\nThank you!"
            self["support_txt"].setText(support_text)

        except Exception as e:
            print(f"Error updating system info: {e}")
            self["ip_label"].setText("IP: غير متوفر")
            self["model_label"].setText("النموذج: غير متوفر")
            self["image_label"].setText("الصورة: غير متوفر")
            self["internet_status"].setText("الشبكة: غير متوفر")
            self["python_version"].setText("بايثون: غير متوفر")

    def show_changes_only(self):
        try:
            print("عرض التغييرات الجديدة فقط...")
            changes, new_features = check_plugin_changes()
            if changes or new_features:
                self.session.open(ChangesNotification, changes, new_features)
            else:
                self.session.open(MessageBox, "لا توجد تغييرات أو إضافات جديدة حالياً.", MessageBox.TYPE_INFO)
        except Exception as e:
            print(f"خطأ في عرض التغييرات: {e}")
            self.session.open(MessageBox, f"فشل في تحميل التغييرات.\nالسبب: {str(e)}", MessageBox.TYPE_ERROR)

    def get_positions(self):
        try:
            if isFHD():
                return [
                    [120, 110], [320, 110], [520, 110], [720, 110], [920, 110],
                    [120, 270], [320, 270], [520, 270], [720, 270], [920, 270],
                    [120, 430], [320, 430], [520, 430], [720, 430], [920, 430]
                ]
            else:
                return [
                    [65, 135], [200, 135], [345, 135], [485, 135], [620, 135],
                    [65, 270], [200, 270], [345, 270], [485, 270], [620, 270],
                    [65, 405], [200, 405], [345, 405], [485, 405], [620, 405],
                    [65, 540], [200, 540], [345, 540], [485, 540], [620, 540]
                ]
        except:
            return [
                [65, 135], [200, 135], [345, 135], [485, 135], [620, 135],
                [65, 270], [200, 270], [345, 270], [485, 270], [620, 270],
                [65, 405], [200, 405], [345, 405], [485, 405], [620, 405],
                [65, 540], [200, 540], [345, 540], [485, 540], [620, 540]
            ]

    def get_max_entries(self):
        return len(self.names) - 1

    def paint_screen(self):
        try:
            self.npics = len(self.names)
            if self.npics == 0:
                self["info"].setText("لا توجد عناصر متاحة")
                self["description"].setText("")
                return

            self.npage = (self.npics // self.PIXMAPS_PER_PAGE) + (1 if self.npics % self.PIXMAPS_PER_PAGE > 0 else 0)

            if self.ipage < self.npage:
                self.maxentry = (self.PIXMAPS_PER_PAGE * self.ipage) - 1
                self.minentry = (self.ipage - 1) * self.PIXMAPS_PER_PAGE
            else:
                self.maxentry = self.npics - 1
                self.minentry = (self.ipage - 1) * self.PIXMAPS_PER_PAGE

            for i in range(self.PIXMAPS_PER_PAGE):
                idx = self.minentry + i
                name_widget = self["name_label" + str(i + 1)]
                pixmap_widget = self["pixmap" + str(i + 1)]

                if idx <= self.maxentry and idx < len(self.names):
                    name_widget.setText(self.names[idx])

                    if idx < len(self.pics):
                        pic_path = load_image(self.pics[idx])
                    else:
                        pic_path = nss_pic

                    if pic_path and os.path.exists(pic_path):
                        try:
                            from Tools.LoadPixmap import LoadPixmap
                            p = LoadPixmap(path=pic_path)
                            if p is not None:
                                pixmap_widget.instance.setPixmap(p)
                                pixmap_widget.show()
                            else:
                                pixmap_widget.hide()
                        except Exception as e:
                            print(f"Error loading pixmap {pic_path}: {e}")
                            pixmap_widget.hide()
                    else:
                        pixmap_widget.hide()
                else:
                    name_widget.setText(" ")
                    pixmap_widget.hide()

            self.update_cursor()
            if 0 <= self.index < len(self.names):
                self["info"].setText(self.names[self.index])
            else:
                self["info"].setText(" ")
            self.update_description()

        except Exception as e:
            print(f"Error in paint_screen: {e}")
            self["info"].setText("خطأ في تحميل المحتوى")
            self["description"].setText("")

    def update_description(self):
        try:
            if 0 <= self.index < len(self.descriptions):
                description = self.descriptions[self.index]
                if description:
                    self["description"].setText(description)
                else:
                    self["description"].setText("لا يوجد وصف متاح")
            else:
                self["description"].setText("")
        except Exception as e:
            print(f"Error updating description: {e}")
            self["description"].setText("")

    def get_cursor_position(self, relative_index):
        try:
            if 0 <= relative_index < self.PIXMAPS_PER_PAGE:
                widget_name = "pixmap" + str(relative_index + 1)
                if widget_name in self:
                    selected_widget = self[widget_name]
                    position = selected_widget.getPosition()
                    size = selected_widget.getSize()

                    cursor_x = position[0] - 5
                    cursor_y = position[1] - 5
                    cursor_width = size[0] + 10
                    cursor_height = size[1] + 10

                    return (cursor_x, cursor_y, cursor_width, cursor_height)
            return None
        except Exception as e:
            print(f"Error getting cursor position: {e}")
            return None

    def update_cursor(self, animate=True):
        try:
            if 0 <= self.index < len(self.names):
                relative_index = self.index - self.minentry

                new_pos = self.get_cursor_position(relative_index)
                if new_pos:
                    self["cursor"].move(eRect(*new_pos))
                    self["cursor"].show()
                    # تحديث موقع الإطار أيضا
                    self["pic_frame"].move(eRect(new_pos[0] - 8, new_pos[1] - 8, new_pos[2] + 16, new_pos[3] + 16))
                    self["pic_frame"].show()
                else:
                    self["cursor"].hide()
                    self["pic_frame"].hide()

                self["info"].setText(self.names[self.index])
                self.update_description()
            else:
                self["cursor"].hide()
                self["pic_frame"].hide()
                self["info"].setText(" ")
                self["description"].setText("")
        except Exception as e:
            print(f"Error in update_cursor: {e}")
            self["cursor"].hide()
            self["pic_frame"].hide()

    def key_left(self):
        if self.index > 0:
            self.index -= 1
            if self.index < self.minentry:
                self.ipage = max(1, self.ipage - 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])

    def key_right(self):
        if self.index < len(self.names) - 1:
            self.index += 1
            if self.index > self.maxentry:
                self.ipage = min(self.npage, self.ipage + 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])

    def key_up(self):
        if self.index - 5 >= 0:
            self.index -= 5
            if self.index < self.minentry:
                self.ipage = max(1, self.ipage - 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])
        else:
            self.index = self.maxentry
            self.paint_screen()

    def key_down(self):
        if self.index + 5 < len(self.names):
            self.index += 5
            if self.index > self.maxentry:
                self.ipage = min(self.npage, self.ipage + 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])
        else:
            self.index = self.minentry
            self.paint_screen()

    def list_sort(self):
        try:
            if not hasattr(self, "original_data"):
                self.original_data = (list(self.names), list(self.titles), list(self.pics), list(self.urls), list(self.descriptions))
                self.sorted = False

            if self.sorted:
                self.names, self.titles, self.pics, self.urls, self.descriptions = self.original_data
                self["sort"].setText("ترتيب أبجدي")
                self["sort_label"].setText("ترتيب أبجدي")
            else:
                combined = list(zip(self.names, self.titles, self.pics, self.urls, self.descriptions))
                combined.sort(key=lambda x: x[0].lower() if isinstance(x[0], str) else str(x[0]))
                if combined:
                    self.names, self.titles, self.pics, self.urls, self.descriptions = zip(*combined)
                else:
                    self.names, self.titles, self.pics, self.urls, self.descriptions = ([], [], [], [], [])
                self["sort"].setText("ترتيب افتراضي")
                self["sort_label"].setText("ترتيب افتراضي")

            self.sorted = not self.sorted
            self.paint_screen()
        except Exception as e:
            print(f"Error in list_sort: {e}")

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                plugin_name = self.names[self.index]
                download_url = self.urls[self.index]

                if download_url and download_url.strip():
                    self.download_with_confirmation(plugin_name, download_url)
                else:
                    self.session.open(MessageBox, "رابط التحميل غير متوفر!", MessageBox.TYPE_ERROR)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في التثبيت: %s" % str(e), MessageBox.TYPE_ERROR)

    def updatePlugin(self):
        try:
            self.session.openWithCallback(
                self.manual_update_check_callback,
                UpdateProgress
            )

        except Exception as e:
            self.session.open(MessageBox, "فشل التحقق من التحديثات: %s" % str(e), MessageBox.TYPE_ERROR)

    def manual_update_check_callback(self, has_update):
        if has_update:
            has_update, latest_version = check_for_updates()
            if has_update:
                self.session.openWithCallback(
                    self.manual_update_callback,
                    UpdateConfirmation,
                    currversion,
                    latest_version
                )
            else:
                self.session.open(MessageBox, "لا توجد تحديثات جديدة متاحة!", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "لا توجد تحديثات جديدة متاحة!", MessageBox.TYPE_INFO)

    def manual_update_callback(self, result):
        if result:
            self.session.open(Console, "تحديث MagicPanelGold",
                            ["wget -q '%s' -O /tmp/update_magicpanel.sh && bash /tmp/update_magicpanel.sh" % UPDATE_SCRIPT_URL])

    def download_with_confirmation(self, plugin_name, download_url):
        def confirmation_callback(result):
            if result:
                self.start_download(plugin_name, download_url)
            else:
                self["info"].setText("تم إلغاء التثبيت")

        self.session.openWithCallback(confirmation_callback, DownloadConfirmation, plugin_name, download_url)

    def start_download(self, plugin_name, download_url):
        try:
            print(f"Installing: {plugin_name}")
            print(f"URL: {download_url}")

            self["info"].setText(f"جاري تثبيت {plugin_name}...")

            clean_url = download_url.strip()
            if clean_url.startswith(('"', "'")):
                clean_url = clean_url[1:]
            if clean_url.endswith(('"', "'")):
                clean_url = clean_url[:-1]

            if not clean_url.startswith('http'):
                clean_url = 'https://' + clean_url

            cmd = f"wget -q '{clean_url}' -O /tmp/install_script.sh && chmod +x /tmp/install_script.sh && bash /tmp/install_script.sh"
            self.session.open(Console, f"جاري تثبيت {plugin_name}", [cmd])

        except Exception as e:
            error_msg = f"فشل التثبيت: {str(e)}"
            print(error_msg)
            self.session.open(MessageBox, error_msg, MessageBox.TYPE_ERROR)

class BasePanel(Screen):
    skin = """
    <screen name="BasePanel" position="center,center" size="1600,780" title="Magic Panel Gold" backgroundColor="black">
        <widget name="info" position="121,615" size="950,50" font="Regular; 32" halign="center" valign="center" foregroundColor="yellow" />
        <widget name="description" position="121,675" size="950,58" font="Regular; 26" halign="center" valign="center" foregroundColor="white" />
        <widget name="sort" position="1274,585" size="185,30" font="Regular; 26" halign="center" valign="center" backgroundColor="black" transparent="1" foregroundColor="white" />
        <widget name="key_red" position="1279,497" size="185,40" font="Regular; 30" foregroundColor="red" halign="center" valign="center" backgroundColor="black" />
        <widget name="key_yellow" position="1279,541" size="185,40" font="Regular; 30" foregroundColor="yellow" halign="center" valign="center" backgroundColor="black" />
        <widget name="pic_frame" position="113,102" size="164,110" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold/images/pic_frame2.png" zPosition="1" transparent="1" />
        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold/images/panel.png" position="0,0" size="1606,772" zPosition="-10" transparent="1" />
        <widget name="title" position="104,15" zPosition="4" size="870,54" font="Regular; 45" foregroundColor="white" backgroundColor="#40000000" transparent="1" halign="left" valign="center" />
        <ePixmap position="0,75" size="1600,5" zPosition="1" backgroundColor="red" />
        <widget name="pixmap1" position="120,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label1" position="120,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="#b8860b" />
        <widget name="pixmap2" position="320,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label2" position="320,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap3" position="520,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label3" position="520,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap4" position="720,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label4" position="720,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap5" position="920,110" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label5" position="920,220" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap6" position="120,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label6" position="120,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap7" position="320,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label7" position="320,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap8" position="520,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label8" position="520,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap9" position="720,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label9" position="720,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap10" position="920,270" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label10" position="920,380" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap11" position="120,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label11" position="120,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap12" position="320,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label12" position="320,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap13" position="520,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label13" position="520,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap14" position="720,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label14" position="720,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <widget name="pixmap15" position="920,430" size="150,100" zPosition="2" transparent="1" />
        <widget name="name_label15" position="920,540" size="150,30" font="Regular; 23" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <ePixmap position="118,595" size="950,10" zPosition="2" backgroundColor="gold" transparent="1" />
        <ePixmap position="1275,494" size="185,40" zPosition="1" backgroundColor="red" transparent="1" />
        <ePixmap position="1274,540" size="185,40" zPosition="1" backgroundColor="green" transparent="1" />
        <widget name="key_green" position="1274,651" size="185,40" font="Regular;30" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <ePixmap position="1274,653" size="185,40" zPosition="1" backgroundColor="yellow" transparent="1" />
        <ePixmap position="1274,698" size="185,40" zPosition="1" backgroundColor="blue" transparent="1" />
        <widget name="key_blue" position="1275,696" size="185,40" font="Regular;30" halign="center" valign="center" backgroundColor="transparent" transparent="1" foregroundColor="white" />
        <eLabel position="120,600" size="950,2" backgroundColor="#ff9800" zPosition="1" />
        <widget name="ip_label" position="1214,116" size="300,35" font="Regular; 26" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget name="model_label" position="1214,156" size="300,35" font="Regular; 26" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget name="image_label" position="1214,195" size="361,56" font="Regular; 24" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget name="internet_status" position="1214,257" size="300,35" font="Regular; 26" foregroundColor="white" zPosition="2" backgroundColor="black" transparent="1" />
        <widget source="global.CurrentTime" render="Label" position="1346,18" size="210,35" font="Regular; 28" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
            <convert type="ClockToText">Format %H:%M:%S</convert>
        </widget>
        <widget source="global.CurrentTime" render="Label" position="1346,47" size="210,35" font="Regular; 28" halign="center" foregroundColor="#b8860b" backgroundColor="#160000" transparent="1" zPosition="6">
        <convert type="ClockToText">Format:%d.%m.%Y</convert>
        </widget>
        <eLabel backgroundColor="green" cornerRadius="3" position="1274,692" size="185,6" zPosition="11" />
        <eLabel backgroundColor="red" cornerRadius="3" position="1235,494" size="25,40" zPosition="11" />
        <eLabel backgroundColor="yellow" cornerRadius="3" position="1235,540" size="25,40" zPosition="11" />
        <eLabel backgroundColor="blue" cornerRadius="3" position="1274,737" size="185,6" zPosition="11" />
        <eLabel backgroundColor="green" cornerRadius="3" position="1177,122" size="25,25" zPosition="11" />
        <eLabel backgroundColor="red" cornerRadius="3" position="1177,162" size="25,25" zPosition="11" />
        <eLabel backgroundColor="yellow" cornerRadius="3" position="1177,202" size="25,25" zPosition="11" />
        <eLabel backgroundColor="blue" cornerRadius="3" position="1177,262" size="25,25" zPosition="11" />
        <widget name="python_version" position="1214,296" size="300,35" font="Regular; 26" halign="left" transparent="1" backgroundColor="#160000" foregroundColor="#ff8c00" />
        <eLabel name="sort_index" position="521,743" size="52,25" backgroundColor="#40000000" halign="center" valign="center" transparent="1" cornerRadius="26" font="Regular; 42" zPosition="1" text="0" foregroundColor="#40000000" />
        <widget name="sort_label" position="120,741" zPosition="4" size="394,25" font="Regular; 42" foregroundColor="#40000000" backgroundColor="#40000000" transparent="1" halign="left" valign="center" />
        <eLabel backgroundColor="#ff8c00" cornerRadius="3" position="1177,302" size="25,25" zPosition="11" />
        <ePixmap position="1534,15" size="55,55" zPosition="1" backgroundColor="blue" />
        <eLabel name="" position="1106,108" size="480,650" zPosition="-90" cornerRadius="18" backgroundColor="black" foregroundColor="black" borderWidth="2" borderColor="#10808080" />
        <eLabel text="Sort-AZ" position="1274,615" size="185,30" halign="center" font="Regular; 20" backgroundColor="green" transparent="1" valign="center" foregroundColor="green" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,595" size="25,4" zPosition="11" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,610" size="25,4" zPosition="11" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,625" size="25,4" zPosition="11" />
        <eLabel backgroundColor="white" cornerRadius="3" position="1235,641" size="25,4" zPosition="11" />
        <widget name="qr" position="1175,369" size="90,90" zPosition="11" transparent="1" />
        <widget name="support_txt" position="1284,339" size="276,150" font="Regular; 23" backgroundColor="black" foregroundColor="white" transparent="1" zPosition="11" halign="left" valign="top" />
        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TranslatorProAI/images/MG.png" position="1027,15" size="55,50" zPosition="-1" transparent="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.PIXMAPS_PER_PAGE = 15
        self.pos = self.get_positions()
        self.names = []
        self.pics = []
        self.urls = []
        self.titles = []
        self.descriptions = []
        self.sorted = False
        self.index = 0
        self.ipage = 1
        self.minentry = 0
        self.maxentry = 0
        self.npics = 0

        # إضافة جميع الـ Widgets الضرورية
        self["info"] = Label(_("Please Wait..."))
        self["description"] = Label(_(""))
        self["sort"] = Label(_("Sort A-Z"))
        self["key_red"] = Label(_("Exit"))
        self["key_yellow"] = Label(_("Update"))
        self["key_green"] = Label("")
        self["key_blue"] = Label(_("التغييرات"))
        self["cursor"] = Pixmap()
        self["pic_frame"] = Pixmap()
        self["MG"] = Pixmap()
        self["title"] = Label("Magic Panel Gold")

        self["ip_label"] = Label()
        self["model_label"] = Label()
        self["image_label"] = Label()
        self["internet_status"] = Label()
        self["python_version"] = Label()
        self["sort_label"] = Label(_("Sort A-Z"))

        # QR code and support text widgets
        self["qr"] = Pixmap()
        self["support_txt"] = Label()

        # إضافة الـ Widgets الديناميكية
        for i in range(1, self.PIXMAPS_PER_PAGE + 1):
            self["pixmap" + str(i)] = Pixmap()
            self["name_label" + str(i)] = Label()

        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"],
        {
            "ok": self.okbuttonClick,
            "cancel": self.close,
            "red": self.close,
            "yellow": self.updatePlugin,
            "blue": self.show_changes,
            "left": self.key_left,
            "right": self.key_right,
            "up": self.key_up,
            "down": self.key_down,
            "menu": self.list_sort,
        }, -1)

        self.onLayoutFinish.append(self.paint_screen)
        self.onLayoutFinish.append(self.update_system_info)

    def update_system_info(self):
        try:
            self["ip_label"].setText("IP: " + get_ip_address())
            self["model_label"].setText("model: " + get_model())
            self["image_label"].setText("image: " + get_image())
            self["internet_status"].setText("internet_status: " + get_internet_status())
            self["python_version"].setText("python: " + get_python_version())

            # Load cursor and frame images
            try:
                from Tools.LoadPixmap import LoadPixmap
                cursor_path = os.path.join(plugin_path, "images", "cursor.png")
                if os.path.exists(cursor_path):
                    p = LoadPixmap(path=cursor_path)
                    if p is not None:
                        self["cursor"].instance.setPixmap(p)
                        self["cursor"].show()
                else:
                    print(f"Cursor image not found at: {cursor_path}")

                # Load frame image
                frame_path = os.path.join(plugin_path, "images", "pic_frame2.png")
                if os.path.exists(frame_path):
                    p = LoadPixmap(path=frame_path)
                    if p is not None:
                        self["pic_frame"].instance.setPixmap(p)
                        self["pic_frame"].show()

                # Load QR code image
                qr_path = os.path.join(plugin_path, "images", "qrcode.png")
                if os.path.exists(qr_path):
                    p = LoadPixmap(path=qr_path)
                    if p is not None:
                        self["qr"].instance.setPixmap(p)
                        self["qr"].show()
            except Exception as e:
                print(f"Error loading images: {e}")

            # Set support text
            support_text = "Do you think this plugin is useful to you?\nSupport the creator and development\nThank you!"
            self["support_txt"].setText(support_text)

        except Exception as e:
            print(f"Error updating system info: {e}")
            self["ip_label"].setText("IP: غير متوفر")
            self["model_label"].setText("النموذج: غير متوفر")
            self["image_label"].setText("الصورة: غير متوفر")
            self["internet_status"].setText("الشبكة: غير متوفر")
            self["python_version"].setText("بايثون: غير متوفر")

    def get_positions(self):
        try:
            if isFHD():
                return [
                    [120, 110], [320, 110], [520, 110], [720, 110], [920, 110],
                    [120, 270], [320, 270], [520, 270], [720, 270], [920, 270],
                    [120, 430], [320, 430], [520, 430], [720, 430], [920, 430]
                ]
            else:
                return [
                    [65, 135], [200, 135], [345, 135], [485, 135], [620, 135],
                    [65, 270], [200, 270], [345, 270], [485, 270], [620, 270],
                    [65, 405], [200, 405], [345, 405], [485, 405], [620, 405],
                    [65, 540], [200, 540], [345, 540], [485, 540], [620, 540]
                ]
        except:
            return [
                [65, 135], [200, 135], [345, 135], [485, 135], [620, 135],
                [65, 270], [200, 270], [345, 270], [485, 270], [620, 270],
                [65, 405], [200, 405], [345, 405], [485, 405], [620, 405],
                [65, 540], [200, 540], [345, 540], [485, 540], [620, 540]
            ]

    def get_max_entries(self):
        return len(self.names) - 1

    def paint_screen(self):
        try:
            self.npics = len(self.names)
            if self.npics == 0:
                self["info"].setText("لا توجد عناصر متاحة")
                self["description"].setText("")
                return

            self.npage = (self.npics // self.PIXMAPS_PER_PAGE) + (1 if self.npics % self.PIXMAPS_PER_PAGE > 0 else 0)

            if self.ipage < self.npage:
                self.maxentry = (self.PIXMAPS_PER_PAGE * self.ipage) - 1
                self.minentry = (self.ipage - 1) * self.PIXMAPS_PER_PAGE
            else:
                self.maxentry = self.npics - 1
                self.minentry = (self.ipage - 1) * self.PIXMAPS_PER_PAGE

            for i in range(self.PIXMAPS_PER_PAGE):
                idx = self.minentry + i
                name_widget = self["name_label" + str(i + 1)]
                pixmap_widget = self["pixmap" + str(i + 1)]

                if idx <= self.maxentry and idx < len(self.names):
                    name_widget.setText(self.names[idx])

                    if idx < len(self.pics):
                        pic_path = load_image(self.pics[idx])
                    else:
                        pic_path = nss_pic

                    if pic_path and os.path.exists(pic_path):
                        try:
                            from Tools.LoadPixmap import LoadPixmap
                            p = LoadPixmap(path=pic_path)
                            if p is not None:
                                pixmap_widget.instance.setPixmap(p)
                                pixmap_widget.show()
                            else:
                                pixmap_widget.hide()
                        except Exception as e:
                            print(f"Error loading pixmap {pic_path}: {e}")
                            pixmap_widget.hide()
                    else:
                        pixmap_widget.hide()
                else:
                    name_widget.setText(" ")
                    pixmap_widget.hide()

            self.update_cursor()
            if 0 <= self.index < len(self.names):
                self["info"].setText(self.names[self.index])
            else:
                self["info"].setText(" ")
            self.update_description()

        except Exception as e:
            print(f"Error in paint_screen: {e}")
            self["info"].setText("خطأ في تحميل المحتوى")
            self["description"].setText("")

    def update_description(self):
        try:
            if 0 <= self.index < len(self.descriptions):
                description = self.descriptions[self.index]
                if description:
                    self["description"].setText(description)
                else:
                    self["description"].setText("لا يوجد وصف متاح")
            else:
                self["description"].setText("")
        except Exception as e:
            print(f"Error updating description: {e}")
            self["description"].setText("")

    def get_cursor_position(self, relative_index):
        try:
            if 0 <= relative_index < self.PIXMAPS_PER_PAGE:
                widget_name = "pixmap" + str(relative_index + 1)
                if widget_name in self:
                    selected_widget = self[widget_name]
                    position = selected_widget.getPosition()
                    size = selected_widget.getSize()

                    cursor_x = position[0] - 5
                    cursor_y = position[1] - 5
                    cursor_width = size[0] + 10
                    cursor_height = size[1] + 10

                    return (cursor_x, cursor_y, cursor_width, cursor_height)
            return None
        except Exception as e:
            print(f"Error getting cursor position: {e}")
            return None

    def update_cursor(self, animate=True):
        try:
            if 0 <= self.index < len(self.names):
                relative_index = self.index - self.minentry

                new_pos = self.get_cursor_position(relative_index)
                if new_pos:
                    self["cursor"].move(eRect(*new_pos))
                    self["cursor"].show()
                    # تحديث موقع الإطار أيضا
                    self["pic_frame"].move(eRect(new_pos[0] - 8, new_pos[1] - 8, new_pos[2] + 16, new_pos[3] + 16))
                    self["pic_frame"].show()
                else:
                    self["cursor"].hide()
                    self["pic_frame"].hide()

                self["info"].setText(self.names[self.index])
                self.update_description()
            else:
                self["cursor"].hide()
                self["pic_frame"].hide()
                self["info"].setText(" ")
                self["description"].setText("")
        except Exception as e:
            print(f"Error in update_cursor: {e}")
            self["cursor"].hide()
            self["pic_frame"].hide()

    def key_left(self):
        if self.index > 0:
            self.index -= 1
            if self.index < self.minentry:
                self.ipage = max(1, self.ipage - 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])

    def key_right(self):
        if self.index < len(self.names) - 1:
            self.index += 1
            if self.index > self.maxentry:
                self.ipage = min(self.npage, self.ipage + 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])

    def key_up(self):
        if self.index - 5 >= 0:
            self.index -= 5
            if self.index < self.minentry:
                self.ipage = max(1, self.ipage - 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])
        else:
            self.index = self.maxentry
            self.paint_screen()

    def key_down(self):
        if self.index + 5 < len(self.names):
            self.index += 5
            if self.index > self.maxentry:
                self.ipage = min(self.npage, self.ipage + 1)
                self.paint_screen()
            else:
                self.update_cursor()
                if self.index < len(self.names):
                    self["info"].setText(self.names[self.index])
        else:
            self.index = self.minentry
            self.paint_screen()

    def list_sort(self):
        try:
            if not hasattr(self, "original_data"):
                self.original_data = (list(self.names), list(self.titles), list(self.pics), list(self.urls), list(self.descriptions))
                self.sorted = False

            if self.sorted:
                self.names, self.titles, self.pics, self.urls, self.descriptions = self.original_data
                self["sort"].setText("ترتيب أبجدي")
                self["sort_label"].setText("ترتيب أبجدي")
            else:
                combined = list(zip(self.names, self.titles, self.pics, self.urls, self.descriptions))
                combined.sort(key=lambda x: x[0].lower() if isinstance(x[0], str) else str(x[0]))
                if combined:
                    self.names, self.titles, self.pics, self.urls, self.descriptions = zip(*combined)
                else:
                    self.names, self.titles, self.pics, self.urls, self.descriptions = ([], [], [], [], [])
                self["sort"].setText("ترتيب افتراضي")
                self["sort_label"].setText("ترتيب افتراضي")

            self.sorted = not self.sorted
            self.paint_screen()
        except Exception as e:
            print(f"Error in list_sort: {e}")

    def okbuttonClick(self):
        pass

    def updatePlugin(self):
        try:
            has_update, latest_version = check_for_updates()

            if has_update:
                changes, new_features = check_plugin_changes()
                self.session.openWithCallback(
                    self.manual_update_callback,
                    UpdateConfirmation,
                    currversion,
                    latest_version
                )
            else:
                changes, new_features = check_plugin_changes()
                if changes or new_features:
                    self.session.openWithCallback(
                        self.changes_notification_callback,
                        ChangesNotification,
                        changes,
                        new_features
                    )
                else:
                    self.session.open(MessageBox, "لا توجد تحديثات جديدة متاحة!", MessageBox.TYPE_INFO)

        except Exception as e:
            self.session.open(MessageBox, "فشل التحقق من التحديثات: %s" % str(e), MessageBox.TYPE_ERROR)

    def manual_update_callback(self, result):
        try:
            if result:
                self.session.open(Console, "تحديث MagicPanelGold",
                                ["wget -q '%s' -O /tmp/update_magicpanel.sh && bash /tmp/update_magicpanel.sh" % UPDATE_SCRIPT_URL])
        except Exception as e:
            print(f"خطأ في معالجة التحديث اليدوي: {e}")
            self.session.open(MessageBox, f"فشل بدء التحديث: {str(e)}", MessageBox.TYPE_ERROR)

    def changes_notification_callback(self, result=None):
        print("تم عرض التغييرات الجديدة")

    def show_changes(self):
        try:
            print("عرض التغييرات والإضافات الجديدة...")
            changes, new_features = check_plugin_changes()

            print(f"تم جلب {len(changes)} تغيير و {len(new_features)} ميزة جديدة")

            if changes or new_features:
                self.session.open(
                    ChangesNotification,
                    changes,
                    new_features
                )
            else:
                self.session.open(
                    MessageBox,
                    "لا توجد تغييرات أو إضافات جديدة حالياً.\nسيتم إعلامك عند توفر تحديثات جديدة.",
                    MessageBox.TYPE_INFO
                )

        except Exception as e:
            print(f"خطأ في عرض التغييرات: {e}")
            default_changes = [
                "تحسينات في استقرار النظام",
                "إصلاح مشاكل التحميل",
                "تحسينات في الأداء",
                "تحسين واجهة المستخدم"
            ]
            default_features = [
                "دعم أحدث الإصدارات",
                "تحسين تجربة المستخدم",
                "إضافة خيارات جديدة"
            ]

            self.session.open(
                ChangesNotification,
                default_changes,
                default_features
            )

    def download_with_confirmation(self, plugin_name, download_url):
        def confirmation_callback(result):
            if result:
                self.start_download(plugin_name, download_url)
            else:
                self["info"].setText("تم إلغاء التثبيت")

        self.session.openWithCallback(confirmation_callback, DownloadConfirmation, plugin_name, download_url)

    def start_download(self, plugin_name, download_url):
        try:
            print(f"Installing: {plugin_name}")
            print(f"URL: {download_url}")

            self["info"].setText(f"جاري تثبيت {plugin_name}...")

            clean_url = download_url.strip()
            if clean_url.startswith(('"', "'")):
                clean_url = clean_url[1:]
            if clean_url.endswith(('"', "'")):
                clean_url = clean_url[:-1]

            if not clean_url.startswith('http'):
                clean_url = 'https://' + clean_url

            cmd = f"wget -q '{clean_url}' -O /tmp/install_script.sh && chmod +x /tmp/install_script.sh && bash /tmp/install_script.sh"
            self.session.open(Console, f"جاري تثبيت {plugin_name}", [cmd])

        except Exception as e:
            error_msg = f"فشل التثبيت: {str(e)}"
            print(error_msg)
            self.session.open(MessageBox, error_msg, MessageBox.TYPE_ERROR)

class SkinsPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Skins"
        self["info"].setText("اختر فئة السكين...")

        self.skin_data = {
            "OpenATV Skins": {
                "icon": os.path.join(picfold, "atv.png"),
                "description": "سكينس مخصصة لصورة OpenATV",
                "channels": [
                   ("RED-KNIGHT-FHD-v1.0-mod-H-Ahmed.py3.136-7.", "https://raw.githubusercontent.com/Ham-ahmed/knight/refs/heads/main/RED-KNIGHT-FHD-v1.0-mod-HAhmed.sh", os.path.join(picfold, "Re001.png"), "سكين RED-KNIGHT معدل من Hamdy-Ahmed"),
                   ("Artemis_v1.0-mod_H-Ahmed-OPENATV-py3.13.6-7", "https://raw.githubusercontent.com/Ham-ahmed/288/refs/heads/main/Artemis_-v1.0-mod_HAhmed.sh", os.path.join(picfold, "art001.png"), "سكين Artemis معدل من Hamdy-Ahmed"),
                   ("Sky-Novalerx_3.0-OPENATV-py3.13.6_Mod-H-Ahmed", "https://raw.githubusercontent.com/Ham-ahmed/Skins/refs/heads/main/Sky-Novalerx_3.0-MOD_HAhmed.sh", os.path.join(picfold, "sky001.png"), "سكين Artemis معدل من Hamdy-Ahmed"),
                   ("GigabluePaxV4-Skin3x1_OPENATV_Mod-H-Ahmed", "https://raw.githubusercontent.com/Ham-ahmed/Atv/refs/heads/main/GigabluePaxV4-Skin3x1_ATV_Mod-H-Ahmed.sh", os.path.join(picfold, "gig001.png"), "سكين Artemis معدل من Hamdy-Ahmed"),
                   ("AglareFHD_v.5.6-D.Mohamed-Nasr", "https://raw.githubusercontent.com/Ham-ahmed/154/refs/heads/main/Aglare-FHD-v5.6.sh", os.path.join(picfold, "agl001.png"), "سكين Algare By Mohamed-Nasr"),
                   ("AglareFHD_v.5.4-D.Mohamed-Nasr", "https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglareatv/installer.sh", os.path.join(picfold, "agl001.png"), "سكين Algare By Mohamed-Nasr"),
                   ("MaxyFHD-v1.3-D.Mohamed-Nasr", "https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh", os.path.join(picfold, "max001.png"), "سكين MaxyFHD By Mohamed-Nasr"),
                   ("xDreamyFHD_v.5.8.1-Mahamoud-Hussein", "https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين xdreamy By Mahamoud-Hussein"),
                   ("xDreamyFHD_v.5.2.1-Mahamoud-Hussein", "https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين xdreamy By Mahamoud-Hussein"),
                   ("xDreamyFHD_v.5.2-Mahamoud-Hussein", "https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين xdreamy By Mahamoud-Hussein"),
                   ("xDreamyFHD_v.5.2-Mahamoud-Hussein", "https://raw.githubusercontent.com/Ham-ahmed/openatv/main/metrix_skinparts_mnasr.sh", os.path.join(picfold, "xdr001.png"), "سكين metrix By Mahamoud-Hussein"),
                   ("fullhdglass17 skin 9.50-06-05-2025 ", "https://raw.githubusercontent.com/Ham-ahmed/65/refs/heads/main/fullhdglass17_9.50.sh", os.path.join(picfold, "gls001.png")),
                ]
            },
            "OpenPLI Skins": {
                "icon": os.path.join(picfold, "pll.png"),
                "channels": [
                   ("GigabluePaxV4-Skin3x1_OPENPli-GCC-py3.12-_Mod-H", "https://gitlab.com/h-ahmed/Panel/-/raw/main/pli/GigabluePaxV4-Skin3x1_PLi-GCC_Mod-H-Ahmed.sh", os.path.join(picfold, "gig001.png"), "سكين Gigablue معدل من Hamdy-Ahmed"),
                   ("PLi-FullNightFHD-v1.0-H_Ahmed-py3.13-foxbob-Gcc14.2", "https://raw.githubusercontent.com/Ham-ahmed/pli/refs/heads/main/PLi-FullNightFHD_v1.0-Mod-HA.sh", os.path.join(picfold, "plin001.png"), "سكين Fullnight معدل من Hamdy-Ahmed"),
                   ("Luka-FHD-PLI v1.0-MNasr", "https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh", os.path.join(picfold, "max001.png"), "سكين Luka-FHD-PLI v1.0 By Mohamed-Nasr"),
                   ("AglareFHD_6.2-pli-MNasr", "https://raw.githubusercontent.com/Ham-ahmed/118/refs/heads/main/installer.sh", os.path.join(picfold, "agl001.png"), "سكين Algare By Mohamed-Nasr"),
                   ("MaxyFHD_1.0-pli3.12.4-MNasr", "https://raw.githubusercontent.com/Ham-ahmed/Skins2024/main/1skins-maxy-fhd-pli_1.0_all.sh", os.path.join(picfold, "max001.png"), "سكين MaxyFHD By Mohamed-Nasr"),
                 ]
            },
            "openBH Skins": {
                "icon": os.path.join(picfold, "bh1.png"),
                "channels": [
                    ("MX_PrioFHD_Mod_H-Ahmed_New Skin", "https://raw.githubusercontent.com/Ham-ahmed/294/refs/heads/main/Mx-PrioFHD-Skin-Mod_H-Ahmed.sh", os.path.join(picfold, "pri001.png"), "سكين Mx prioFHD معدل من Hamdy-Ahmed"),
                    ("MX_Slim-Line_NP_Mod_H-A Skin", "https://gitlab.com/h-ahmed/Panel/-/raw/main/mx-slim/MX_Slim-Line_NP_Mod_H-Ahmed.sh", os.path.join(picfold, "606.png"), "سكين SlimFHD معدل من Hamdy-Ahmed"),
                    ("MX_LiveFHD_posterX-v4_New Skin", "https://raw.githubusercontent.com/Ham-ahmed/Skins2024/main/MX-LiveFHD-posterX_v4-mod-HAhmed.sh", os.path.join(picfold, "5430.png"), "سكين Mx LiveFHD معدل من Hamdy-Ahmed"),
                    ("MX_LiveFHD_posterX-v3_New Skin", "https://raw.githubusercontent.com/Ham-ahmed/BH-Skins/main/MX-LiveFHD-posterX-v3_mod-HAhmed.sh", os.path.join(picfold, "5430.png"), "سكين Mx LiveFHD معدل من Hamdy-Ahmed"),
                ]
            },
            "egami Skins": {
                "icon": os.path.join(picfold, "eg1.png"),
                "channels": [
                  ("RED-KNIGHT-FHD-v1.0-mod-H Skin", "https://raw.githubusercontent.com/Ham-ahmed/knight/refs/heads/main/RED-KNIGHT-FHD-v1.0-mod-HAhmed.sh", os.path.join(picfold, "kni001.png"), "سكين RedKnightFHD معدل من Hamdy-Ahmed"),
                  ("oDreamyFHD_mini-posterX-v2 Skin", "https://raw.githubusercontent.com/Ham-ahmed/oDreamy-mini/main/oDreamyFHD_mini-posterX-v2_Mod_HAhmed.sh", os.path.join(picfold, "odr001.png"), "سكين odreamyFHD Mini معدل من Hamdy-Ahmed"),
                  ("oDreamyFHD_mini-posterX Skin", "https://raw.githubusercontent.com/Ham-ahmed/Skins2024/main/oDreamyFHD_mini-posterX-Mod_HA.sh", os.path.join(picfold, "odr001.png"), "سكين odreamyFHD Mini معدل من Hamdy-Ahmed"),
                  ("AglareFHD_v.4.7 Skin", "https://gitlab.com/h-ahmed/Panel/-/raw/main/Aglaer/Aglare-FHD-4.7.sh", os.path.join(picfold, "agl001.png"), "سكين Artemis By Mohamed-Nasr"),
                  ("xDreamyFHD_v.3.8 Skin", "https://gitlab.com/h-ahmed/Panel/-/raw/main/xdreamy/skins-xDreamy-v3.8.sh", os.path.join(picfold, "xdr001.png"), "سكين Artemis By Mahamoud-Hussein"),
                  ("luka-fhd_1.5-FHD Skin", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/luka-fhd_1.0_egami.sh", os.path.join(picfold, "luk001.png"), "سكين Artemis By Mohamed-Nasr"),
                  ("luka-fhd_1.0-FHD Skin", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/luka-fhd_1.0_egami.sh", os.path.join(picfold, "luk001.png"), "سكين Artemis By Mohamed-Nasr"),
                ]
            },
            "openvix Skins": {
                "icon": os.path.join(picfold, "vi.png"),
                "channels": [
                  ("youVixFHD_v3-Skin-Mod_H-A Skin", "https://gitlab.com/h-ahmed/Panel/-/raw/main/youvix/youVixFHD_v3-Skin-Mod_H-Ahmed.sh", os.path.join(picfold, "yvi001.png"), "سكين youvixFHD معدل من Hamdy-Ahmed"),
                  ("YouViX_New-Skin_PosterX_4x1 Skin", "https://gitlab.com/h-ahmed/Panel/-/raw/main/youvix/skins-youVix-Mod_H-Ahmed.sh", os.path.join(picfold, "yov002.png"), "سكين youvixFHD معدل من Hamdy-Ahmed"),
                  ("YouViX_Skin_PosterX_4x1 Skin", "https://raw.githubusercontent.com/Ham-ahmed/Skin-py3-12-2/main/YouViX-Skin6_5_003-PosterX_4x1-Mod-HA.sh", os.path.join(picfold, "yov002.png"), "سكين youvixFHD معدل من Hamdy-Ahmed"),
                  ("YouViX_Skin_PosterX_4x1 Skin", "https://raw.githubusercontent.com/Ham-ahmed/Skins2024/main/YouViX-Skin_PosterX_4x1-Mod-HAhmed.sh", os.path.join(picfold, "yvi003.png"), "سكين youvixFHD معدل من Hamdy-Ahmed"),
                  ("AglareFHD_v.6.2-Atv-egami-spa Skin", "https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglareatv/installer.sh", os.path.join(picfold, "agl001.png"), "سكين Algare By Mohamed-Nasr"),
                  ("AglareFHD_v.5.3-Atv-egami-spa Skin", "https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglareatv/installer.sh", os.path.join(picfold, "agl001.png"), "سكين Algare By Mohamed-Nasr"),
                ]
            },
            "openspa Skins": {
                "icon": os.path.join(picfold, "spa.png"),
                "channels": [
                 ("estuaryFHD-v5_openspa_RED_MOD-HA_py3.12.9", "https://raw.githubusercontent.com/Ham-ahmed/openspa/refs/heads/main/esturyHD-Spa-v5_red-MOD_HA.sh", os.path.join(picfold, "est001.png"), "سكين estuaryFHD معدل من Hamdy-Ahmed"),
                 ("xDreamyFHD_v.5.2.1-M.Hussein", "https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين Xdreamr By Mahamoud-Hussein"),
                 ("E2-DarkOS_posterX-openvix py 3.12", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel/main/E2-DarkOS_posterX-Mod_HAhmed.sh", os.path.join(picfold, "Dr001.png"), "سكين E2 DarkosFHD معدل من Hamdy-Ahmed"),
                 ("premium-fhd-black-openvix py 3.12", "https://gitlab.com/eliesat/skins/-/raw/main/all/premium-fhd/premium-fhd-black.sh", os.path.join(picfold, "pre001.png"), "سكين premium By Mohamed-Nasr"),
                 ("estuaryFHD-posterX_MOD-HA_py3.12.4", "https://raw.githubusercontent.com/Ham-ahmed/openspa/main/estuaryHD_openspa-posterX-v.5-mod-HAhmed.sh", os.path.join(picfold, "est001.png"), "سكين estuaryFHD معدل من Hamdy-Ahmed"),
                 ("openplusFHD_posterX-v2-8.3.006-MOD-H-A", "https://raw.githubusercontent.com/Ham-ahmed/openspa/main/openplusFHD_posterX-v2_Mod-H-Ahmed.sh", os.path.join(picfold, "opl001.png"), "سكين openPluseFHD معدل من Hamdy-Ahmed"),
                 ("BlackSPAFHD_posterX-8.3.006-MOD-H-A", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel/main/BlackSPAFHD_posterX-Mod_HAhmed.sh", os.path.join(picfold, "bos001.png"), "سكين BlackSpaFHD معدل من Hamdy-Ahmed"),
                 ("openplusFHD_posterX-8.3.006-MOD-H-A", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel/main/openplusFHD_posterX-Mod_HAhmed.sh", os.path.join(picfold, "opl001.png"), "سكين openPluseFHD معدل من Hamdy-Ahmed"),
                ]
            },
            "pure2 Skins": {
                "icon": os.path.join(picfold, "pur.png"),
                "channels": [
                 ("esturyFHD-pure2-7.4-Mod-HA Skin", "https://raw.githubusercontent.com/Ham-ahmed/Skin-py3-12-2/main/estuaryfhd-posterX-mod3_H-Ahmed.sh", os.path.join(picfold, "est001.png"), "سكين estuaryFHD معدل من Hamdy-Ahmed"),
                 ]
            },
            "openHDF Skins": {
                "icon": os.path.join(picfold, "H-D.png"),
                "channels": [
                 ("XionFHD_Mod-HA Skin", "https://raw.githubusercontent.com/Ham-ahmed/XionFHD/main/XionHDF-posterX-v02_Mod_HAhmed.sh", os.path.join(picfold, "xio001.png"), "سكين XionFHD معدل من Hamdy-Ahmed"),
                 ]
            },
            "TeaBlue Skins": {
                "icon": os.path.join(picfold, "tm.png"),
                "channels": [
                  ("Gigabluepaxv4FHD_3x1-Mod-HA Skin", "https://raw.githubusercontent.com/Ham-ahmed/gigablue/refs/heads/main/GigabluePaxV4-Skin3x1_Mod-H-Ahmed.sh", os.path.join(picfold, "gig001.png"), "سكين Gigablue pax معدل من Hamdy-Ahmed"),
                  ("Gigabluepaxv4FHD_3x1-Mod-HA Skin", "https://raw.githubusercontent.com/Ham-ahmed/gigablue/refs/heads/main/GigabluePaxV4-Skin3x1_Mod-H-Ahmed.sh", os.path.join(picfold, "gig001.png"), "سكين Gigablue pax معدل من Hamdy-Ahmed"),
                  ]
            },
            "satdream Skins": {
                "icon": os.path.join(picfold, "sl.png"),
                "channels": [
                  ("SatDreamGrFHD-10py3.9.9.Mod-HA Skin", "https://raw.githubusercontent.com/Ham-ahmed/SatDreamGr/main/Satdreamgr-HDF-posterX-v01_Mod_HAhmed.sh", os.path.join(picfold, "std001.png"), "سكين SatDreamGrFHD معدل من Hamdy-Ahmed"),
                  ]
            },
            "ALL-IMAGES Skins": {
                "icon": os.path.join(picfold, "al.png"),
                "channels": [
                 ("Fury-FHD-V7.3_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V7.1_Skin", "https://raw.githubusercontent.com/Ham-ahmed/1003/refs/heads/main/furySkin_7-1.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V7.0_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V6.8_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V6.1_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V5.7_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V5.6_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V5.5_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("Fury-FHD-V5.4_Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين fury By Eslam-salama"),
                 ("XDREAMY-FHD_v6.1.0 Skin", "https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين xdreamy By Mahamoud-Hussein"),
                 ("XDREAMY-FHD_v6.0.0 Skin", "https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh", os.path.join(picfold, "xdr001.png"), "سكين xdreamy By Mahamoud-Hussein"),
                 ("FURY-FHD-4.6 Skin", "https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh", os.path.join(picfold, "fu001.png"), "سكين xdreamy By eslam salama"),
                 ("XDREAMY-FHD_5.9.9-r95 Skin", "https://raw.githubusercontent.com/Insprion80/Skins/refs/heads/main/xDreamy/XDREAMY_AiO.sh", os.path.join(picfold, "xdr001.png"), "سكين xdreamy By Mahamoud-Hussein"),
                 ("XDREAMY-FHD_5.9.4 Skin", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/installer-xdreamy.sh", os.path.join(picfold, "xdr001.png"), "سكين xdreamy By Mahamoud-Hussein"),
                ]
            }
        }

        self.names = list(self.skin_data.keys())
        self.pics = [data["icon"] for data in self.skin_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]
        self.descriptions = [data.get("description", "لا يوجد وصف متاح") for data in self.skin_data.values()]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.skin_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class FreePanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Free"
        self["info"].setText("اختر stalker مجاني للتثبيت...")

        self.free_data = {
             "28-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("28-xtreamity-playlists-19-04-2026", "https://raw.githubusercontent.com/Ham-ahmed/28s/refs/heads/main/28-xtreamity.sh", os.path.join(picfold, "fe000.png"), "New Stalkers By Hamdy-Ahmed"),
                    ("28-xklass-playlists-19-04-2026", "https://raw.githubusercontent.com/Ham-ahmed/28s/refs/heads/main/28-xklass.sh", os.path.join(picfold, "fe000.png"), "New Stalkers By Hamdy-Ahmed"),
                ]
            },
            "12-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("12-xtreamity-playlists-23-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/232/refs/heads/main/12-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("12-xklass-playlists-23-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/232/refs/heads/main/12-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "14-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("12-xtreamity-playlists-23-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/232/refs/heads/main/12-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("12-xklass-playlists-07-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/232/refs/heads/main/12-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("14-xtreamity-playlists-07-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/71/refs/heads/main/14-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("14-xklass-playlists-07-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/71/refs/heads/main/14-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "29-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("29-xtreamity-playlists-02-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/211/refs/heads/main/29-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("29-xklass-playlists-02-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/211/refs/heads/main/29-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "24-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("24-xtreamity-playlists-29-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2910/refs/heads/main/24-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("24-xklass-playlists-29-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2910/refs/heads/main/24-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "Estalker-portals": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("31-estalker-playlists_07-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/71/refs/heads/main/31-estalker.sh", os.path.join(picfold, "estk.png"), "Stalkers By Hamdy-Ahmed"),
                    ("41-estalker-playlists_22-12-2025", "https://raw.githubusercontent.com/Ham-ahmed/41-estalker/refs/heads/main/41-estalker.sh", os.path.join(picfold, "estk.png"), "Stalkers By Hamdy-Ahmed"),
                    ("34-estalker-playlists_29-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/2911/refs/heads/main/34-estalker.sh", os.path.join(picfold, "estk.png"), "Stalkers By Hamdy-Ahmed"),
                    ("24-estalker-playlists_22-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2210/refs/heads/main/24-estalker.sh", os.path.join(picfold, "estk.png"), "Stalkers By Hamdy-Ahmed"),
                    ("23-estalker-playlists_07-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/710/refs/heads/main/23-estalker.sh", os.path.join(picfold, "estk.png"), "Stalkers By Hamdy-Ahmed"),
                    ("18-estalker-playlists_06-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/610/refs/heads/main/18-estalker.sh", os.path.join(picfold, "estk.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "20-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("20-xtreamity-playlists-22-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2210/refs/heads/main/28-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("20-xklass-playlists-22-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2210/refs/heads/main/28-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "43-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("43-xklass-playlists-09-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/910/refs/heads/main/43-xklass.sh", os.path.join(picfold, "fe000.png"), "playlists By Hamdy-Ahmed"),
                    ("43-xtreamity-playlists-09-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/910/refs/heads/main/43-xtreamity.sh", os.path.join(picfold, "fe000.png"), "playlists By Hamdy-Ahmed"),
                ]
            },
            "36-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("36-xklass-playlists-07-08-2025", "https://raw.githubusercontent.com/Ham-ahmed/78/refs/heads/main/36-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("36-xtreamity-playlists-07-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/78/refs/heads/main/36-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "54-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("54-xtreamity-playlists-19-05-2025", "https://raw.githubusercontent.com/Ham-ahmed/195/refs/heads/main/54-xklass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("54-xklass-playlists-19-05-2025", "https://raw.githubusercontent.com/Ham-ahmed/195/refs/heads/main/54-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "67-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("67-xtreamity-playlists-21-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/214/refs/heads/main/67-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("67-xklass-playlists-21-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/214/refs/heads/main/67-xklass.shh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            },
            "23-stalker": {
                "icon": join(picfold, "fr.png"),
                "channels": [
                    ("23-xtreamity-playlists-30-03-2025", "https://raw.githubusercontent.com/Ham-ahmed/303/refs/heads/main/23-xtreamity.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                    ("23-xklass-playlists--30-03-2025", "https://raw.githubusercontent.com/Ham-ahmed/303/refs/heads/main/23-xclass.sh", os.path.join(picfold, "fe000.png"), "Stalkers By Hamdy-Ahmed"),
                ]
            }
        }

        self.names = list(self.free_data.keys())
        self.pics = [data["icon"] for data in self.free_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.free_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class MultibootPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Multiboot"
        self["info"].setText("اختر بلجن multiboot للتثبيت...")

        self.multiboot_data = {
            "MyPanel": {
                "icon": join(picfold, "pa.png"),
                "channels": [
                    ("install panel v6", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel-v6/refs/heads/main/New-panel_ajpanel-HA_v6.0.sh", os.path.join(picfold, "free_icon.png"), "Agpanel panel Desighn By Hamdy Ahmed"),
                ]
            },
            "Update the panel": {
                "icon": os.path.join(picfold, "up.png"),
                "channels": [
                   ("Update-My-panel", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel-v6/refs/heads/main/1New_update.sh", os.path.join(picfold, "uup.png"), "Upgrade Agpanel panel By Hamdy Ahmed"),
                ]
            }
        }

        self.names = list(self.multiboot_data.keys())
        self.pics = [data["icon"] for data in self.multiboot_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.multiboot_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class AjpanelPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Ajpanel"
        self["info"].setText("اختر خيار Ajpanel...")

        self.ajpanel_data = {
            "Ajpanel v10.0": {
                "icon": join(picfold, "aj.png"),
                "channels": [
		("ajpanel-v10.8.5", "https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
		("ajpanel-v10.8.3", "https://raw.githubusercontent.com/Ham-ahmed/155/refs/heads/main/ajpanel_v10.8.3.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.8.2", "https://raw.githubusercontent.com/Ham-ahmed/105/refs/heads/main/ajpanel_v10.8.2.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.8.1", "https://raw.githubusercontent.com/Ham-ahmed/154/refs/heads/main/ajpanel_v108.0.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.8.0", "https://raw.githubusercontent.com/Ham-ahmed/154/refs/heads/main/ajpanel_v10.8.1.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.7.1", "https://raw.githubusercontent.com/Ham-ahmed/93/refs/heads/main/ajpanel_v10.7.1_all.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.7.0", "https://raw.githubusercontent.com/Ham-ahmed/53/refs/heads/main/ajpanel_v10.7.0_all.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.6.0", "https://raw.githubusercontent.com/Ham-ahmed/122/refs/heads/main/ajpanel_v10.6.0.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.5.1", "https://raw.githubusercontent.com/Ham-ahmed/Ajpanel/refs/heads/main/plugin-ajpanel_v10.5.0.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.4", "https://raw.githubusercontent.com/biko-73/AjPanel/main/installer.sh", os.path.join(picfold, "ajj001.png")),
        ("ajpanel-v10.2.3", "https://raw.githubusercontent.com/Ham-ahmed/Ajpanel/refs/heads/main/plugin-ajpanel_v10.2.3.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.2.2", "https://raw.githubusercontent.com/Ham-ahmed/Ajpanel/refs/heads/main/plugin-ajpanel_v10.2.2.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.2.0", "https://raw.githubusercontent.com/Ham-ahmed/212/refs/heads/main/ajpanel_v10.2.0_all.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.1.0", "https://raw.githubusercontent.com/biko-73/AjPanel/main/installer.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v10.0.0", "https://raw.githubusercontent.com/biko-73/AjPanel/main/installer.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
                 ]
            },
            "Ajpanel v9.0": {
                "icon": os.path.join(picfold, "aj.png"),
                "channels": [
        ("ajpanel-v9.4.0", "https://raw.githubusercontent.com/Ham-ahmed/Ajpanel/main/plugin-extensions-ajpanel_v9.4.0.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v9.3.0", "https://raw.githubusercontent.com/Ham-ahmed/Ajpanel/main/plugin-extensions-ajpanel_v9.3.0_all.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v9.1.0", "https://raw.githubusercontent.com/Ham-ahmed/Ajpanel/main/plugin-extensions-ajpanel_v9.1.0_all.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
        ("ajpanel-v9.0.0", "https://raw.githubusercontent.com/Ham-ahmed/Ajpanel/main/plugin-extensions-ajpanel_v9.0.0_all.sh", os.path.join(picfold, "ajj001.png"), "مطور البلجن AMA-Jamry"),
                ]
            }
        }

        self.names = list(self.ajpanel_data.keys())
        self.pics = [data["icon"] for data in self.ajpanel_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.ajpanel_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class PluginsPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Plugins"
        self["info"].setText("اختر فئة البلجن...")

        self.plugins_data = {
            "Weather plugin": {
                "icon": join(picfold, "pll.png"),
                "channels": [
        ("foreca-one_1.0.1_New", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/foreca-one_1.0.1.sh", os.path.join(picfold, "oa00.png"), "متوافق مع كل صور بايثون 3"),
        ("oaweatheriet5_1.4_New", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/oaweatheriet5_1.4.sh", os.path.join(picfold, "oa00.png"), "متوافق مع كل صور بايثون 3"),
        ("foreca-one_1.0.1_New", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/foreca-one_1.0.1.sh", os.path.join(picfold, "oa00.png"), "متوافق مع كل صور بايثون 3"),
		("oaweather-4.0", "https://raw.githubusercontent.com/Ham-ahmed/177/refs/heads/main/oaweather_4.0.sh", os.path.join(picfold, "oa00.png"), "متوافق مع كل صور بايثون 3"),
        ("oaweather3.2.1", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/oaweather_3.2.1_all.sh", os.path.join(picfold, "oa00.png")),
        ("oaweather2.6", "https://raw.githubusercontent.com/Ham-ahmed/1New-P/main/oaweather.sh", os.path.join(picfold, "oa00.png")),
        ("weather-plugin-v2.1", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/weatherplugin_2.1_all.sh", os.path.join(picfold, "thw00.png")),
        ("weatherplugin", "https://raw.githubusercontent.com/Ham-ahmed/1New-P/main/weather_plugin.sh", os.path.join(picfold, "thw00.png")),
        ("TheWeather", "https://raw.githubusercontent.com/biko-73/TheWeather/main/installer.sh", os.path.join(picfold, "thw00.png"), "متوافق مع كل صور بايثون 3"),
        ("weatherplugin-py2-py3", "https://raw.githubusercontent.com/Ham-ahmed/Iptv-plugin/refs/heads/main/theweather-py2-py3_2.4_r1.sh", os.path.join(picfold, "thw00.png")),
        ("weatherplugin", "https://gitlab.com/eliesat/extensions/-/raw/main/weatherplugin/weatherplugin.sh", os.path.join(picfold, "thw00.png")),
        ("weatherplugin-vector", "https://gitlab.com/eliesat/extensions/-/raw/main/weatherplugin-vector/weatherplugin-vector.sh", os.path.join(picfold, "thw00.png")),
        ("theweather", "https://gitlab.com/eliesat/extensions/-/raw/main/theweather/theweather.sh", os.path.join(picfold, "thw00.png")),
             ]
        },
            "historyzap plugin": {
                "icon": os.path.join(picfold, "sl.png"),
                "channels": [
        ("historyzap_selector.v1.045_New", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/historyzap_1.0.45.sh", os.path.join(picfold, "op.png"), "متوافق مع كل صور بايثون 3"),
        ("historyzap_selector.v1.045", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/historyzap_1.0.45.sh", os.path.join(picfold, "op.png"), "متوافق مع كل صور بايثون 3"),
		("historyzap_selector.v1.45", "https://raw.githubusercontent.com/Ham-ahmed/207/refs/heads/main/historyzap_1.0.45.sh", os.path.join(picfold, "op.png"), "متوافق مع كل صور بايثون 3"),
        ("historyzap-1.0.44_py3.13_3.12", "https://raw.githubusercontent.com/Ham-ahmed/306/refs/heads/main/historyzap_1.0.44.sh", os.path.join(picfold, "op.png")),
        ("History_Zap_1.0.38-py3.12", "https://raw.githubusercontent.com/biko-73/History_Zap_Selector/main/installer.sh", os.path.join(picfold, "op.png")),
                     ]
        },
             "GlobalTranslatePro plugin": {
                "icon": os.path.join(picfold, "sl.png"),
                "channels": [
        ("GlobalTranslatePro-Grid_v5.3_22-04-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/Grid/refs/heads/main/GlobalTranslatePro.sh", os.path.join(picfold, "nnn0.png"), "Py3.14.4 openatv8.0-openpli-Gcc-15.2 By Hamdy Ahmed Developer iptv and Live channel الترجمة الفورية"),
        ("GlobalTranslatePro-List_v5.3_22-04-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/list/refs/heads/main/GlobalTranslatePro.sh", os.path.join(picfold, "nnn0.png"), "Py3.14.4 openatv8.0-openpli-Gcc-15.2 By Hamdy Ahmed Developer الترجمة الفورية"),
        ("GlobalTranslatePro-Grid_v5.3_puure2_22-04-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/pure2/refs/heads/main/GlobalTranslatePro.sh", os.path.join(picfold, "nnn0.png"), "pure2_13.13.11 By Hamdy Ahmed Developer iptv and Live channel الترجمة الفورية"),
        ("GlobalTranslatePro-Grid_v5.4_25-04-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/5.4/refs/heads/main/GlobalTranslatePro.sh", os.path.join(picfold, "nnn0.png"), "Py3.13.11-12 openatv7.6_openHB5.6.006-7_egimi11_Spa8.5.002 By Hamdy Ahmed Developer iptv and Live channel الترجمة الفورية"),
        ("GlobalTranslatePro-v5.0_09-04-2026_plugin", "https://raw.githubusercontent.com/Ham-ahmed/Global/refs/heads/main/GlobalTranslatePro.sh", os.path.join(picfold, "nnn0.png"), "Py3.13.4-12 openBH vix pure2 By Hamdy Ahmed Developer iptv and Live channel الترجمة الفورية"),
        ("GlobalTranslatePro-v5.1_09-04-2026_plugin", "https://raw.githubusercontent.com/Ham-ahmed/GlobalA/refs/heads/main/GlobalTranslatePro.sh", os.path.join(picfold, "nnn0.png"), "py3.13.4-12 openAtv egami11 opnspa By Hamdy Ahmed Developer الترجمة الفورية"),
        ("GlobalTranslatePro-v5.2_09-04-2026_plugin", "https://raw.githubusercontent.com/Ham-ahmed/Globalp/refs/heads/main/GlobalTranslatePro.sh", os.path.join(picfold, "nnn0.png"), "py3.14.3 openAtv openpli Gcc 15.2 By Hamdy Ahmed Developer الترجمة الفورية"),
                     ]
        },
             "TranslateAI plugin": {
                "icon": os.path.join(picfold, "sl.png"),
                "channels": [
        ("TranslatorAI-v3.1_28-03-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/AI/refs/heads/main/TranslatorAI-v3.1.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer iptv and Live channel الترجمة الفورية"),
        ("TranslatorProAI-v3.0_20-03-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranAI/refs/heads/main/TranslatorProAI-v3.0.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("AITranslates_v2.7-07-03-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/703/refs/heads/main/AiTranslate-2.7_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer"),
        ("AITranslatesS_Shadow_v2.8-07-03-2026_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/0703/refs/heads/main/AiTranslateS-2.8_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
		("TranslateAI_v6.6_17-py3.13_01-2026-New_plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAI-6.6_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("TranslateAI_v6.3_py3.13_14-01-2026_plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAI-6.3_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("TranslateAI_v6.2-py3.13__08-01-2026-plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAI-6.2_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("TranslateAI_v6.6_plugin-py3.12_18-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAI-6.6_py3-12.sh", os.path.join(picfold, "nnn0.png"), "py3.12_Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("TranslateAIEpg-08-01-2026-New_plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAIEpg_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer ترجمة الدليل الاليكتروني للقنوات"),
        ("TranslateAI_v6.1_py3.13_04-01-2026_plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAI-6.1_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("TranslateAI_v5.9-py3.13_01-01-2026-plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAI-5.9_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("TranslateAI_v5.8_py3.13_30-12-2025-plugin", "https://raw.githubusercontent.com/Ham-ahmed/TranslateAI/refs/heads/main/TranslateAI_plugin.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
        ("AISubtitles_v2.2-24-12-2025_New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2.2/refs/heads/main/AISubtitles_v2.2.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer"),
        ("AISubtitles_v1.0-plugin", "https://raw.githubusercontent.com/Ham-ahmed/24/refs/heads/main/AISubtitles_v1.0.sh", os.path.join(picfold, "nnn0.png"), "Edit By Hamdy Ahmed Developer الترجمة الفورية"),
                     ]
        },
            "New plugin": {
                "icon": os.path.join(picfold, "sl.png"),
                "channels": [
        ("FuryBiss-v4.0-New-plugin", "https://raw.githubusercontent.com/islam-2412/FuryBiss/main/fury/installer.sh", os.path.join(picfold, "nnn0.png"), "By MohamedOS Developer يعمل عبى كل صور بايثون 3"),
        ("FuryBiss-plugin", "https://raw.githubusercontent.com/islam-2412/FuryBiss/refs/heads/main/fury/installer.sh", os.path.join(picfold, "nnn0.png"), "By MohamedOS Developer يعمل عبى كل صور بايثون 3"),
        ("PulseSoftcam_Updater-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/21F/refs/heads/main/PulseSoftcam_Updater.sh", os.path.join(picfold, "nnn0.png"), "By MohamedOS Developer يعمل عبى كل صور بايثون 3"),
        ("UniversalCamConfig-2.4-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/Universal/refs/heads/main/plugin_manager.sh", os.path.join(picfold, "nnn0.png"), "By Hamdy Ahmed Developer يعمل عبى كل صور بايثون 3"),
        ("e2Bisskeyseditor-2.0-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/1812/refs/heads/main/E2BissKeyEditor-2.0.sh", os.path.join(picfold, "nnn0.png"), "By ismail Saidi Developer يعمل عبى كل صور بايثون 3"),
        ("buttonpatcher_1.0-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/152/refs/heads/main/buttonpatcher_1.0.sh", os.path.join(picfold, "nnn0.png"), "D.M.Nasr Developer يعمل عبى كل صور بايثون 3"),
        ("ipstreamer_1.00-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/152/refs/heads/main/ipstreamer_1.00.sh", os.path.join(picfold, "nnn0.png"), "D.M.Nasr Developer يعمل عبى كل صور بايثون 3"),
        ("dreamosatxsignal_2.0-plugin", "https://raw.githubusercontent.com/Ham-ahmed/1303/refs/heads/main/dreamosatxsignal_2.0.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("dreamosatxline_1.0-plugin", "https://raw.githubusercontent.com/Ham-ahmed/1303/refs/heads/main/dreamosatxline_1.0.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("mixaudio-1.2_arm-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/mixaudio-1.2_arm.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("simplysports_4.1-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/simplysports_4.1.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("xmlupdatebyiet5_1.2-plugin", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/xmlupdatebyiet5_1.2.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("e2Bisskeyseditor-1.0-plugin", "https://raw.githubusercontent.com/Ham-ahmed/612/refs/heads/main/e2Bisskeyseditor-1.0.sh", os.path.join(picfold, "nnn0.png"), "By ismail Saidi Developer يعمل عبى كل صور بايثون 3"),
        ("cutsclear_1.2-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2802/refs/heads/main/cutsclear_1.2.sh", os.path.join(picfold, "nnn0.png"), "Two safe ways to clean up unnecessary .cuts files py 2.7 3.12"),
        ("oscamstatus_7.0-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/oscamstatus_7.00.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("oscamstatus_6.97-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2112/refs/heads/main/oscamstatus_6.97.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("CiefpSettingsT2miAbertis-New-plugin", "https://raw.githubusercontent.com/ciefp/CiefpSettingsT2miAbertis/main/installer.sh", os.path.join(picfold, "nnn0.png"), "By Ciefp Developer يعمل عبى كل صور بايثون 3"),
        ("CiefpTMDBSearch v1.9-New-plugin", "https://raw.githubusercontent.com/ciefp/CiefpTMDBSearch/main/installer.sh", os.path.join(picfold, "nnn0.png"), "By Ciefp Developer يعمل عبى كل صور بايثون 3"),
        ("wifimanager_1.1-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2111/refs/heads/main/wifimanager_1.1.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("wifimanager_1.0-plugin", "https://raw.githubusercontent.com/Ham-ahmed/1711/refs/heads/main/wifimanager_1.0.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("OrangeAudio-New-plugin", "https://raw.githubusercontent.com/popking159/OrangeAudio/refs/heads/main/installer.sh", os.path.join(picfold, "nnn0.png"), "by M.Nasr-يعمل عبى كل صور بايثون 3"),
        ("crashlogviewer_1.8-plugin", "https://raw.githubusercontent.com/Ham-ahmed/21F/refs/heads/main/crashlogviewer_1.8.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("crashlogviewer_1.7-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/1912/refs/heads/main/crashlogviewer_1.7.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("crashlogviewer_1.6-plugin", "https://raw.githubusercontent.com/Ham-ahmed/611/refs/heads/main/crashlogviewer_1.6.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("simple-zoom-panel_2.3.4-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/simple-zoom-panel_2.3.4.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("simple-zoom-panel_1.2.3.1-plugin", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/simple-zoom-panel_2.3.1.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("simple-zoom-panel_1.2.3-plugin", "https://raw.githubusercontent.com/Ham-ahmed/2910/refs/heads/main/simple-zoom-panel_2.3.0.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("simple-zoom-panel_2.3.0-plugin", "https://raw.githubusercontent.com/Ham-ahmed/310/refs/heads/main/ServiceScanUpdates_1.3.2.sh", os.path.join(picfold, "nnn0.png")),
        ("simple-zoom-panel_2.2.8-plugin", "https://raw.githubusercontent.com/Ham-ahmed/310/refs/heads/main/ServiceScanUpdates_1.3.2.sh", os.path.join(picfold, "nnn0.png")),
        ("FeedCatcher 1.1-New-plugin", "https://raw.githubusercontent.com/Bahaa-E2/FeedCatcher/refs/heads/main/FeedCatcher.sh", os.path.join(picfold, "nnn0.png")),
        ("quicksignalmodedbyiet5_2.2-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/211/refs/heads/main/quicksignalmodedbyiet5_2.2.sh", os.path.join(picfold, "nnn0.png"), "Plugin By developer iet5"),
        ("raedquicksignal_18.0-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/210/refs/heads/main/raedquicksignal_18.0.sh", os.path.join(picfold, "nnn0.png"), "Plugin By developer BO-hlala"),
        ("auto dcw key add v1.0.6-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/auto-dcw-key-add_v1.0.6.sh", os.path.join(picfold, "nnn0.png"), "يعمل عبى كل صور بايثون 3"),
        ("footonsat_4.2-New-plugin_13-11-2025", "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh", os.path.join(picfold, "nnn0.png")),
        ("footonsat_4.1-plugin_06-11-2025", "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh", os.path.join(picfold, "nnn0.png")),
        ("footonsat_3.7-plugin_02-11-2025", "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh", os.path.join(picfold, "nnn0.png")),
        ("footonsat_3.4-plugin_12-10-2025", "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh", os.path.join(picfold, "nnn0.png")),
        ("footonsat_3.2-plugin_12-10-2025", "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh", os.path.join(picfold, "nnn0.png")),
        ("footonsat_2.2-plugin", "https://raw.githubusercontent.com/Ham-ahmed/110/refs/heads/main/footonsat_2.2.sh", os.path.join(picfold, "nnn0.png")),
        ("satelliweblivefeeds2.1_py3.12-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/110/refs/heads/main/satelliweblivefeeds2.1_py3.12.sh", os.path.join(picfold, "nnn0.png")),
        ("satelliweblivefeeds2.1_py3.13-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/110/refs/heads/main/satelliweblivefeeds2.1_py3.13.sh", os.path.join(picfold, "nnn0.png")),
        ("temperaturmonitor_2.0-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/110/refs/heads/main/temperaturmonitor_2.0.sh", os.path.join(picfold, "nnn0.png")),
        ("keyadder plugin v9.0-New-plugin", "https://raw.githubusercontent.com/fairbird/KeyAdder/main/installer.sh", os.path.join(picfold, "nnn0.png")),
        ("backupsuite_3.0_r9-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/207/refs/heads/main/backupsuite_3.0-r9.sh", os.path.join(picfold, "nnn0.png")),
        ("enigma2readeradder-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/177/refs/heads/main/enigma2readeradder.sh", os.path.join(picfold, "nnn0.png")),
        ("multibootselector_1.16-r0-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/28-8/refs/heads/main/multibootselector_1.16-r0.sh", os.path.join(picfold, "nnn0.png")),
        ("servicescanupdates-v3.2-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/198/refs/heads/main/ervicescanupdates_v3.2.sh", os.path.join(picfold, "nnn0.png")),
        ("FeedCatcher.sh.v1.1-New-plugin.", "https://raw.githubusercontent.com/Ham-ahmed/118/refs/heads/main/FeedCatcher.sh", os.path.join(picfold, "nnn0.png")),
        ("auto-dcw-key-add v1.0.8-New-plugin", "https://raw.githubusercontent.com/Ham-ahmed/28-8/refs/heads/main/auto-dcw-key-add_v1.0.8.sh", os.path.join(picfold, "nnn0.png")),
        ("raedquicksignal_18.2-By-BO-hlala-New", "https://raw.githubusercontent.com/fairbird/RaedQuickSignal/main/installer.sh", os.path.join(picfold, "nnn0.png")),
        ("raedquicksignal_18.0-By-BO-hlala-New", "https://raw.githubusercontent.com/Ham-ahmed/28-8/refs/heads/main/raedquicksignal_18.0-By-BO-hlala.sh", os.path.join(picfold, "nnn0.png")),
        ("oscamstatus..v6.94-New.plugin", "https://raw.githubusercontent.com/Ham-ahmed/28/refs/heads/main/oscamstatus_6.94.sh", os.path.join(picfold, "nnn0.png")),
                       ]
            },
            "Other plugin": {
                "icon": os.path.join(picfold, "op.png"),
                "channels": [
        ("opencamview_1.3_New", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/opencamview_1.3.sh", os.path.join(picfold, "op.png")),
        ("wireguard-vpn-15.9_New", "https://raw.githubusercontent.com/Ham-ahmed/110/refs/heads/main/wireguard-vpn_15.9.sh", os.path.join(picfold, "op.png")),
        ("wireguard-vpn-13.9", "https://raw.githubusercontent.com/Ham-ahmed/2412/refs/heads/main/wireguard-vpn_13.9.sh", os.path.join(picfold, "op.png")),
        ("wireguard-vpn-13.0", "https://raw.githubusercontent.com/Ham-ahmed/212/refs/heads/main/wireguard-vpn_13.0_all.sh", os.path.join(picfold, "op.png")),
        ("youtube-py3-git1292", "https://raw.githubusercontent.com/Ham-ahmed/93/refs/heads/main/youtube_py3-1292.sh", os.path.join(picfold, "yo00.png")),
        ("youtube-py3-git240", "https://raw.githubusercontent.com/Ham-ahmed/11863/refs/heads/main/youtube_py3-git1240.sh", os.path.join(picfold, "yo00.png")),
        ("youtube-py3-git1231", "https://raw.githubusercontent.com/Ham-ahmed/plugins3/refs/heads/main/youtube_py3-git1231.sh", os.path.join(picfold, "yo00.png")),
        ("footonsat-4.4_New", "https://raw.githubusercontent.com/Ham-ahmed/Iptv-plugin/refs/heads/main/footonsat_1.9-r0.sh", os.path.join(picfold, "foot.png")),
        ("footonsat-", "https://gitlab.com/eliesat/extensions/-/raw/main/footonsat/footonsat.sh", os.path.join(picfold, "foot.png")),
        ("footonsat-1.6.r0", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/footonsat_1.9-r0_all.sh", os.path.join(picfold, "foot.png")),
        ("bootlogoswapper-v2.4", "https://raw.githubusercontent.com/Ham-ahmed/plugins3/refs/heads/main/bootlogoswapper_v2.4.sh", os.path.join(picfold, "op.png")),
        ("crashlogviewer-1.5", "https://raw.githubusercontent.com/Ham-ahmed/plugins3/refs/heads/main/crashlogviewer_1.5.sh", os.path.join(picfold, "op.png")),
        ("crashlogviewer-1.3", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/crashlogviewer_1.3_all.sh", os.path.join(picfold, "op.png")),
        ("filecommander-2024", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/filecommander_mod_2024_by_lululla_all.sh", os.path.join(picfold, "op.png")),
        ("alternativesoftcammanager", "https://gitlab.com/eliesat/extensions/-/raw/main/alternativesoftcammanager/alternativesoftcammanager.sh", os.path.join(picfold, "op.png")),
        ("athantimes", "https://gitlab.com/eliesat/extensions/-/raw/main/athantimes/athantimes.sh", os.path.join(picfold, "op.png")),
        ("bissfeedautokey", "https://gitlab.com/eliesat/extensions/-/raw/main/bissfeedautokey/bissfeedautokey.sh", os.path.join(picfold, "op.png")),
        ("bitrate2.0", "https://gitlab.com/eliesat/extensions/-/raw/main/bitrate/bitrate.sh", os.path.join(picfold, "op.png")),
        ("bouquetmakerxtream", "https://gitlab.com/eliesat/extensions/-/raw/main/bouquetmakerxtream/bouquetmakerxtream.sh", os.path.join(picfold, "op.png")),
        ("cacheflush", "https://gitlab.com/eliesat/extensions/-/raw/main/cacheflush/cacheflush.sh", os.path.join(picfold, "op.png")),
        ("crondmanager", "https://gitlab.com/eliesat/extensions/-/raw/main/crondmanager/crondmanager.sh", os.path.join(picfold, "op.png")),
        ("easy-cccam", "https://gitlab.com/eliesat/extensions/-/raw/main/easy-cccam/easy-cccam.sh", os.path.join(picfold, "op.png")),
        ("epggrabber", "https://gitlab.com/eliesat/extensions/-/raw/main/epggrabber/epggrabber.sh", os.path.join(picfold, "op.png")),
        ("feedsfinder", "https://gitlab.com/eliesat/extensions/-/raw/main/feedsfinder/feedsfinder.sh", os.path.join(picfold, "op.png")),
        ("freeserver", "https://gitlab.com/eliesat/extensions/-/raw/main/freeserver/freeserver.sh", os.path.join(picfold, "op.png")),
        ("internet-speed-test", "https://gitlab.com/eliesat/extensions/-/raw/main/internetspeedtest/internet-speed-test.sh", os.path.join(picfold, "op.png")),
        ("ipaudio-6.8", "https://gitlab.com/eliesat/extensions/-/raw/main/ipaudio/ipaudio.sh", os.path.join(picfold, "op.png")),
        ("ipaudiopro-1.1-py-3.9-3.11", "https://gitlab.com/eliesat/extensions/-/raw/main/ipaudiopro/ipaudiopro.sh", os.path.join(picfold, "op.png")),
        ("ipchecker", "https://gitlab.com/eliesat/extensions/-/raw/main/ipchecker/ipchecker.sh", os.path.join(picfold, "op.png")),
        ("acherone New plugin v1.3", "https://raw.githubusercontent.com/Ham-ahmed/105/refs/heads/main/acherone_1.3.sh", os.path.join(picfold, "op.png")),
        ("simple zoom panel 2.2.7", "https://raw.githubusercontent.com/Ham-ahmed/28/refs/heads/main/simple-zoom-panel_2.2.7.sh", os.path.join(picfold, "op.png")),
        ("wireguard-vpn15.1-3.12.24-02-2025", "https://raw.githubusercontent.com/Ham-ahmed/242/refs/heads/main/wireguard-vpn_15.1_3.12.sh", os.path.join(picfold, "op.png")),
        ("wireguard-vpn15.1-3.13.24-02-2025", "https://raw.githubusercontent.com/Ham-ahmed/242/refs/heads/main/wireguard-vpn_15.1_3.13.sh", os.path.join(picfold, "op.png")),
        ("setpicon_v3.0-py3", "https://raw.githubusercontent.com/Ham-ahmed/133/refs/heads/main/setpicon_v3.0.sh", os.path.join(picfold, "op.png")),
        ("youtube-1-ffmpeg_177_armv7ahf.py3..", "https://raw.githubusercontent.com/Ham-ahmed/233/refs/heads/main/ffmpeg_177_armv7ahf.sh", os.path.join(picfold, "yo00.png")),
        ("youtube-2.exteplayer3_177_armv7ahf.py3", "https://raw.githubusercontent.com/Ham-ahmed/233/refs/heads/main/exteplayer3_177_armv7ahf.sh", os.path.join(picfold, "yo00.png")),
                 ]
             },
            "MultiBoot plugin": {
                "icon": os.path.join(picfold, "mul.png"),
                "channels": [
		("opdboot_1.0-Multiboot_py3", "https://raw.githubusercontent.com/Ham-ahmed/2910/refs/heads/main/opdboot_1.0-git4-61e13a5.sh", os.path.join(picfold, "mul.png"), "متوافق مع كل صور بايثون 3"),
                         ]
             },
            "Panels New": {
                "icon": os.path.join(picfold, "mul.png"),
                "channels": [
        ("panelaio_11.0-19-04-2026", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/panelaio_11.0.sh", os.path.join(picfold, "mul.png"), "متوافق مع كل صور بايثون 3"),
        ("canpanel_1.8.4 10-04-2026", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/canpanel_py3_1.8.4.sh", os.path.join(picfold, "mul.png"), "متوافق مع كل صور بايثون 3"),
        ("panelaio_9.7_New_03-04-2026", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/panelaio_9.7.sh", os.path.join(picfold, "othe.png")),
        ("panelaio_New_9.1.1_24-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/panelaio_9.1.1.sh", os.path.join(picfold, "othe.png")),
		("panel_aio_9.0 panel 01-12-2026", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/panel_aio_9.0.sh", os.path.join(picfold, "mul.png"), "متوافق مع كل صور بايثون 3"),
		("boxtools_1.8 panel New_01-12-2026", "https://raw.githubusercontent.com/Ham-ahmed/1202/refs/heads/main/boxtools_1.8.sh", os.path.join(picfold, "mul.png"), "متوافق مع كل صور بايثون 3"),
        ("canpanel_1.7.1 New_24-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/canpanel_1.7.1.sh", os.path.join(picfold, "mul.png"), "متوافق مع كل صور بايثون 3"),
        ("canpanel_1.6.1 01-12-2026", "https://raw.githubusercontent.com/Ham-ahmed/1202/refs/heads/main/canpanel_1.6.1.sh", os.path.join(picfold, "mul.png"), "متوافق مع كل صور بايثون 3"),
                ]
            }
        }

        self.names = list(self.plugins_data.keys())
        self.pics = [data["icon"] for data in self.plugins_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.plugins_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class CamEmuPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Cam-Emu"
        self["info"].setText("اختر محاكي CAM للتثبيت...")

        self.camemu_data = {
            "Ncam emu": {
                "icon": os.path.join(picfold, "ncm.png"),
                "channels": [
                    ("Ncam-emu_v15.7-r0.New-fairman", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/ncam_V15.7-r0.sh", os.path.join(picfold, "ncm.png"), "المطور - fairman"),
                    ("Ncam-emu_v15.6-r0.New-fairman", "https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh", os.path.join(picfold, "ncm.png"), "المطور - fairman"),
                    ("Ncam-emu_v15.4-r0.-fairman", "https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh", os.path.join(picfold, "ncm.png"), "المطور - fairman"),
                    ("Ncam-emu_v15.2-r0-fairman", "https://raw.githubusercontent.com/Ham-ahmed/2412/main/ncam_15.2-r0_all.sh", os.path.join(picfold, "ncm.png"), "المطور - fairman"),
                    ("Ncam-emu_v15.1-r0-fairman", "https://raw.githubusercontent.com/Ham-ahmed/softcam-emu/refs/heads/main/ncam_15.1-r0_all.sh", os.path.join(picfold, "ncm.png"), "المطور - fairman"),
            ]
        },
            "Oscam emu": {
                "icon": os.path.join(picfold, "osc.png"),
                "channels": [
                   ("oscam-emu_11950-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/oscam_11950-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam-emu_11946-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/oscam_11946-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam-emu_11945-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/oscam_11945-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam-emu_11943-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/1202/refs/heads/main/oscam_11943-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam-emu_11942-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/0102/refs/heads/main/oscam_11942-emu-r803.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
		           ("oscam-emu_11936-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/221/refs/heads/main/oscam_11936-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
		           ("oscam-emu_11868-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/22/refs/heads/main/oscam_11868-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
	               ("oscam-emu_11870-802-audi06-19", "https://raw.githubusercontent.com/Ham-ahmed/43/refs/heads/main/oscam-11870-emu-802-audi06_19.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam-emu_11866-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/141/refs/heads/main/oscam_11866-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
		           ("oscam-emu_11865-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/2125/refs/heads/main/oscam_11865-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
		           ("oscam-emu_11884-802-audi06-19", "https://raw.githubusercontent.com/Ham-ahmed/105/refs/heads/main/oscam-11884-emu-802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam-emu_11863-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/11863/refs/heads/main/oscam_11863-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
	           	   ("oscam-emu_11862-802-audi06-19", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/oscam-emu_11862-802-arm-mips_audi06-19.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam-emu_11860-.mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/oscam11860/refs/heads/main/oscam_11860-emu-r802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
                   ("oscam--11884-emu-802-", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/oscam-all-images_11884-emu-802.sh", os.path.join(picfold, "oss0.png"), "المطور - Mohamed-OS"),
            ]
        },
                   "powercam emu": {
                "icon": os.path.join(picfold, "pow.png"),
                "channels": [
                  ("power-11950-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/powercam-oscam_11950-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
                  ("power-11946-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/powercam-oscam_11946-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
                  ("power-11945-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/powercam-oscam_11945-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
                  ("power-11943-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/1202/refs/heads/main/powercam-oscam_11943-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
                  ("power-11942-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/0102/refs/heads/main/powercam-oscam_11942-r803.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
                  ("power-11936-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/221/refs/heads/main/powercam-oscam_11936-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
                  ("power-11868-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/22/refs/heads/main/powercam-oscam_11868-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
                  ("power-11866-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/141/refs/heads/main/powercam-oscam_11866-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
	              ("power-11865-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/2125/refs/heads/main/powercam-oscam_11865-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
		          ("power-11863-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/11863/refs/heads/main/powercam-oscam_11863-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
	              ("power-11860-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/oscam11860/refs/heads/main/powercam-oscam_11860-emu-r802.sh", os.path.join(picfold, "pow.png"), "المطور - Mohamed-OS"),
            ]
        },
                   "supcam emu": {
                "icon": os.path.join(picfold, "sup.png"),
                "channels": [
                 ("supcam-11950-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/supcam--oscam_11950-r802", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
                 ("supcam-11946-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/supcam--oscam_11946-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
                 ("supcam-11945-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/supcam--oscam_11945-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
                 ("supcam-11943-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/1202/refs/heads/main/supcamoscam_11943-emu-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
                 ("supcam-11942-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/0102/refs/heads/main/supcam-oscam_11942-r803.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
                 ("supcam-11936-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/221/refs/heads/main/supcam-oscam_11936-emu-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
		         ("supcam-11868-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/22/refs/heads/main/supcam-oscam_11868-emu-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
		         ("supcam-11865-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/2125/refs/heads/main/supcam-oscam_11865-emu-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
	             ("supcam-11863-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/11863/refs/heads/main/supcam-oscam_11863-emu-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
	             ("supcam-11866-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/141/refs/heads/main/supcam-oscam_11866-emu-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
	             ("supcam-11860-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/oscam11860/refs/heads/main/supcam-oscam_11860-emu-r802.sh", os.path.join(picfold, "sup.png"), "المطور - Mohamed-OS"),
            ]
        },
                   "ultracam emu": {
                "icon": os.path.join(picfold, "ult.png"),
                "channels": [
                ("ultaracam-11950-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/ultracam--oscam_11950-r802", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
                ("ultaracam-11946-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/ultracam--oscam_11946-r802", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
                ("ultaracam-11945-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/ultracam--oscam_11945-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
                ("ultaracam-11943-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/1202/refs/heads/main/ultracamoscam_11943-emu-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
                ("ultaracam-11942-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/0102/refs/heads/main/ultracam-oscam_11942-r803.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
                ("ultaracam-11936-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/221/refs/heads/main/ultracam-oscam_11936-emu-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
                ("ultaracam-11868-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/22/refs/heads/main/ultracam-oscam_11868-emu-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
		        ("ultaracam-11865-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/2125/refs/heads/main/ultracam-oscam_11865-emu-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
	            ("ultaracam-11863-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/11863/refs/heads/main/ultracam-oscam_11863-emu-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
		        ("ultaracam-11866-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/141/refs/heads/main/ultracam-oscam_11866-emu-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
	        	("ultaracam-11860-mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/oscam11860/refs/heads/main/ultracam-oscam_11860-emu-r802.sh", os.path.join(picfold, "ult.png"), "المطور - Mohamed-OS"),
            ]
        },
                   "gosatplus emu": {
                "icon": os.path.join(picfold, "gos.png"),
                "channels": [
                ("gosatplus-oscam_11950_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/gosatplus--oscam_11950-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11946_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/gosatplus--oscam_11946-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11945_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/gosatplus--oscam_11945-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11943_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/1202/refs/heads/main/gosatplusoscam_11943-emu-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11942_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/0102/refs/heads/main/gosatplus-oscam_11942-r803.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11936_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/221/refs/heads/main/gosatplus-oscam_11936-emu-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11868_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/22/refs/heads/main/gosatplus-oscam_11868-emu-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11866_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/141/refs/heads/main/gosatplus-oscam_11866-emu-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam11865..mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/2125/refs/heads/main/gosatplus-oscam_11865-emu-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11863_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/11863/refs/heads/main/gosatplus-oscam_11863-emu-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ("gosatplus-oscam_11860_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/oscam11860/refs/heads/main/gosatplus-oscam_11860-emu-r802.sh", os.path.join(picfold, "gos.png"), "المطور - Mohamed-OS"),
                ]
            }
        }

        self.names = list(self.camemu_data.keys())
        self.pics = [data["icon"] for data in self.camemu_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.camemu_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class BackupPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Backup"
        self["info"].setText("اختر نسخة احتياطية للاستعادة...")

        self.backup_data = {
            "All Tools": {
                "icon": os.path.join(picfold, "Bb.png"),
                "channels": [
                    ("all-plugins_2.0-Script_py3.14.3", "https://gitlab.com/h-ahmed/Panel/-/raw/main/bootlogo/314/all-plugins_2.0.sh", os.path.join(picfold, "Bb.png"), " Hamdy-Ahmed Script Contains py 3.14.3-AJPanel-ArabicSavior-Bitrate-EPGGrabber-EPGImport.."),
                    ("all-plugins_1.0-Script_3.13.4-12", "https://raw.githubusercontent.com/Ham-ahmed/201/refs/heads/main/all-plugins_1.0.sh", os.path.join(picfold, "Bb.png"), " Hamdy-Ahmed Script Contains py 3.13.4-12-AJPanel-ArabicSavior-Bitrate-EPGGrabber-EPGImport.."),
                    ("ajpanel-v10.8.6", "https://raw.githubusercontent.com/Ham-ahmed/155/main/ajpanel_v10.8.4.sh", os.path.join(picfold, "Bb.png")),
                    ("ArabicSavior-For All", "https://raw.githubusercontent.com/fairbird/ArabicSavior/main/installer.sh", os.path.join(picfold, "Bb.png")),
                    ("EpgGrabber-24.8-All", "https://raw.githubusercontent.com/ziko-ZR1/Epg-plugin/master/Download/installer.sh", os.path.join(picfold, "Bb.png")),
                    ("EpgGrabber-23.5-All", "https://raw.githubusercontent.com/Ham-ahmed/EPG/main/epg-plugin-master-v23.5.sh", os.path.join(picfold, "Bb.png")),
                    ("SubsSupport v1.8.0 r03-D.Mnasr", "https://github.com/popking159/ssupport/raw/main/subssupport-install.sh", os.path.join(picfold, "Bb.png")),
                    ("subssupport-v1.7.0-r29-D.Mnasr", "https://raw.githubusercontent.com/popking159/ssupport/main/subssupport-install.shoplus-py3.11_4.1-r0_all.sh", os.path.join(picfold, "Bb.png")),
                    ("subssupport-v1.7.0-r7mora-Mnasr", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/subssupport-install.sh", os.path.join(picfold, "Bb.png")),
                    ("subssupport-v1.7.0 r5mora-Mnasr", "https://raw.githubusercontent.com/popking159/ssupport/main/subssupport-install.sh", os.path.join(picfold, "Bb.png")),
                    ("subssupport-By_Mora Hosny", "https://raw.githubusercontent.com/popking159/ssupport/main/subssupport-install.sh", os.path.join(picfold, "Bb.png")),
                    ("xtraevent6.892", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/xtraevent_6.892.sh", os.path.join(picfold, "Bb.png")),
                    ("xtraevent6.891", "https://raw.githubusercontent.com/Ham-ahmed/611/refs/heads/main/xtraevent_6.891.sh", os.path.join(picfold, "Bb.png")),
                    ("xtraevent6.8", "https://raw.githubusercontent.com/Ham-ahmed/283/main/xtraevent_6.820.sh", os.path.join(picfold, "Bb.png")),
                    ("xtraevent5.3", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel/main/xtraevent-5.3.sh", os.path.join(picfold, "Bb.png")),
                    ("Ncam-emu-v15.6r0", "https://raw.githubusercontent.com/Ham-ahmed/2412/main/ncam_15.2-r0_all.sh", os.path.join(picfold, "Bb.png")),
                    ("oscam-emu-11868_mohamed-OS", "https://raw.githubusercontent.com/Ham-ahmed/22/main/oscam_11868-emu-r802.sh", os.path.join(picfold, "Bb.png")),
                    ("keyadder plugin v9.4-New-plugin", "https://raw.githubusercontent.com/fairbird/KeyAdder/main/installer.sh", os.path.join(picfold, "Bb.png")),
                    ("RaedQuickSignal-v17.4", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/RaedQuickSignalv17.4.sh", os.path.join(picfold, "Bb.png")),
                    ("multi-stalkerpro-v1.2openAtv7.5.1", "https://raw.githubusercontent.com/Ham-ahmed/Panel/main/Mstalker/MultiStalkerPro_Atv.sh", os.path.join(picfold, "Bb.png")),
                    ("multistalker-pro-v1.2", "https://raw.githubusercontent.com/Ham-ahmed/backup/main/multistalker-pro_v1.2.sh", os.path.join(picfold, "Bb.png")),
                    ("multistalker-pro-v1.1", "https://raw.githubusercontent.com/Ham-ahmed/112024/main/multi-stalkerpro_1.1.sh", os.path.join(picfold, "Bb.png")),
                    ("multistalker-pro.v1.2-py3.9.9", "https://raw.githubusercontent.com/Ham-ahmed/83/main/multi-stalkerpro-1.2.sh", os.path.join(picfold, "Bb.png")),
                    ("bouquetmakerxtream-1.18", "https://raw.githubusercontent.com/Ham-ahmed/Iptv-plugin/main/bouquetmakerxtream_pliugin1.18.20240723.sh", os.path.join(picfold, "Bb.png")),
                    ("e2iplayer", "https://gitlab.com/MOHAMED_OS/e2iplayer/-/raw/main/install-e2iplayer.sh", os.path.join(picfold, "Bb.png")),
                    ("Xklass-1.47", "https://raw.githubusercontent.com/Ham-ahmed/154/main/xklass_1.47.sh", os.path.join(picfold, "Bb.png")),
                    ("vavoo-v1.22", "https://raw.githubusercontent.com/Ham-ahmed/newp/main/vavoo_v1.22.sh", os.path.join(picfold, "Bb.png")),
                    ("iptosat-1.8", "https://gitlab.com/eliesat/extensions/-/raw/main/iptosat/iptosat.sh", os.path.join(picfold, "Bb.png")),
                    ("bouquetmakerxtream.v1.48", "https://raw.githubusercontent.com/Ham-ahmed/154/main/bouquetmakerxtream_1.48.sh", os.path.join(picfold, "Bb.png")),
                    ("jedimakerxtream-6.39", "https://raw.githubusercontent.com/Ham-ahmed/122/main/jedimakerxtream_6.39.sh", os.path.join(picfold, "Bb.png")),
                    ("History_Zap_1.0.38-py3.12", "https://raw.githubusercontent.com/biko-73/History_Zap_Selector/main/installer.sh", os.path.join(picfold, "Bb.png")),
                    ("oaweather2.6", "https://raw.githubusercontent.com/Ham-ahmed/1New-P/main/oaweather.sh", os.path.join(picfold, "Bb.png")),
                    ("weather-plugin-v2.1", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/main/weatherplugin_2.1_all.sh", os.path.join(picfold, "Bb.png")),
                    ("Tmbd-v.8.6-py3.11.2", "https://raw.githubusercontent.com/biko-73/TMBD/main/installer.sh", os.path.join(picfold, "Bb.png")),
                ]
            },
            "Bosnia Package": {
                "icon": os.path.join(picfold, "cam.png"),
                "channels": [
                    ("Bosnia_ukrania-Package", "https://raw.githubusercontent.com/Ham-ahmed/bo-snia/main/Bosnia_ukrania-MStream.sh", os.path.join(picfold, "Bb.png")),
                    ("ukrania_Bouquet-4.9e", "https://raw.githubusercontent.com/Ham-ahmed/bo-snia/main/ukrania_MStream_4.9e.sh", os.path.join(picfold, "Bb.png")),
                    ("astra-config_1711_New-17-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/bo-snia/refs/heads/main/astra-config_1711.sh", os.path.join(picfold, "Bb.png")),
                    ("astra-sm-arm-0.2", "https://raw.githubusercontent.com/Ham-ahmed/bo-snia/main/astra-sm_0.2-r0.sh", os.path.join(picfold, "Bb.png")),
                    ("ukrania_config-0109", "https://raw.githubusercontent.com/Ham-ahmed/bo-snia/main/ukrania_config_0109.sh", os.path.join(picfold, "Bb.png")),
                    ("Bosnia-Bouquet-16e", "https://raw.githubusercontent.com/Ham-ahmed/bo-snia/main/Bosnia_MStream_16e.sh", os.path.join(picfold, "Bb.png")),
                    ("astra_config-0507", "https://raw.githubusercontent.com/Ham-ahmed/bo-snia/main/astra_config_050724.sh", os.path.join(picfold, "Bb.png")),
                ]
            }
        }

        self.names = list(self.backup_data.keys())
        self.pics = [data["icon"] for data in self.backup_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.backup_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class IptvPlayerPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Iptv-player"
        self["info"].setText("اختر مشغل IPTV للتثبيت...")

        self.iptv_data = {
                        "estalker": {
                "icon": os.path.join(picfold, "pt1.png"),
                "channels": [
                    ("estalker_1.36_03-04-2026", "https://raw.githubusercontent.com/Ham-ahmed/304/refs/heads/main/estalker_1.36.sh", os.path.join(picfold, "pt1.png"), " kiddac مشغل الأي ب py 3.14.3 ي تي في من المطور"),
                    ("estalker_1.35_03-04-2026", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/estalker_1.35.sh", os.path.join(picfold, "pt1.png"), " kiddac مشغل الأي ب py 3.14.3 ي تي في من المطور"),
                    ("estalker_1.30_10-03-2026", "https://raw.githubusercontent.com/Ham-ahmed/1003/refs/heads/main/estalker_1.30.sh", os.path.join(picfold, "pt1.png"), " kiddac مشغل الأي بي تي في من المطور"),
                    ("estalker_1.27_20-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/estalker_1.27.sh", os.path.join(picfold, "pt1.png"), " kiddac مشغل الأي بي تي في من المطور"),
                    ("estalker_1.23_17-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/estalker_1.22.sh", os.path.join(picfold, "pt1.png"), " kiddac مشغل الأي بي تي في من المطور"),
                    ("estalker_1.20_06-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/611/refs/heads/main/estalker_1.20.sh", os.path.join(picfold, "pt1.png"), " kiddac مشغل الأي بي تي في من المطور"),
		            ("estalker_1.14-02-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/6-9/refs/heads/main/estalker_1.14.sh", os.path.join(picfold, "pt1.png"), " kiddac مشغل الأي بي تي في من المطور"),
                    ("estalker_1.11-23-08-2025", "https://raw.githubusercontent.com/Ham-ahmed/238/refs/heads/main/estalker_0.11.sh", os.path.join(picfold, "pt1.png")),
	            ]
            },
                        "Xklass": {
                "icon": os.path.join(picfold, "pt2.png"),
                "channels": [
                    ("Xklass-1.80-03-04-2026", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/xklass_1.80.sh", os.path.join(picfold, "pt2.png"), " kiddac مشغل الأي ب py 3.14.3 ي تي في من المطور"),
                    ("Xklass-1.78-10-03-2026", "https://raw.githubusercontent.com/Ham-ahmed/1003/refs/heads/main/xklass_1.78.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.77-28-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/2802/refs/heads/main/xklass_1.77.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.76-24-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/xklass_1.76.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.74-19-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/xklass_1.74.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.71-21-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/2111/refs/heads/main/xklass_1.71.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.70-17-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/1711/refs/heads/main/xklass_1.70.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.69-13-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/xklass_1.69.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.68-29-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2410/refs/heads/main/xklass_1.68.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.67-22-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2210/refs/heads/main/xklass_1.67.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.66-30-09-2025", "https://raw.githubusercontent.com/Ham-ahmed/6-9/refs/heads/main/xklass_1.66.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.60-17-07-2025", "https://raw.githubusercontent.com/Ham-ahmed/88/refs/heads/main/xklass_1.60.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.49-29-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/294/refs/heads/main/xklass_1.49.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.47-15-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/154/refs/heads/main/xklass_1.47.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.44-06-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/64/refs/heads/main/xklass_1.44.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.43-28-03-2025", "https://raw.githubusercontent.com/Ham-ahmed/283/refs/heads/main/xklass_1.43.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.38-13-03-2025", "https://raw.githubusercontent.com/Ham-ahmed/133/refs/heads/main/xklass_1.38.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.35-03-2-2025", "https://raw.githubusercontent.com/Ham-ahmed/122/refs/heads/main/xklass_1.35.sh", os.path.join(picfold, "pt2.png")),
                    ("Xklass-1.33-03-2-2025", "https://raw.githubusercontent.com/Ham-ahmed/32/refs/heads/main/xklass_1.33_all.sh", os.path.join(picfold, "pt2.png")),
	            ]
            },
                        "xstreamity": {
                "icon": os.path.join(picfold, "pt3.png"),
                "channels": [
                   ("xstreamity..v5.41_10-04-2026", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/xstreamity_5.41.sh", os.path.join(picfold, "pt3.png"), " kiddac مشغل الأي ب py 3.14.3 ي تي في من المطور"),
                   ("xstreamity..v5.39_03-04-2026", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/xstreamity_5.39.sh", os.path.join(picfold, "pt3.png"), " kiddac مشغل الأي ب py 3.14.3 ي تي في من المطور"),
                   ("xstreamity..v5.34_10-03-2026", "https://raw.githubusercontent.com/Ham-ahmed/1003/refs/heads/main/xstreamity_5.34.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.33_28-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/2802/refs/heads/main/xstreamity_5.33.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.32_24-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/xstreamity_5.32.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.31_22-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/21F/refs/heads/main/xstreamity_5.32.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.30_20-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/xstreamity_5.31.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.23_19-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/xstreamity_5.23.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.20_21-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/2111/refs/heads/main/xstreamity_5.20.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.19-17-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/1711/refs/heads/main/xstreamity_5.19.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.18-13-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/xstreamity_5.18.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.17-24-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2410/refs/heads/main/xstreamity_5.17.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.16-22-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2210/refs/heads/main/xstreamity_5.16.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.15-29-09-2025", "https://raw.githubusercontent.com/Ham-ahmed/6-9/refs/heads/main/xstreamity_5.15.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.13-11-09-2025", "https://raw.githubusercontent.com/Ham-ahmed/119/refs/heads/main/xstreamity_5.13.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v5.09-08-08-2025", "https://raw.githubusercontent.com/Ham-ahmed/198/refs/heads/main/xstreamity_5.09.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v4.95-15-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/154/refs/heads/main/xstreamity_4.95.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v4.92-06-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/283/refs/heads/main/xstreamity_4.90.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v4.90-28-3-2025", "https://raw.githubusercontent.com/Ham-ahmed/283/refs/heads/main/xstreamity_4.90.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v4.88-10-3-2025", "https://raw.githubusercontent.com/Ham-ahmed/93/refs/heads/main/xstreamity_4.88.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v4.86-24-2-2025", "https://raw.githubusercontent.com/Ham-ahmed/242/refs/heads/main/xstreamity_4.86.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v4.83..21-2-2025", "https://raw.githubusercontent.com/Ham-ahmed/2102/refs/heads/main/xstreamity_4.83.sh", os.path.join(picfold, "pt3.png")),
                   ("xstreamity..v4.75..03-2-2025", "https://raw.githubusercontent.com/Ham-ahmed/32/refs/heads/main/xstreamity_4.75.sh", os.path.join(picfold, "pt3.png")),
			    ]
            },
                        "jedimaker": {
                "icon": os.path.join(picfold, "pt4.png"),
                "channels": [
                   ("jediepgxtream_2.15", "https://raw.githubusercontent.com/Ham-ahmed/1610/refs/heads/main/jediepgxtream_2.15.sh", os.path.join(picfold, "pt4.png")),
                   ("jedimakerxtream", "https://gitlab.com/eliesat/extensions/-/raw/main/jedimakerxtream/jedimakerxtream.sh", os.path.join(picfold, "pt4.png")),
                   ("jedimakerxtream.v6.40", "https://raw.githubusercontent.com/Ham-ahmed/2102/refs/heads/main/jedimakerxtream_6.40.sh", os.path.join(picfold, "pt4.png")),
	            ]
            },
                        "bouquetmaker": {
                "icon": os.path.join(picfold, "pt5.png"),
                "channels": [
                   ("bouquetmakerxtream.v1.72", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/bouquetmakerxtream_1.72.sh", os.path.join(picfold, "pt5.png")),
                   ("bouquetmakerxtream.v1.66", "https://raw.githubusercontent.com/Ham-ahmed/1711/refs/heads/main/bouquetmakerxtream_1.66.sh", os.path.join(picfold, "pt5.png")),
                   ("bouquetmakerxtream.v1.65", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/bouquetmakerxtream_1.65.sh", os.path.join(picfold, "pt5.png")),
                   ("bouquetmakerxtream.v1.64", "https://raw.githubusercontent.com/Ham-ahmed/1610/refs/heads/main/bouquetmakerxtream_1.64.sh", os.path.join(picfold, "pt5.png")),
                   ("bouquetmakerxtream.v1.60", "https://raw.githubusercontent.com/Ham-ahmed/118/refs/heads/main/bouquetmakerxtream_1.60.sh", os.path.join(picfold, "pt5.png")),
                   ("bouquetmakerxtream.v1.48", "https://raw.githubusercontent.com/Ham-ahmed/154/refs/heads/main/bouquetmakerxtream_1.48.sh", os.path.join(picfold, "pt5.png")),
                   ("bouquetmakerxtream.v1.47", "https://raw.githubusercontent.com/Ham-ahmed/64/refs/heads/main/bouquetmakerxtream_1.47.sh", os.path.join(picfold, "pt5.png")),
                ]
            },
                        "Other-player": {
                "icon": os.path.join(picfold, "pt1.png"),
                "channels": [
                  ("vavoo-maker_1.63-New", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/vavoo_1.63.sh", os.path.join(picfold, "pt1.png")),
                  ("vavoo-maker_1.46", "https://raw.githubusercontent.com/Ham-ahmed/0102/refs/heads/main/vavoo-1.46.sh", os.path.join(picfold, "pt1.png")),
                  ("vavoo-maker_1.43", "https://raw.githubusercontent.com/Ham-ahmed/1912/refs/heads/main/vavoo_1.43.sh", os.path.join(picfold, "pt1.png")),
                  ("vavoo-maker_1.42", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/vavoo_1.42.sh", os.path.join(picfold, "pt1.png")),
                  ("vavoo-maker_1.40", "https://raw.githubusercontent.com/Ham-ahmed/2111/refs/heads/main/vavoo_1.40.sh", os.path.join(picfold, "pt1.png")),
                  ("vavoo-maker_1.2-New", "https://raw.githubusercontent.com/Belfagor2005/VavooMaker/main/installer.sh", os.path.join(picfold, "pt1.png")),
                  ("m3uconverter_3.1", "https://raw.githubusercontent.com/Ham-ahmed/611/refs/heads/main/m3uconverter_3.1.sh", os.path.join(picfold, "pt1.png")),
                  ("Archimede-M3UConverter2.1-New", "https://raw.githubusercontent.com/Belfagor2005/Archimede-M3UConverter/main/installer.sh", os.path.join(picfold, "pt1.png")),
                  ("m3uconverter_3.1", "https://raw.githubusercontent.com/Ham-ahmed/611/refs/heads/main/m3uconverter_3.1.sh", os.path.join(picfold, "pt1.png")),
                  ("vavoo-maker_1.38-New", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/vavoo_1.38.sh", os.path.join(picfold, "pt1.png")),
                  ("iptosat-1.8", "https://gitlab.com/eliesat/extensions/-/raw/main/iptosat/iptosat.sh", os.path.join(picfold, "pt1.png")),
                  ("xcplugin_forever-v4.3", "https://raw.githubusercontent.com/Belfagor2005/xc_plugin_forever/main/installer.sh", os.path.join(picfold, "pt1.png")),
                  ("multi-stalkerpro-v1.2-openAtv", "https://raw.githubusercontent.com/Ham-ahmed/2125/refs/heads/main/multi-stalkerpro_Atv-py3.-12-8.sh", os.path.join(picfold, "pt1.png")),
                  ("multistalker-pro-v1.2", "https://raw.githubusercontent.com/Ham-ahmed/backup/main/multistalker-pro_v1.2.sh", os.path.join(picfold, "pt1.png")),
                  ("multistalker-pro-v1.1", "https://raw.githubusercontent.com/Ham-ahmed/112024/refs/heads/main/multi-stalkerpro_1.1.sh", os.path.join(picfold, "pt1.png")),
                  ("stalkerportalconverter-v1.3", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/stalkerportalconverter_1.3.sh", os.path.join(picfold, "pt1.png")),
                  ("e2m3u2bouquet_2.0.12", "https://raw.githubusercontent.com/Ham-ahmed/1610/refs/heads/main/e2m3u2bouquet_2.0.12.sh", os.path.join(picfold, "pt1.png")),
                ]
            }
        }

        self.names = list(self.iptv_data.keys())
        self.pics = [data["icon"] for data in self.iptv_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.iptv_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class ElectronicGuidePanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "electronicGuide"
        self["info"].setText("اختر دليل إلكتروني...")

        self.electronic_guide_data = {
                        "EpgGrabber": {
                "icon": join(picfold, "eg1.png"),
                "channels": [
                   ("EpgGrabber-24.8-New_Version", "https://raw.githubusercontent.com/ziko-ZR1/Epg-plugin/master/Download/installer.sh", os.path.join(picfold, "eg1.png")),
                   ("EpgGrabber-23.7-", "https://raw.githubusercontent.com/ziko-ZR1/Epg-plugin/master/Download/installer.sh", os.path.join(picfold, "eg1.png")),
				   ("epgimport_2.9.3_iet5_New", "https://raw.githubusercontent.com/Ham-ahmed/2802/refs/heads/main/epgimport_2.9.3_iet5.sh", os.path.join(picfold, "eg1.png"), " Saied El far المطور"),
				   ("epgimport_mod_iet5-2.9", "https://raw.githubusercontent.com/Ham-ahmed/152/refs/heads/main/epgimport%20mod_iet5%202.9.sh", os.path.join(picfold, "eg1.png")),
				   ("epgimport-mod-dorik1972", "https://raw.githubusercontent.com/Ham-ahmed/122/refs/heads/main/epgimport-mod-dorik1972-1.9.1.sh", os.path.join(picfold, "eg1.png")),
				]
            },
		             	"subssupport": {
                "icon": join(picfold, "sub.png"),
                "channels": [
                  ("subssupport-v1.8.0-r7_py3.14.3_New", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/subssupport_1.8.0-r7.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.8.0-r7_py3.14.3", "https://raw.githubusercontent.com/Ham-ahmed/304/refs/heads/main/subssupport_1.8.0-r7.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.8.0-r6-New", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/subssupport_1.8.0-r6.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.8.0-r2-New", "https://raw.githubusercontent.com/Ham-ahmed/110/refs/heads/main/subssupport_1.8.0-r2.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.7.0-r25", "https://github.com/popking159/ssupport/raw/main/subssupport-install.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.7.0-r10", "https://github.com/popking159/ssupport/raw/main/subssupport-install.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.7.0-r8", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/subssupport-1.1.0-r8-install.sh", os.path.join(picfold, "sub.png")),
                  ("newvirtualkeyboard_Subsport", "https://raw.githubusercontent.com/fairbird/NewVirtualKeyBoard/main/subsinstaller.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.7.0-r7", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/refs/heads/main/subssupport-install.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.7.0 r6", "https://github.com/popking159/ssupport/raw/main/subssupport-install.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-v1.7.0 r5", "https://github.com/popking159/ssupport/raw/main/subssupport-install.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-By_Mora Hosny", "https://github.com/popking159/ssupport/raw/main/subssupport-install.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-By_Mora Hosny", "https://raw.githubusercontent.com/Ham-ahmed/subsupport/main/SubsSupport.sh", os.path.join(picfold, "sub.png")),
                  ("subssupport-3.12.1", "https://raw.githubusercontent.com/Ham-ahmed/subsupport/main/SubsSupport.sh", os.path.join(picfold, "sub.png")),
				]
            },
		               	"xtraevent": {
                "icon": join(picfold, "xt.png"),
                "channels": [
                  ("xtraevent-7.1", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/xtraevent_v7.1.sh", os.path.join(picfold, "Bb.png")),
                  ("xtraevent-6.893", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/xtraevent_6.893.sh", os.path.join(picfold, "Bb.png")),
                  ("xtraevent-6.892", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/xtraevent_6.892.sh", os.path.join(picfold, "Bb.png")),
                  ("xtraevent_6.891", "https://raw.githubusercontent.com/Ham-ahmed/611/refs/heads/main/xtraevent_6.891.sh", os.path.join(picfold, "Bb.png")),
                  ("xtraevent_6.890", "https://raw.githubusercontent.com/Ham-ahmed/2410/refs/heads/main/xtraevent_6.890.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.870", "https://raw.githubusercontent.com/Ham-ahmed/28/refs/heads/main/xtraevent_6.870.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.840", "https://raw.githubusercontent.com/Ham-ahmed/177/refs/heads/main/xtraevent_6.840.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.810", "https://raw.githubusercontent.com/Ham-ahmed/33/refs/heads/main/xtraevent_6.810_all.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.806", "https://raw.githubusercontent.com/popking159/xtraeventplugin/refs/heads/main/xtraevent-install.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.801", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel/main/EPGTranslator-plugin.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.802", "https://raw.githubusercontent.com/Ham-ahmed/plugins2/refs/heads/main/jediepgxtream_2.12.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.8", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/refs/heads/main/xtraevent_6.801_all.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent_6.798", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/refs/heads/main/xtraevent_6.8_all.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent-v6.7", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/refs/heads/main/xtraevent_6.798_all.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent-v6.6", "https://github.com/Ham-ahmed/xtra/blob/main/xtraevent-plugin_v6.7.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent-v6.2", "https://raw.githubusercontent.com/Ham-ahmed/xtra/main/xtraevent-plugin_v6.6.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent5.3", "https://raw.githubusercontent.com/Ham-ahmed/EPG/main/xtraEvent_v6.2.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent4.5", "https://raw.githubusercontent.com/Ham-ahmed/Secript-Panel/main/xtraevent-5.3.sh", os.path.join(picfold, "xt.png")),
                  ("xtraevent5.2", "https://gitlab.com/eliesat/extensions/-/raw/main/xtraevent/xtraevent-4.5.sh", os.path.join(picfold, "xt.png")),
				]
            },
			           	"TMBD": {
                "icon": join(picfold, "tmd.png"),
                "channels": [
				  ("TMBD_8.6-r7_py 3.11-12", "https://raw.githubusercontent.com/Ham-ahmed/plugins3/refs/heads/main/TMBD_8.6-r7.sh", os.path.join(picfold, "tmd.png")),
                  ("Tmbd-v.8.6_py 3.11.2", "https://raw.githubusercontent.com/Ham-ahmed/EPG/refs/heads/main/tmdb_1.0.9_all.sh", os.path.join(picfold, "tmd.png")),
                ]
            },
			           	"Translator": {
                "icon": join(picfold, "tmd.png"),
                "channels": [
				  ("Translator-1.4_py 3.12.9", "https://raw.githubusercontent.com/Ham-ahmed/312/refs/heads/main/translator_1.4.sh", os.path.join(picfold, "tmd.png"), " Edit by H Ahmed 03-12-2025"),
                ]
            },
			           	"NewVirtualKey": {
                "icon": join(picfold, "tmd.png"),
                "channels": [
				  ("NewVirtualKeyBoard_py 3.13.9-11", "https://raw.githubusercontent.com/fairbird/NewVirtualKeyBoard/main/installer.sh", os.path.join(picfold, "tmd.png")),
                ]
            }
        }

        self.names = list(self.electronic_guide_data.keys())
        self.pics = [data["icon"] for data in self.electronic_guide_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.electronic_guide_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class NovalerPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Novaler"
        self["info"].setText("")

        self.Novaler_data = {
            "novalerstore": {
                "icon": join(picfold, "nova.png"),
                "channels": [
                    ("novalerstore-py3.13", "http://ipk.ath.cx/pg/novalerstore-py3.13.sh", os.path.join(picfold, "nova.png")),
                    ("novalerstore-py3.12", "http://ipk.ath.cx/pg/novalerstore-py3.12.sh", os.path.join(picfold, "nova.png")),
                    ("novalerstore-py3-11", "http://ipk.ath.cx/pg/novalerstore-py3.11.sh", os.path.join(picfold, "nova.png")),
                    ("novalerstore-py3-9.9", "http://ipk.ath.cx/pg/novalerstore-py3.9.sh", os.path.join(picfold, "nova.png")),
                ]
            },
            "ipaudioplus": {
                "icon": join(picfold, "nova.png"),
                "channels": [
                    ("ipaudioplus-py3.12", "https://raw.githubusercontent.com/Ham-ahmed/Novaler/main/ipaudioplus-py3.12_4.1-r0_all.sh", os.path.join(picfold, "nova.png")),
                    ("ipaudioplus-py3-11", "https://raw.githubusercontent.com/Ham-ahmed/Novaler/main/ipaudioplus-py3.11_4.1-r0_all.sh", os.path.join(picfold, "nova.png")),
                    ("ipaudioplus-py3-9.9", "https://raw.githubusercontent.com/Ham-ahmed/Novaler/main/ipaudioplus-py3.9_4.1-r0_all.sh", os.path.join(picfold, "nova.png")),
                ]
            },
            "ipsat": {
                "icon": join(picfold, "nova.png"),
                "channels": [
                    ("ipsat-py3.12", "https://raw.githubusercontent.com/Ham-ahmed/Novaler/main/ipsat-py3.12_9.5-r0_all.sh", os.path.join(picfold, "nova.png")),
                    ("ipsat-py3-11", "https://raw.githubusercontent.com/Ham-ahmed/Novaler/main/ipsat-py3.11_9.5-r0_all.sh", os.path.join(picfold, "nova.png")),
                    ("ipsat-py3-9.9", "https://raw.githubusercontent.com/Ham-ahmed/Novaler/main/ipsat-py3.9_9.5-r0_all.sh", os.path.join(picfold, "nova.png")),
                ]
            },
            "novacampro": {
                "icon": join(picfold, "nova.png"),
                "channels": [
                    ("novacampro-py3.13", "http://ipk.ath.cx/pg/novacam-py3.13.sh", os.path.join(picfold, "nova.png")),
                    ("novacampro-py3.12", "http://ipk.ath.cx/pg/novacam-py3.12.sh", os.path.join(picfold, "nova.png")),
                    ("novacampro-py3.11", "http://ipk.ath.cx/pg/novacam-py3.11.sh", os.path.join(picfold, "nova.png")),
                    ("novacampro-py3.9", "http://ipk.ath.cx/pg/novacam-py3.9.sh", os.path.join(picfold, "nova.png")),
                ]
            },
            "beengo": {
                "icon": join(picfold, "nova.png"),
                "channels": [
                    ("beengo-py3.13", "http://ipk.ath.cx/pg/beengo-py3.13.sh", os.path.join(picfold, "nova.png")),
                    ("beengo-py3.12", "http://ipk.ath.cx/pg/beengo-py3.12.sh", os.path.join(picfold, "nova.png")),
                    ("beengo-py3-11", "http://ipk.ath.cx/pg/beengo-py3.11.sh", os.path.join(picfold, "nova.png")),
                    ("beengo-py3-9.9", "http://ipk.ath.cx/pg/beengo-py3.9.sh", os.path.join(picfold, "nova.png")),
                ]
            },
            "novatv": {
                "icon": join(picfold, "nova.png"),
                "channels": [
                    ("novalertv-py3.13", "http://ipk.ath.cx/pg/novalertv-py3.13.sh", os.path.join(picfold, "nova.png")),
                    ("novalertv-py3.12", "http://ipk.ath.cx/pg/novalertv-py3.12.sh", os.path.join(picfold, "nova.png")),
                    ("novalertv-py3-11", "http://ipk.ath.cx/pg/novalertv-py3.11.sh", os.path.join(picfold, "nova.png")),
                    ("novalertv-py3-9.9", "http://ipk.ath.cx/pg/novalertv-py3.9.sh", os.path.join(picfold, "nova.png")),
                    ("novatv-py3.13", "http://ipk.ath.cx/pg/novatv-py3.13.sh", os.path.join(picfold, "nova.png")),
                    ("novatv-py3.12", "http://ipk.ath.cx/pg/novatv-py3.12.sh", os.path.join(picfold, "nova.png")),
                    ("novatv-py3-11", "http://ipk.ath.cx/pg/novatv-py3.11.sh", os.path.join(picfold, "nova.png")),
                    ("novatv-py3-9.9", "http://ipk.ath.cx/pg/novatv-py3.9.sh", os.path.join(picfold, "nova.png")),
                ]
            }
        }

        self.names = list(self.Novaler_data.keys())
        self.pics = [data["icon"] for data in self.Novaler_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.Novaler_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class AudioPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Audio"
        self["info"].setText("")

        self.electronic_guide_data = {
            "plugin": {
                "icon": join(picfold, "sou.png"),
                "channels": [
                   ("Ipaudiopro-1.5-py3.13.11-opnvix&BH_27-01-2026", "https://gitlab.com/h-ahmed/Panel/-/raw/main/Ipaudiopro/install_ipaudio2-1.5.sh", os.path.join(picfold, "aud.png")),
                   ("Ipaudiopro-1.5-py3.13.9-opnvix&openBH", "https://gitlab.com/h-ahmed/Panel/-/raw/main/Ipaudiopro/install_ipaudio-1.5.sh", os.path.join(picfold, "aud.png")),
                   ("Ipaudio-8.6-py3.13.9-3.13.11", "https://raw.githubusercontent.com/popking159/ipaudio/main/installer-ipaudio.sh", os.path.join(picfold, "aud.png"), "By_D.Mohamed-Nasr"),
                   ("Ipaudiopro-1.5-py3.12.4-5-6", "https://raw.githubusercontent.com/zKhadiri/IPAudioPro-Releases-/refs/heads/main/installer.sh", os.path.join(picfold, "aud.png")),
                   ("Ipaudiopro-1.5-.py3.9.9", "https://raw.githubusercontent.com/Ham-ahmed/83/refs/heads/main/ipaudiopro_1.5_3.9.9.sh", os.path.join(picfold, "aud.png")),
                   ("Ipaudiopro-1.4-py3.12.4-5-6", "https://raw.githubusercontent.com/Ham-ahmed/Plugin/refs/heads/main/ipaudiopro_1.4.sh", os.path.join(picfold, "aud.png")),
                   ("ipaudiopro-haitham_Aniss+audio..", "https://raw.githubusercontent.com/Ham-ahmed/20-5/refs/heads/main/ipaudiopro-haitham.sh", os.path.join(picfold, "aud.png")),
                   ("Ipaudiopro-1.3-py3.12.4-5", "https://raw.githubusercontent.com/biko-73/ipaudio/main/ipaudiopro.sh", os.path.join(picfold, "aud.png")),
                   ("Ipaudiopro-openvix_6.6.001", "https://raw.githubusercontent.com/Ham-ahmed/Ipaudio-2024/main/ipaudiopro_1.1-r2.sh", os.path.join(picfold, "aud.png")),
                   ("Ipaudiopro-v1.1-py3.12", "https://raw.githubusercontent.com/Ham-ahmed/Ipaudio-2024/main/ipaudiopro-py3.12_v1.1-By-Zakaria.sh", os.path.join(picfold, "aud.png")),
                ]
            },
            "Audio Files": {
                "icon": join(picfold, "sou.png"),
                "channels": [
                   ("anisaudio-radiobest-AS_mix", "https://raw.githubusercontent.com/Ham-ahmed/1912/refs/heads/main/anisaudio-radiobest-AS_mix.sh", os.path.join(picfold, "aud.png"), "For plugin ipaudio8.7-ipaudiopro1.5"),
                   ("M-Elsaftyv1.1-r6_picons+audio", "https://raw.githubusercontent.com/Ham-ahmed/Ipaudio-2024/main/ipaudiopro1.1-r2-Elsafty.sh", os.path.join(picfold, "aud.png")),
                ]
            }
        }

        self.names = list(self.electronic_guide_data.keys())
        self.pics = [data["icon"] for data in self.electronic_guide_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.electronic_guide_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class SatchPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Satch"
        self["info"].setText("اختر فئة القنوات الفضائية...")

        self.satch_data = {
            "Hazem Wahba": {
                "icon": os.path.join(picfold, "ch3.png"),
                "channels": [
                    ("HAZEM-WAHBA-motor-17-04-2026", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/H-WAHBA-Channels.sh", os.path.join(picfold, "ch3.png"), "HAZEM-WAHBA_Motor-channel_34W-93E"),
                    ("HAZEM-WAHBA-motor-03-04-2026", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/HAZEM-WAHBA-Channels.sh", os.path.join(picfold, "ch3.png"), "HAZEM-WAHBA_Motor-channel_34W-93E"),
                    ("HAZEM-WAHBA-motor-28-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/2802/refs/heads/main/HAZEM-WAHBA-Channels.sh", os.path.join(picfold, "ch3.png"), "HAZEM-WAHBA_Motor-channel_34W-93E"),
                    ("HAZEM-WAHBA-motor-18-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/HAZEM-WAHBA-Channels.sh", os.path.join(picfold, "ch3.png"), "HAZEM-WAHBA_Motor-channel_34W-93E"),
                    ("HAZEM-WAHBA-motor-14-02-2026", "https://raw.githubusercontent.com/Ham-ahmed/142/refs/heads/main/HAZEM-WAHBA-Channels.sh", os.path.join(picfold, "ch3.png"), "HAZEM-WAHBA_Motor-channel_30W-90E"),
                    ("HAZEM-WAHBA-motor-02-01-2026", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/HAZEM-WAHBA-Channels.sh", os.path.join(picfold, "ch3.png"), "HAZEM-WAHBA_Motor-channel_30W-90E"),
                    ("HAZEM-WAHBA-motor-30-12-2025", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor-13-12-2025", "https://raw.githubusercontent.com/Ham-ahmed/1612/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png"), "HAZEM-WAHBA_Motor-channel_30W-90E"),
                    ("HAZEM-WAHBA-motor-06-12-2025", "https://raw.githubusercontent.com/Ham-ahmed/612/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor-29-11-2025", "https://raw.githubusercontent.com/Ham-ahmed/2911/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor-10-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/1010/refs/heads/main/HazenWahba_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor13-09-2025", "https://raw.githubusercontent.com/Ham-ahmed/929/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor06-09-2025", "https://raw.githubusercontent.com/Ham-ahmed/6-9/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor28-08-2025", "https://raw.githubusercontent.com/Ham-ahmed/28-8/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor10-08-2025", "https://raw.githubusercontent.com/Ham-ahmed/108/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor0-04-2025", "https://raw.githubusercontent.com/Ham-ahmed/48/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("HAZEM-WAHBA-motor10-02-2025", "https://raw.githubusercontent.com/Ham-ahmed/28/refs/heads/main/HAZEM-WAHBA_Channels.sh", os.path.join(picfold, "ch3.png")),
                ]
            },
            "Other Ch": {
                "icon": os.path.join(picfold, "ch3.png"),
                "channels": [
                    ("Mohammed-Nasr-motor_03-04-2026", "https://gitlab.com/h-ahmed/Panel/-/raw/main/204/MNASR-Channels.sh", os.path.join(picfold, "ch3.png")),
                    ("SaidiIsmail-motor_29-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/2910/refs/heads/main/SaidiIsmail_Channels.sh", os.path.join(picfold, "ch3.png"), "المطور - SaidiIsmail_30W-70E"),
                    ("Tarekalashry-motor_06-10-2025", "https://raw.githubusercontent.com/Ham-ahmed/610/refs/heads/main/Tarekalashry_Channels.sh", os.path.join(picfold, "ch3.png"), "المطور - Tarekalashry_30W-52E"),
                    ("mohamed-os-motor_31-01-2024", "https://raw.githubusercontent.com/Ham-ahmed/22/refs/heads/main/channels_backup_Mohamed-OS_31-1-2025.sh", os.path.join(picfold, "ch3.png")),
                    ("Mohammed-Nasr-motor8-3-202", "https://raw.githubusercontent.com/Ham-ahmed/133/refs/heads/main/channels_backup_MNasr_08-03-2025.sh", os.path.join(picfold, "ch3.png")),
                    ("mohamed-os-motor_20-12-2024", "https://raw.githubusercontent.com/Ham-ahmed/11863/refs/heads/main/channels_backup_Mohamed-OS_20-12-2024.sh", os.path.join(picfold, "ch3.png")),
                    ("mohamed-os-motor_12-12-2024", "https://raw.githubusercontent.com/Ham-ahmed/channels-Files/refs/heads/main/channels_backup_20241212_MohamedOS.sh", os.path.join(picfold, "ch3.png")),
                    ("mohamed-os-motor_29-11-2024", "https://raw.githubusercontent.com/Ham-ahmed/212/refs/heads/main/channels_backup_20241229_vhannibal.sh", os.path.join(picfold, "ch3.png")),
                    ("vhannibal-motor_29-11-2024", "https://raw.githubusercontent.com/Ham-ahmed/channels-Files/refs/heads/main/channels_backup_Mohamed-OS_22-11-2024.sh", os.path.join(picfold, "ch3.png")),
                    ("ciefp-motor_23-11-2024", "https://raw.githubusercontent.com/Ham-ahmed/channels-Files/refs/heads/main/channels_backup_20241123_ciefp.sh", os.path.join(picfold, "ch3.png")),
                    ("mohamed-os-motor_22-11-2024", "https://raw.githubusercontent.com/Ham-ahmed/channels-Files/refs/heads/main/channels_backup_Mohamed-OS_22-11-2024.sh", os.path.join(picfold, "ch3.png")),
                ]
            }
        }

        self.names = list(self.satch_data.keys())
        self.pics = [data["icon"] for data in self.satch_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.satch_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class OthersPanlPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "OthersPanl"
        self["info"].setText("")

        self.OthersPanl_data = {
            "levi45-addon": {
                "icon": join(picfold, "othe.png"),
                "channels": [
                    ("levi45-addon.manager10.1r31", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/levi45-addon_10.1-r31.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-addon.manager10.1r30", "https://raw.githubusercontent.com/Ham-ahmed/1612/refs/heads/main/levi45-addon_10.1-r30.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-addon.manager10.1r29", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/levi45-addon_10.1-r29.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-addon.manager10.1r28", "https://raw.githubusercontent.com/Ham-ahmed/43/refs/heads/main/installer-addon18.0-r28.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-multicammanager10.2-r5", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/levi45multicammanager_10.2-r5.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-multicammanager10.2-r4", "https://raw.githubusercontent.com/Ham-ahmed/1612/refs/heads/main/levi45multicam_10.2-r4.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-multicammanager10.2r2.", "https://raw.githubusercontent.com/levi-45/Manager/main/installer.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-multicammanager10.1r33", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/levi45multicammanager_10.1-r33.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-multicammanager10.2r3.", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/levi45multicam_10.2-r3.sh", os.path.join(picfold, "lev.png")),
                    ("freeserver-v2.4-New", "https://raw.githubusercontent.com/Ham-ahmed/21F/refs/heads/main/levi45-freeserver_2.4.sh", os.path.join(picfold, "lev.png")),
                    ("freeserver-v2.3", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/levi45-freeserver_2.3.sh", os.path.join(picfold, "lev.png")),
                    ("freeserver-v2.2", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/levi45-freeserver_2.2.sh", os.path.join(picfold, "lev.png")),
                    ("freeserver-v2_1", "https://raw.githubusercontent.com/Ham-ahmed/2112/refs/heads/main/levi45-freeserver_2.1.sh", os.path.join(picfold, "lev.png")),
                    ("freeserver-v2_1.4", "https://raw.githubusercontent.com/Ham-ahmed/1612/refs/heads/main/levi45-freeserver-py2_1.4.sh", os.path.join(picfold, "lev.png")),
					("levi45-freeserver_1.8", "https://raw.githubusercontent.com/Ham-ahmed/210/refs/heads/main/freeserver_1.8.sh", os.path.join(picfold, "lev.png"), "Plugin By developer levi45"),
                    ("levi45emulator_1.3", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/levi45emulator_1.3.sh", os.path.join(picfold, "lev.png")),
                    ("levi45emulator_1.2", "https://raw.githubusercontent.com/Ham-ahmed/1812/refs/heads/main/levi45emulator_1.2.sh", os.path.join(picfold, "lev.png")),
                    ("levi45emulator_1.1", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/levi45emulator_1.1.sh", os.path.join(picfold, "lev.png")),
                    ("levi45emulator_1.0", "https://raw.githubusercontent.com/Ham-ahmed/198/refs/heads/main/levi45emulator_1.0.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-settings_1.6", "https://raw.githubusercontent.com/Ham-ahmed/192/refs/heads/main/levi45-settings_1.6.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-settings_1.5", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/levi45-settings_1.5.sh", os.path.join(picfold, "lev.png")),
					("levi45-settings_1.4", "https://raw.githubusercontent.com/Ham-ahmed/1612/refs/heads/main/levi45-settings_1.4.sh", os.path.join(picfold, "lev.png")),
                    ("levi45-settings_1.3", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/levi45-settings_1.3.sh", os.path.join(picfold, "lev.png")),
					("levi45-settings_1.2", "https://raw.githubusercontent.com/Ham-ahmed/206/refs/heads/main/levi45-settings_1.2.sh", os.path.join(picfold, "lev.png")),
					("levi45-settings_1.9", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/levi45-freeserver_1.9.sh", os.path.join(picfold, "lev.png")),
                    ("levi45iptv_1.2_New", "https://raw.githubusercontent.com/Ham-ahmed/2112/refs/heads/main/levi45iptv_1.2.sh", os.path.join(picfold, "lev.png"), "Plugin By developer levi45"),
					("levi45iptv_1.0", "https://raw.githubusercontent.com/Ham-ahmed/2611/refs/heads/main/levi45iptv_1.0.sh", os.path.join(picfold, "lev.png"), "Plugin By developer levi45"),
                    ("oscam-emu-levi45_11949-803", "https://raw.githubusercontent.com/Ham-ahmed/194/refs/heads/main/oscam_levi45_11959.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11946-803", "https://raw.githubusercontent.com/Ham-ahmed/104/refs/heads/main/oscam-emu-levi45_11946-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11945-803", "https://raw.githubusercontent.com/Ham-ahmed/083/refs/heads/main/oscam-emu-levi45_11945-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11942-803", "https://raw.githubusercontent.com/Ham-ahmed/0102/refs/heads/main/levi45_oscam-11942-r803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11936-803", "https://raw.githubusercontent.com/Ham-ahmed/221/refs/heads/main/oscam-emu-levi45_11936-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11925-803", "https://raw.githubusercontent.com/Ham-ahmed/181/refs/heads/main/oscam-emu-levi45_11925-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11907-803", "https://raw.githubusercontent.com/Ham-ahmed/1812/refs/heads/main/oscam-emu-levi45_11907-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11906-803", "https://raw.githubusercontent.com/Ham-ahmed/2111/refs/heads/main/oscam-emu-levi45_11906-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11903-803", "https://raw.githubusercontent.com/Ham-ahmed/611/refs/heads/main/oscam-levi45_11903-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11902-803", "https://raw.githubusercontent.com/Ham-ahmed/2210/refs/heads/main/oscam-emu-levi45_11902-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45_11891-803", "https://raw.githubusercontent.com/Ham-ahmed/1610/refs/heads/main/oscam-emu-levi45_11891-803.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11889-803", "https://raw.githubusercontent.com/levi-45/Levi45Emulator/main/installer.sh", os.path.join(picfold, "lev.png")),
					("oscam-emu-levi45-11885-802", "https://raw.githubusercontent.com/Ham-ahmed/177/refs/heads/main/oscam-emu-levi45_11885-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11884-802", "https://raw.githubusercontent.com/Ham-ahmed/105/refs/heads/main/oscam-emu-levi45_11884-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11868-802", "https://raw.githubusercontent.com/Ham-ahmed/22/refs/heads/main/oscam-emu-levi45_11868-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11865-802", "https://raw.githubusercontent.com/Ham-ahmed/2125/refs/heads/main/oscam-emu-levi45_11865-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11862-802", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/oscam-emu-levi45_11862-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11861-802", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/oscam-emu-levi45_11861-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11860-802", "https://raw.githubusercontent.com/Ham-ahmed/oscam11860/refs/heads/main/oscam-emu-levi45_11860-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11858-802", "https://raw.githubusercontent.com/Ham-ahmed/Levi45/refs/heads/main/oscam-emu-levi45_11858-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11856-802", "https://raw.githubusercontent.com/Ham-ahmed/others2/refs/heads/main/oscam-emu-levi45_11856-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11854-802", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/oscam-emu-levi45_11854-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11849-802", "https://raw.githubusercontent.com/Ham-ahmed/others2/refs/heads/main/oscam-emu-levi45_11849-802.sh", os.path.join(picfold, "lev.png")),
                    ("oscam-emu-levi45-11847-802", "https://raw.githubusercontent.com/Ham-ahmed/others2/refs/heads/main/oscam-emu-levi45_11847-802.sh", os.path.join(picfold, "lev.png")),
					("oscam-emu-levi45-11845-802", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/oscam-emu-levi45_11845-802.sh", os.path.join(picfold, "othe.png")),
				]
            },
            "Other-panel": {
                "icon": join(picfold, "othe.png"),
                "channels": [
                    ("CiefpTMDBSearch-1.7_New", "https://raw.githubusercontent.com/ciefp/CiefpTMDBSearch/main/installer.sh", os.path.join(picfold, "othe.png")),
                    ("CiefpChannelManager-1.4_New", "https://raw.githubusercontent.com/ciefp/CiefpChannelManager/main/installer.sh", os.path.join(picfold, "othe.png")),
                    ("oscamicamall_020-Update-Kitte888", "https://raw.githubusercontent.com/Ham-ahmed/152/refs/heads/main/oscamicamall%20020%20Kitte888.sh", os.path.join(picfold, "othe.png"), "Plugin By developer Kitte888"),
                    ("oscamicamall_019-Update-Kitte888", "https://raw.githubusercontent.com/Ham-ahmed/221/refs/heads/main/oscamicamall_019-Update-Kitte888.sh", os.path.join(picfold, "othe.png"), "Plugin By developer Kitte888"),
                	("oscamicamall_V.10.0-Kitte888", "https://raw.githubusercontent.com/Ham-ahmed/210/refs/heads/main/oscamicamall_V.10.0.sh", os.path.join(picfold, "othe.png"), "Plugin By developer Kitte888"),
				    ("oscamicamall_V.9.2-Kitte888", "https://raw.githubusercontent.com/Ham-ahmed/238/refs/heads/main/oscamicamall_V.9.2-Kitte888.sh", os.path.join(picfold, "othe.png")),
                    ("oscamicamnew-11857-ICAMEMU", "https://raw.githubusercontent.com/Ham-ahmed/Levi45/refs/heads/main/oscamicamnew_11857-ICAMEMU-Kitte888.sh", os.path.join(picfold, "othe.png")),
                    ("oscamicamnew-11847-ICAMEMU", "https://raw.githubusercontent.com/Ham-ahmed/others2/refs/heads/main/oscamicamnew_11847-ICAMEMU-Kitte888.sh", os.path.join(picfold, "othe.png")),
                    ("oscamicamnew-11886-ICAMEMU", "https://raw.githubusercontent.com/Ham-ahmed/88/refs/heads/main/oscamicamnewtest_11886-ICAMEMUTEST.sh", os.path.join(picfold, "othe.png")),
                    ("oscamicamnew-11868-ICAMEMU", "https://raw.githubusercontent.com/Ham-ahmed/83/refs/heads/main/oscamicamnew_11868-ICAMEMU-Kitte888.sh", os.path.join(picfold, "othe.png")),
                    ("oscamicamnew-11845-ICAMEMU", "https://raw.githubusercontent.com/Ham-ahmed/Others/refs/heads/main/oscamicamnew_11845-ICAMEMU-Kitte888.sh", os.path.join(picfold, "othe.png")),
                    ("oscam-11943-802_audi06_19", "https://raw.githubusercontent.com/Ham-ahmed/21F/refs/heads/main/oscam-11943-802_audi06_19.sh", os.path.join(picfold, "othe.png")),
                    ("oscam-emu 11881 802 audi06_19", "https://raw.githubusercontent.com/Ham-ahmed/294/refs/heads/main/oscam-11881-emu-802.sh", os.path.join(picfold, "othe.png")),
                    ("CiefpsettingsPanel-v.2", "https://raw.githubusercontent.com/Ham-ahmed/141/refs/heads/main/installer.sh", os.path.join(picfold, "othe.png")),
                    ("panelaio_plugin9.1.1", "https://raw.githubusercontent.com/Ham-ahmed/2402/refs/heads/main/panelaio_9.1.1.sh", os.path.join(picfold, "othe.png")),
                    ("panelaio_plugin3.1", "https://raw.githubusercontent.com/Ham-ahmed/1311/refs/heads/main/panelaio_3.1.sh", os.path.join(picfold, "othe.png")),
                    ("panelaio_plugin1.6", "https://raw.githubusercontent.com/Ham-ahmed/28/refs/heads/main/panelaio_1.6.sh", os.path.join(picfold, "othe.png")),
                    ("CiefpOscamEditor-1.2.0", "https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh", os.path.join(picfold, "othe.png")),
                ]
            }
        }

        self.names = list(self.OthersPanl_data.keys())
        self.pics = [data["icon"] for data in self.OthersPanl_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.OthersPanl_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class PiconsPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Picons"
        self["info"].setText("")

        self.Picons_data = {
            "Picons plugin": {
                "icon": join(picfold, "ico003.png"),
                "channels": [
                     ("chocholousek-plugin", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/chocholousek-picons_5.0.240904.sh", join(picfold, "plu.png")),
                     ("piconinstaller-plugin", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/piconinstaller_24.08.26_all.sh", join(picfold, "plu.png")),
                ]
            },
            "All sat": {
                "icon": join(picfold, "ico003.png"),
                "channels": [
                    ("picons_All-Sat_30-3-2024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons_All-Sat_28-3-2024.sh", join(picfold, "icon02.png")),
                    ("picons_NilSat-8W-26E", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-Nilsat-8w-26e_01032024.sh", join(picfold, "icon02.png")),
                ]
            },
            "weast sat": {
                "icon": join(picfold, "ico003.png"),
                "channels": [
                    ("picons-30.0W-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-30.0W_2032024.sh", join(picfold, "icon02.png")),
                    ("Nilsat7.0w-8.0w-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-Nilsat7.0w-8.0w_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-7.0W-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-7.0W_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-8.0W-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-8.0W_2032024.sh", join(picfold, "icon02.png")),
                    ("picons_NilSat-8W", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-Nilsat-8w-01032024.sh", join(picfold, "icon02.png")),
                    ("picons-4.0W-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-4.0W_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-1.0W-0.8W_2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-1.0W-0.8W_2032024.sh", join(picfold, "icon02.png")),
                ]
            },
            "est sat": {
                "icon": join(picfold, "ico003.png"),
                "channels": [
                    ("picons-1.9E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-1.9E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-7.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-7.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-9.0E-2832024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-9.0E_2832024.sh", join(picfold, "icon02.png")),
                    ("picons-13.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-13.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-16.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-16.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-19.2E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-19.2E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-21.5E-2832024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-21.5E_28032024.sh", join(picfold, "icon02.png")),
                    ("picons-23.5E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-23.5E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-26.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-26.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-39.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-39.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-42.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-42.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-45.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-45.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-46.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-46.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-51.5E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-51.5E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-52.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-52.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-53.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-53.0E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-54.9E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-54.9E_2032024.sh", join(picfold, "icon02.png")),
                    ("picons-62.0E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-62.0E2032024.sh", join(picfold, "icon02.png")),
                    ("picons-68.5E-2032024", "https://raw.githubusercontent.com/Ham-ahmed/picons/main/picons-68.5E_2032024.sh", join(picfold, "icon02.png")),
                ]
            }
        }

        self.names = list(self.Picons_data.keys())
        self.pics = [data["icon"] for data in self.Picons_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.Picons_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class BootlogoPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Bootlogo"
        self["info"].setText("")

        self.bootlogo_data = {
            "Bootlogo plugin": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("bootlogoswapper", "https://gitlab.com/eliesat/extensions/-/raw/main/bootlogoswapper/bootlogoswapper-eliesat-special-edition.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"openAtv": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
		           ("atv share-3-bootlogo", "https://gitlab.com/h-ahmed/Panel/-/raw/main/bootlogo/a-tv/bootlogo-atv-share.sh", os.path.join(picfold, "blogo.png")),
                   ("atv Swapper-8-bootlogo", "https://gitlab.com/h-ahmed/Panel/-/raw/main/bootlogo/a-tv/bootlogos-atv_swa.sh", os.path.join(picfold, "blogo.png")),
				   ("openatv-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openatv.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"openvix": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
			       ("openvix...share3bootlogo", "https://gitlab.com/h-ahmed/Panel/-/raw/main/bootlogo/vix/bootlogo-vix-share.sh", os.path.join(picfold, "blogo.png")),
                   ("openvix-Swap8-bootlogo", "https://gitlab.com/h-ahmed/Panel/-/raw/main/bootlogo/vix/bootlogos-vix_swa.sh", os.path.join(picfold, "blogo.png")),
				   ("openvix-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openvix.sh", os.path.join(picfold, "blogo.png")),
                   ("openvix-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openvix.sh", os.path.join(picfold, "blogo.png")),
                   ("openvix-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openfix.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"teamblue": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("teamblue-share3-bootlogo", "https://gitlab.com/h-ahmed/Panel/-/raw/main/bootlogo/t-blue/bootlogo-Tblue-share.sh", os.path.join(picfold, "blogo.png")),
                   ("teamblue-Swap.8-bootlogo", "https://gitlab.com/h-ahmed/Panel/-/raw/main/bootlogo/t-blue/bootlogos-Tblue_swa.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"egami": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
			       ("Egami-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-egami.sh", os.path.join(picfold, "blogo.png")),
                   ("Egami-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-novaler.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"openspa": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("openspa-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openspa.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"pure2": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("pure2-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-pure2.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"openbh": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("openbh-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openblackhole.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"opendroid": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("opendroid-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-opendroid.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"openhdf": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("openhdf-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openhdf.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"openpli": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("openpli-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-openpli.sh", os.path.join(picfold, "blogo.png")),
				]
            },
			"pkteam": {
                "icon": join(picfold, "Bb.png"),
                "channels": [
                   ("pkteam-logo", "https://gitlab.com/eliesat/display/-/raw/main/n-image/bootlogos-n-pkteam.sh", os.path.join(picfold, "blogo.png")),
                ]
            }
        }

        self.names = list(self.bootlogo_data.keys())
        self.pics = [data["icon"] for data in self.bootlogo_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.bootlogo_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class MediaPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Media"
        self["info"].setText("")

        self.Media_data = {
            "Media": {
                "icon": join(picfold, "media.png"),
                "channels": [
                ("E2IPlayer-oe-mirrors_12-10-2025", "https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh", os.path.join(picfold, "media.png")),
                ("E2IPlayer-D.M.Nasr-patch_12-10-2025", "https://github.com/popking159/mye2iplayer/raw/main/update_e2iplayer-patch.sh", os.path.join(picfold, "media.png")),
                ("E2IPlayer+Tsplayer-biko", "https://raw.githubusercontent.com/biko-73/E2IPlayer/main/installer_E2.sh", os.path.join(picfold, "media.png")),
                ]
            }
        }

        self.names = list(self.Media_data.keys())
        self.pics = [data["icon"] for data in self.Media_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.Media_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class RemovePanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Remove"
        self["info"].setText("")

        self.Remove_data = {
            "Remove": {
                "icon": join(picfold, "re.png"),
                "channels": [
                    ("aglare_Skin-remove...", "https://raw.githubusercontent.com/Ham-ahmed/Remove/main/aglare_remove.sh", os.path.join(picfold, "re.png")),
				    ("aglarepli-Skin_remove", "https://raw.githubusercontent.com/Ham-ahmed/Remove/main/aglarepli_remove.sh", os.path.join(picfold, "re.png")),
                ]
            }
        }

        self.names = list(self.Remove_data.keys())
        self.pics = [data["icon"] for data in self.Remove_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.Remove_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class ScriptsPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "Scripts"
        self["info"].setText("اختر فئة السكريبتات...")

        self.scripts_data = {
            "addons Scripts": {
                "icon": os.path.join(picfold, "scrip.png"),
                "description": "سكريبتات الاضافات",
                "channels": [
                   ("Delete_Oscam_Emu-Script", "https://raw.githubusercontent.com/Ham-ahmed/2111/refs/heads/main/OSCAM-Removal.sh", os.path.join(picfold, "scr.png"), "Oscam سكريبت حذف الايمو"),
                   ("Delete_All_Emu Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Delete_All_Emu.sh", os.path.join(picfold, "scr.png"), "سكريبت حذف الايمو"),
                   ("Install_ipk_File Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Install_ipk_File.sh", os.path.join(picfold, "scr.png"), "ipk سكريبت تنزيل ملفات"),
                   ("Install_tar-gz_File Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Install_tar-gz_File.sh", os.path.join(picfold, "scr.png"), "Tar.gz سكريبت تنزيل ملفات"),
                   ("mount-media-hdd Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/mount-media-hdd.sh", os.path.join(picfold, "scr.png"), "HDD سكريبت عمل مونت"),
                   ("Restart_enigma2_user Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Restart_enigma2_user.sh", os.path.join(picfold, "scr.png"), "سكريبت عمل اعادة تشغيل"),
                   ("Wget Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Wget.sh", os.path.join(picfold, "scr.png"), "wegitسكريبت "),
                   ("update_images-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/update_tools_images_All-python.sh", os.path.join(picfold, "scr.png"), "ترقية صور الانيجما"),
                   ("DELETE-All-server-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/DELETE-All-server.sh", os.path.join(picfold, "scr.png"), "حذف جميع السيرفرات"),
                   ("DELETE-AllEmu-Ncam-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/DELETE-AllEmu-Ncam.sh", os.path.join(picfold, "scr.png"), "حذف ايمو Ncam"),
                   ("Delete-All_Config-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/Delete-All_Config.sh", os.path.join(picfold, "scr.png"), "حذف كل الكونفج"),
                   ("DELETE_AllEmu-Oscam-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/DELETE_AllEmu-Oscam.sh", os.path.join(picfold, "scr.png"), "حذف ايمو oscam"),
                   ("Delete_All_Crashlogs-Oscam-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/Delete_All_Crashlogs.sh", os.path.join(picfold, "scr.png"), "حذف ملفات الكراش"),
                   ("Delete_channels_bouquets-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/Delete_All_channels_bouquets.sh", os.path.join(picfold, "scr.png"), "حذف ملفات القنوات"),
                   ("Backup_ALL-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/Backup_ALL.sh", os.path.join(picfold, "scr.png"), "عمل باكب كامل"),
                ]
            },
            "ch-bouquets Scripts": {
                "icon": os.path.join(picfold, "scrip.png"),
                "description": "سكريبتات عمل باكب ",
                "channels": [
                   ("Bouquets_Backup Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Bouquets_Backup.sh", os.path.join(picfold, "scr.png"), "سكريبت عمل باكب من ملف قنوات"),
                   ("Bouquets_restore Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Bouquets_Restore.sh", os.path.join(picfold, "scr.png"), "سكريبت فك باكب من ملف قنوات"),
                ]
            },
            "Network Scripts": {
                "icon": os.path.join(picfold, "scrip.png"),
                "description": "Network سكربتات خاصة",
                "channels": [
                   ("IP_address Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/IP_address.sh", os.path.join(picfold, "scr.png"), "الرسيفر  IP  معرفة"),
                   ("Dns-Google Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/DnsGoogle.sh", os.path.join(picfold, "scr.png"), "الرسيفر DNS تغيير"),
                   ("Connection Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Connection_List.sh", os.path.join(picfold, "scr.png"), "بيان حالة الاتصال بالانترنت"),
                ]
            },
            "System Scripts": {
                "icon": os.path.join(picfold, "scrip.png"),
                "description": "system سكريبتات خدمة",
                "channels": [
                   ("Modules_stb Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Modules_stb.sh", os.path.join(picfold, "scr.png"), "معرفة موديل الرسيفر"),
                   ("FreeMemory Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/FreeMemory.sh", os.path.join(picfold, "scr.png"), "تفريغ رامات الرسيفر"),
                   ("Free_Space Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/Free_Space.sh", os.path.join(picfold, "scr.png"), "حل مشكل المساحة"),
                   ("setting-enigma2 Script", "https://raw.githubusercontent.com/Ham-ahmed/1310/refs/heads/main/setting-enigma2.sh", os.path.join(picfold, "scr.png"), "setting-enigma2"),
                   ("System-Info Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/System_info.sh", os.path.join(picfold, "scr.png"), "معلومات نظام التشغيل"),
                   ("STB-Info Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/info_STB.sh", os.path.join(picfold, "scr.png"), "معلومات عن الرسيفر"),
                   ("Cpu_informaition-Script", "https://raw.githubusercontent.com/Ham-ahmed/1410/refs/heads/main/Cpu_informaition.sh", os.path.join(picfold, "scr.png"), "معلومات عن cpu"),
                ]
            }
        }

        self.names = list(self.scripts_data.keys())
        self.pics = [data["icon"] for data in self.scripts_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]
        self.descriptions = [data.get("description", "لا يوجد وصف متاح") for data in self.scripts_data.values()]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.scripts_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class medosharePanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)
        self.name = "share"
        self["info"].setText("اختر فئة السكريبتات...")

        self.medoshare_data = {
            "servers": {
                "icon": os.path.join(picfold, "medo1.png"),
                "description": "سيرفرات تجربة",
                "channels": [
                   ("Medoshare-Server1", "https://raw.githubusercontent.com/Ham-ahmed/medo/refs/heads/main/Medoshare-Server1.sh", os.path.join(picfold, "medo3.png"), "MedoShare-Server_Cccam"),
                   ("Medoshare-Server2", "https://raw.githubusercontent.com/Ham-ahmed/medo/refs/heads/main/Medoshare-Server2.sh", os.path.join(picfold, "medo4.png"), "MedoShare-Server_MGcam"),
                ]
            },
            "info": {
                "icon": os.path.join(picfold, "medo2.png"),
                "description": "معلومات وتقارير",
                "channels": [
                   ("info_Sat-Report", "https://raw.githubusercontent.com/Ham-ahmed/medo/refs/heads/main/info_Sat-Report.sh", os.path.join(picfold, "medo2.png"), "Information about Satallite"),
                   ("info_MedoShare", "https://raw.githubusercontent.com/Ham-ahmed/medo/refs/heads/main/info_medoshare.sh", os.path.join(picfold, "medo2.png"), "Inside the country Egypt"),
                ]
            }
        }

        self.names = list(self.medoshare_data.keys())
        self.pics = [data["icon"] for data in self.medoshare_data.values()]
        self.urls = [""] * len(self.names)
        self.titles = self.names[:]
        self.descriptions = [data.get("description", "لا يوجد وصف متاح") for data in self.medoshare_data.values()]

        for i, pic in enumerate(self.pics):
            self.pics[i] = load_image(pic)

        self.onLayoutFinish.append(self.paint_screen)

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                category = self.names[self.index]
                channels = self.medoshare_data[category]["channels"]
                self.session.open(ChannelGridMenu, category, channels)
        except Exception as e:
            self.session.open(MessageBox, "خطأ في فتح الفئة: %s" % str(e), MessageBox.TYPE_ERROR)

class MagicPanel(BasePanel):
    def __init__(self, session):
        BasePanel.__init__(self, session)

        try:
            self.setTitle("%s" % descplug + " V." + currversion)
        except:
            self.setTitle("Magic Panel Gold V." + currversion)

        self["info"].setText("اختر خيار...")
        self["title"].setText("Magic Panel Gold V." + currversion)

        menu_items = [
            ("Skins", os.path.join(picfold, "Skins.png"), "تثبيت وتغيير سكينس الواجهة"),
            ("Free", os.path.join(picfold, "Free.png"), "خدمات stalker مجانية"),
            ("Ajpanel", os.path.join(picfold, "aj.png"), "لوحة Ajpanel بميزات متقدمة"),
            ("plugins", os.path.join(picfold, "pll.png"), "إضافات وبلجنات إضافية"),
            ("Cam-Emu", os.path.join(picfold, "cam33.png"), "مشغلات ومحاكيات CAM"),
            ("Backup", os.path.join(picfold, "Bb.png"), "نسخ احتياطية واستعادة"),
            ("Iptv-player", os.path.join(picfold, "ipt.png"), "مشغلات IPTV متقدمة"),
            ("electronicGuide", os.path.join(picfold, "ep.png"), "دليل البرامج والإرشادات"),
            ("Novaler", os.path.join(picfold, "nova.png"), "خدمات Novaler المتكاملة"),
            ("Audio", os.path.join(picfold, "sou.png"), "إعدادات الصوت والمشغلات"),
            ("satch", os.path.join(picfold, "ch3.png"), "قنوات ساتلية وإعداداتها"),
            ("OthersPanl", os.path.join(picfold, "op.png"), "خيارات وإضافات إضافية"),
            ("Picons", os.path.join(picfold, "picons.png"), "أيقونات القنوات والشعارات"),
            ("Bootlogo", os.path.join(picfold, "B.png"), "شاشات البدء والإقلاع"),
            ("Media", os.path.join(picfold, "media.png"), "مشغلات الوسائط المتعددة"),
            ("Remove", os.path.join(picfold, "re.png"), "إزالة التطبيقات والإضافات"),
            ("Scripts", os.path.join(picfold, "scrip.png"), "سكريبتات النظام والإدارة"),
            ("MyPanel", os.path.join(picfold, "pa.png"), "لوحة التحكم الرئيسية والإعدادات"),
        ]

        self.names = [name for name, _, _ in menu_items]
        self.titles = self.names[:]
        self.pics = [load_image(pic) for _, pic, _ in menu_items]
        self.urls = [""] * len(self.names)
        self.descriptions = [desc for _, _, desc in menu_items]

        self.onLayoutFinish.append(self.paint_screen)

        self.auto_update_manager = AutoUpdateManager(session)

        self.onShown.append(self.auto_check_updates)

    def auto_check_updates(self):
        """التحقق التلقائي من التحديثات عند فتح البلجن"""
        try:
            self.update_timer = eTimer()
            self.update_timer.callback.append(self.perform_auto_update_check)
            self.update_timer.start(3000, True)

        except Exception as e:
            print(f"خطأ في إعداد التحقق التلقائي من التحديثات: {e}")

    def perform_auto_update_check(self):
        """تنفيذ التحقق التلقائي من التحديثات"""
        try:
            self.auto_update_manager.check_and_update()
        except Exception as e:
            print(f"خطأ أثناء التحقق التلقائي من التحديثات: {e}")

    def okbuttonClick(self):
        try:
            if 0 <= self.index < len(self.names):
                name = self.names[self.index]

                self["info"].setText(f"فتح {name}...")
                self["description"].setText(self.descriptions[self.index])

                if name == "Skins":
                    self.session.open(SkinsPanel)
                elif name == "Free":
                    self.session.open(FreePanel)
                elif name == "Ajpanel":
                    self.session.open(AjpanelPanel)
                elif name == "plugins":
                    self.session.open(PluginsPanel)
                elif name == "Cam-Emu":
                    self.session.open(CamEmuPanel)
                elif name == "Backup":
                    self.session.open(BackupPanel)
                elif name == "Iptv-player":
                    self.session.open(IptvPlayerPanel)
                elif name == "electronicGuide":
                    self.session.open(ElectronicGuidePanel)
                elif name == "Novaler":
                    self.session.open(NovalerPanel)
                elif name == "Audio":
                    self.session.open(AudioPanel)
                elif name == "satch":
                    self.session.open(SatchPanel)
                elif name == "OthersPanl":
                    self.session.open(OthersPanlPanel)
                elif name == "Picons":
                    self.session.open(PiconsPanel)
                elif name == "Bootlogo":
                    self.session.open(BootlogoPanel)
                elif name == "Media":
                    self.session.open(MediaPanel)
                elif name == "Remove":
                    self.session.open(RemovePanel)
                elif name == "Scripts":
                    self.session.open(ScriptsPanel)
                elif name == "MyPanel":
                    self.session.open(MultibootPanel)
                else:
                    self.session.open(MessageBox, "الميزة قريباً!", MessageBox.TYPE_INFO)

        except Exception as e:
            error_msg = f"خطأ في فتح القسم: {str(e)}"
            print(error_msg)
            self.session.open(MessageBox, error_msg, MessageBox.TYPE_ERROR)

# --- Plugin Definition and Main Entry Points ---
def main(session, **kwargs):
    try:
        session.open(MagicPanel)
    except Exception as e:
        print(f"Error opening MagicPanel: {e}")
        try:
            session.open(MessageBox, "خطأ في البلجن: %s" % str(e), MessageBox.TYPE_ERROR)
        except:
            pass

def menu(menuid, **kwargs):
    if menuid == "mainmenu":
        return [("Magic Panel Gold v10.0", main, descplug, 44)]
    return []

# التعريف النهائي لـ Plugins مع التعامل مع جميع الحالات
def Plugins(**kwargs):
    plugin_list = []

    if HAS_PLUGIN_DESCRIPTOR:
        # استخدام PluginDescriptor الحقيقي إذا كان متوفراً
        from Plugins.Plugin import PluginDescriptor

        plugin_list.append(PluginDescriptor(
            name="MagicPanelGold",
            description=descplug,
            icon=load_image(os.path.join(picfold, "MagicPanelGold.png")),
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        ))

        plugin_list.append(PluginDescriptor(
            name="MagicPanelGold",
            description=descplug,
            icon="MagicPanelGold.png",
            where=PluginDescriptor.WHERE_MENU,
            fnc=menu
        ))
    else:
        # استخدام تعريف بديل إذا لم يكن PluginDescriptor متوفراً
        print("Using fallback PluginDescriptor definition")

        class FallbackPluginDescriptor:
            WHERE_PLUGINMENU = 1
            WHERE_MENU = 2

            def __init__(self, name, description, icon, where, fnc):
                self.name = name
                self.description = description
                self.icon = icon
                self.where = where
                self.fnc = fnc

        plugin_list.append(FallbackPluginDescriptor(
            name="MagicPanelGold",
            description=descplug,
            icon=load_image(os.path.join(picfold, "MagicPanelGold.png")),
            where=FallbackPluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        ))

        plugin_list.append(FallbackPluginDescriptor(
            name="MagicPanelGold",
            description=descplug,
            icon="MagicPanelGold.png",
            where=FallbackPluginDescriptor.WHERE_MENU,
            fnc=menu
        ))

    return plugin_list

if __name__ == "__main__":
    print("Magic Panel Gold v10.0 Plugin - Test Mode")