import os, sys, shutil, time
from smiler import smiler
from smiler import reporter
from smiler.granularity import Granularity
from smiler.instrumenting.utils import Utils
import acvcut
import argparse

parser = argparse.ArgumentParser(description='Prepares the working directory.')
parser.add_argument("apk_path", metavar="apk_path", help="path to the original apk")
parser.add_argument("--wd", metavar="wd", help="path to the working directory")
parser.add_argument("--package", metavar="package", help="app package name")

args = parser.parse_args()
wd_path = args.wd # acvcut.wd_path
apk_path = args.apk_path # acvcut.apk_path
package = args.package # acvcut.package

ignore_methods = None # list of methods to ignore coverage measurement 

apktool = os.path.join('smiler', 'libs', 'jars', 'apktool_2.4.1.jar')

app_name = os.path.basename(apk_path)
acv_wd = os.path.join("wd")

pickle = os.path.join(acv_wd, "metadata", app_name[:-3]+'pickle')
pickle_wd = os.path.join(wd_path, "metadata", os.path.basename(pickle))
instr_apk = os.path.join(acv_wd, "instr_"+ app_name)
instr_apk_wd = os.path.join(wd_path, "instr_"+ app_name)

decompiled_app_dir = os.path.join(wd_path, "dec_apk")
smali_dir = os.path.join(decompiled_app_dir, "smali")
smali_dir_cp = os.path.join(wd_path, "smali_orig")

report_out = os.path.join(wd_path)

DEBUG = False

if not DEBUG and os.path.exists(wd_path):
    Utils.recreate_dir(wd_path)
    shutil.rmtree(wd_path)
    os.makedirs(wd_path)

# prepare apktool dirs 
if not DEBUG:
    cmd_dec = "java -jar {} d {} -o {}".format(apktool, apk_path, decompiled_app_dir)
    os.system(cmd_dec)
    shutil.copytree(smali_dir, smali_dir_cp)
else:
    shutil.rmtree(smali_dir)
    shutil.copytree(smali_dir_cp, smali_dir)

smiler.instrument_apk(apk_path, acv_wd, ignore_filter=ignore_methods)

if DEBUG:
    sys.exit()
# copy instrumented metadata
dirname = os.path.dirname(pickle_wd)
if not os.path.exists(dirname):
    os.makedirs(dirname)
shutil.copy(pickle, pickle_wd)
shutil.copy(instr_apk, instr_apk_wd)
shutil.rmtree(acv_wd)

# continue acvtool flow
# acvtool (run emulator first)
smiler.uninstall(package)
smiler.install(instr_apk_wd)
os.system("adb logcat -c")
smiler.start_instrumenting(package, release_thread=True)

raw_input("Test the app and press Enter to continue...")
time.sleep(1)
smiler.stop_instrumenting(package)
reporter.generate(package, pickle_wd, report_out, ignore_filter=ignore_methods)
print("report: {}".format(report_out))
