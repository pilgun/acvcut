import os, sys, shutil, time
from smiler import smiler
from smiler import reporter
from smiler.granularity import Granularity
from smiler.instrumenting.smali_instrumenter import Instrumenter
from smiler.instrumenting.apktool_interface import ApktoolInterface
from smiler.libs.libs import Libs
from smiler.config import config
import acvcut

def main():
    apktool = get_apktool()
    original_apk_path = os.path.join("..", "apks", "simple_apps", "app.apk")
    app_name = os.path.basename(original_apk_path)

    wd_path = os.path.join('..', 'wd_short')
    smali_dir = os.path.join(wd_path, "apktool", acvcut.package, "smali")

    unpacked_app_path = os.path.join(wd_path, "apktool", acvcut.package)
    unpacked_app_path = smiler.decompile_apk(apktool, original_apk_path, acvcut.package, wd_path)
    smalitree = acvcut.load_pickle(acvcut.cut_smalitree_path)
    instrumentation_pickle_path = smiler.get_pickle_path(app_name[:-4], wd_path)
    instrumenter = Instrumenter(smalitree, "instruction", acvcut.package)
    instrumenter.save_instrumented_smali(smali_dir)
    instrumenter.save_pickle(instrumentation_pickle_path)
    
    instrument_manifest(unpacked_app_path)

    instrumented_apk_path = build_n_sign(original_apk_path, wd_path, unpacked_app_path, apktool)
    
    run_acv_online_routine(wd_path, instrumented_apk_path, instrumentation_pickle_path)
    

def run_acv_online_routine(wd_path, instrumented_apk_path, instrumentation_pickle_path):
    report_out = os.path.join(wd_path, "report")

    smiler.uninstall(acvcut.package)
    smiler.install(instrumented_apk_path)
    smiler.start_instrumenting(acvcut.package, release_thread=True)
    os.system("adb shell monkey -p {} 1".format(acvcut.package))
    time.sleep(3)
    smiler.stop_instrumenting(acvcut.package)
    reporter.generate(acvcut.package, instrumentation_pickle_path, report_out)

def build_n_sign(apk_path, wd_path, app_data_path, apktool):
    instrumented_package_path = smiler.get_path_to_instrumented_package(apk_path, wd_path)
    smiler.build_apk(apktool, app_data_path, instrumented_package_path)
    instrumented_apk_path = smiler.get_path_to_insrumented_apk(instrumented_package_path, wd_path)
    smiler.sign_align_apk(instrumented_package_path, instrumented_apk_path)
    return instrumented_apk_path

def instrument_manifest(app_data_path):
    manifest_path = smiler.get_path_to_manifest(app_data_path)
    smiler.instrument_manifest(manifest_path)

def get_apktool():
    apktool = ApktoolInterface(javaPath = config.APKTOOL_JAVA_PATH,
                            javaOpts = config.APKTOOL_JAVA_OPTS,
                            pathApktool = Libs.APKTOOL_PATH,
                            jarApktool = Libs.APKTOOL_PATH)
    return apktool

if __name__ == "__main__":
    main()


