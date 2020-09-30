import os, sys, shutil, time
from smiler import smiler
from smiler import reporter
import acvcut
import test_short


def main():
    stubs_path = os.path.join('..', 'wd', 'stubs.txt')
    #original_apk_path = os.path.join("..", "apks", "simple_apps", "app.apk")
    original_apk_path = os.path.join("..", "wd", "short.apk")
    app_name = os.path.basename(original_apk_path)
    wd_path = os.path.join('..', 'wd_short')

    smiler.instrument_apk(original_apk_path, wd_path, ignore_filter=stubs_path, keep_unpacked=True)

    instrumented_apk = os.path.join(wd_path, "instr_short.apk")
    pickle_path = os.path.join(wd_path, "metadata", "short.pickle")
    test_and_report(instrumented_apk, acvcut.package, pickle_path, wd_path)
    # ec_file = os.path.join(wd_path, "io.pilgun.multidexapp", "ec_files", "onstop_coverage_1585928756160.ec")
    # smalitree = reporter.get_covered_smalitree([ec_file], pickle_path)


def test_and_report(app_path, package, pickle, wd_path):
    smiler.uninstall(package)
    smiler.install(app_path)
    os.system("adb logcat -c")
    smiler.start_instrumenting(acvcut.package, release_thread=True)
    os.system("adb shell monkey -p {} 1".format(package))
    time.sleep(10)
    smiler.stop_instrumenting(acvcut.package)
    reporter.generate(acvcut.package, pickle, wd_path)


if __name__ == "__main__":
    main()
