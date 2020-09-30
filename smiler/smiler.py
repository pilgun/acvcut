import os
import subprocess
import re
import shutil
import threading
import signal
import logging
import time, sched
from config import config
from granularity import Granularity
from instrumenting import manifest_instrumenter
from libs.libs import Libs
from instrumenting.apkil.smalitree import SmaliTree
from instrumenting.apktool_interface import ApktoolInterface
from instrumenting.smali_instrumenter import Instrumenter
from instrumenting.utils import timeit
from instrumenting.utils import Utils

apk_info_pattern = re.compile("package: name='(?P<package>.*?)'")


CRASH_REPORT_FILENAME = "errors.txt"

def install(new_apk_path):
    logging.info("installing {}".format(os.path.basename(new_apk_path)))
    cmd = '{} install -r "{}"'.format(config.adb_path, new_apk_path)
    out = request_pipe(cmd)
    
    logging.info(out)

def uninstall(package):
    logging.info("uninstalling")
    cmd = '{} uninstall "{}"'.format(config.adb_path, package)
    out = request_pipe(cmd)

    logging.info(out)

def request_pipe(cmd):
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = pipe.communicate()

    res = out
    if not out:
        res = err
    
    if pipe.returncode > 0:
        raise Exception("----------------------------------------------------\n\
Out: %s\nError: %s" % (out, err))

    return res

def get_apk_properties(path):
    info_cmd = "%s dump badging %s" % (config.aapt_path, path)
    out = request_pipe(info_cmd)
    matched = re.match(apk_info_pattern, out)

    package_name = matched.group('package')
    
    return apkinfo(package_name, "", "")


def get_package_files_list(package_name):
    cmd = '{} shell ls "/mnt/sdcard/{}/"'.format(config.adb_path, package_name)
    out = request_pipe(cmd)
    files = [f for f in out.split() if not f.endswith('/')]
    return files  

def get_execution_results(package_name, ec_dir, images_dir):
    result_files = get_package_files_list(package_name)
    coverage_files = [f for f in result_files if f.endswith(".ec")]
    images_files = [f for f in result_files if f.endswith(".png")]
    crash_file = CRASH_REPORT_FILENAME if CRASH_REPORT_FILENAME in result_files else None

    if not (coverage_files or crash_file):
        raise Exception("No coverage or crash report files have been detected on the device for {} package.\n\
        Run acvtool with \'-start\' argument to produce coverage.".format(package_name))
    
    Utils.recreate_dir(ec_dir)
    Utils.recreate_dir(images_dir)
    
    pull_files(ec_dir, coverage_files, package_name)
    pull_files(images_dir, images_files, package_name)
    if crash_file:
        pull_files(ec_dir, [crash_file], package_name)


def pull_files(dir_name, file_list, package_name):
    for f in file_list:
        adb_pull(package_name, f, dir_name)
        adb_delete_files(package_name, f)


def adb_pull(package_name, file_path, pull_to):
    cmd = "%s pull mnt/sdcard/%s/%s %s" % (config.adb_path, package_name, file_path, os.path.abspath(pull_to))
    out = request_pipe(cmd)
    logging.info(out)


def adb_delete_files(package_name, file_name):
    cmd = "%s shell rm mnt/sdcard/%s/%s" % (config.adb_path, package_name, file_name)
    out = request_pipe(cmd)


def grant_storage_permission(package):
    read_storage_cmd = "{0} shell pm grant {1} android.permission.READ_EXTERNAL_STORAGE".format(config.adb_path, package)
    subprocess.call(read_storage_cmd, shell=True)

    write_storage_cmd = "{0} shell pm grant {1} android.permission.WRITE_EXTERNAL_STORAGE".format(config.adb_path, package)
    subprocess.call(write_storage_cmd, shell=True)


def start_instrumenting(package, release_thread=False, onstop=None, timeout=None):
    grant_storage_permission(package)
    lock_thread = "" if release_thread else "-w"
    cmd = '{} shell am instrument {} {}/{}'.format(config.adb_path, lock_thread, package, config.INSTRUMENTING_NAME)
    if release_thread:
        os.system(cmd)
        locked = sdcard_path_exists(package) # dir is created, service started # to be change to another lock file on start
        timeout = config.default_onstop_timeout if timeout is None else timeout
        while not locked and timeout:
            time.sleep(1)
            logging.info("wait for coverage service activation {}".format(package))
            locked = sdcard_path_exists(package)
            timeout -= 1
        if not locked:
            raise Exception("Coverage service did not start in time ({})".format(package))
        return
    out = ''
    def run():
        out = request_pipe(cmd)
        logging.info(out)
        
    original_sigint = signal.getsignal(signal.SIGINT)
    
    def stop(signum, frame):
        signal.signal(signal.SIGINT, original_sigint)
        stop_instrumenting(package, timeout)
        if onstop:
            onstop()

    t = threading.Thread(target=run)
    t.start()
    
    print("Press Ctrl+C to finish ...")
    signal.signal(signal.SIGINT, stop)


def sdcard_path_exists(path):
    cmd = "{} shell \"test -e /mnt/sdcard/{} > /dev/null 2>&1 && echo \'1\' || echo \'0\'\"".format(config.adb_path, path)
    logging.debug('Command to check lock file:' + cmd)
    locked = subprocess.check_output(cmd, shell=True).replace("\n","").replace("\r", "")
    return locked == '1'


def coverage_is_locked(package_name):
    lock_file = "{}.lock".format(package_name)
    return sdcard_path_exists(lock_file)


def stop_instrumenting(package_name, timeout=None):
    cmd = "{} shell am broadcast -a 'tool.acv.finishtesting'".format(config.adb_path)
    logging.info("finish testing")
    result = subprocess.call(cmd, shell=True)
    logging.info(result)
    locked = coverage_is_locked(package_name)
    if timeout is None:
        timeout = config.default_onstop_timeout
    while locked and timeout:
        logging.info("wait until the coverage file is saved {}".format(package_name))
        time.sleep(1)
        locked = coverage_is_locked(package_name)
        timeout -= 1

    files = get_package_files_list(package_name)
    coverage_files = [f for f in files if f.endswith(".ec")]
    crash_file = CRASH_REPORT_FILENAME if CRASH_REPORT_FILENAME in files else None

    logging.info("coverage files at /mnt/sdcard/{0}:".format(package_name))
    logging.info("\n".join(coverage_files))
    if crash_file:
        logging.info("crash report /mnt/sdcard/{0}/{1}".format(package_name, crash_file))


def snap(package_name, i=0, output=None):
    logging.info("ec+screen {}".format(i))
    snap_cmd = "{} shell am broadcast -a 'tool.acv.finishtesting'".format(config.adb_path)
    result = subprocess.call(snap_cmd)

    if output:
        if not os.path.exists(output):
            os.makedirs(output)
        files = [f for f in get_package_files_list(package_name) if f.endswith(".ec")]
        pull_files(output, files, package_name)
            
    #screens
    # files = get_package_files_list(package_name)
    # adb_files_ec_set = [f for f in files if f.endswith('.ec')]
    # if len(adb_files_ec_set) > 0:
    #     new_ec = adb_files_ec_set[-1]
    #     time_mark = new_ec.split('_')[1][:-3]
    #     logging.info("screen..")
    #     scrn_cmd = "{} shell screencap -p /mnt/sdcard/{}/{}.png".format(config.adb_path, package_name, time_mark)
    #     result = subprocess.call(scrn_cmd)
    # else:
    #     logging.info("No ec files saved on sdcard.")
    # return


def save_ec_and_screen(package_name, delay=10, output=None, snap_number=722): # 720 per 10s is 2 hours
    i = 1
    logging.info("scheduler: {}, {} sec output: {}".format(package_name, delay, output))
    schedule = sched.scheduler(time.time, time.sleep)
    while i < snap_number:
        schedule.enter(delay*i, i, snap, (package_name, i, output))
        i += 1
    schedule.run()


@timeit
def instrument_apk(apk_path, result_dir, dbg_start=None, dbg_end=None, installation=False, granularity=Granularity.default, mem_stats=None, ignore_filter=None, keep_unpacked=False):
    '''
    I assume that the result_dir is empty is checked.
    '''
    apktool = ApktoolInterface(javaPath = config.APKTOOL_JAVA_PATH,
                               javaOpts = config.APKTOOL_JAVA_OPTS,
                               pathApktool = Libs.APKTOOL_PATH,
                               jarApktool = Libs.APKTOOL_PATH)
    package = get_apk_properties(apk_path).package
    unpacked_data_path = decompile_apk(apktool, apk_path, package, result_dir)
    manifest_path = get_path_to_manifest(unpacked_data_path)
    logging.info("decompiled {0}".format(package))

    instrument_manifest(manifest_path)
    smali_code_path = get_path_to_smali_code(unpacked_data_path)
    file_name = os.path.basename(apk_path)[:-4]
    pickle_path = get_pickle_path(file_name, result_dir)
    instrument_smali_code(smali_code_path, pickle_path, package, granularity, dbg_start, dbg_end, mem_stats, ignore_filter)
    logging.info("instrumented")
   
    instrumented_package_path = get_path_to_instrumented_package(apk_path, result_dir)
    remove_if_exits(instrumented_package_path)
    build_apk(apktool, unpacked_data_path, instrumented_package_path)
    if not keep_unpacked:
        Utils.rm_tree(unpacked_data_path)
    logging.info("built")

    instrumented_apk_path = get_path_to_insrumented_apk(instrumented_package_path, result_dir)
    sign_align_apk(instrumented_package_path, instrumented_apk_path)

    logging.info("apk instrumented: {0}".format(instrumented_apk_path))
    logging.info("package name: {0}".format(package))
    if installation:
        install(instrumented_apk_path)
    return (package, instrumented_apk_path, pickle_path)


def remove_if_exits(path):
    if os.path.exists(path):
        os.remove(path)


def build_dir(apktool_dir, result_dir, signature=False, installation=False):
    apktool = ApktoolInterface(javaPath = config.APKTOOL_JAVA_PATH,
                               javaOpts = config.APKTOOL_JAVA_OPTS,
                               pathApktool = Libs.APKTOOL_PATH,
                               jarApktool = Libs.APKTOOL_PATH)
    build_pkg_path = os.path.join(result_dir, "build_temp.apk")
    build_apk(apktool, apktool_dir, build_pkg_path)
    package = get_apk_properties(build_pkg_path).package
    result_apk_path = build_pkg_path
    if signature:
        result_apk_path = os.path.join(result_dir, "build_{0}.apk".format(package))
        sign_align_apk(build_pkg_path, result_apk_path)
        print('apk was built and signed: {0}'.format(result_apk_path))
    else:
        print('apk was built: {0}'.format(result_apk_path))
    if installation:
        install(result_apk_path)
    return result_apk_path


def decompile_apk(apktool, apk_path, package, result_dir):
    unpacked_data_path = os.path.join(result_dir, "apktool", package)
    (run_successful, cmd_output) = apktool.decode(apkPath = apk_path,
                                        dirToDecompile = unpacked_data_path,
                                        quiet = True,
                                        noSrc = False,
                                        noRes = False,
                                        debug = False,
                                        noDebugInfo = False,
                                        force = True, #directory exist so without this this process finishes
                                        frameworkTag = "",
                                        frameworkDir = "",
                                        keepBrokenRes = False)

    if not run_successful:
        print("Run is not successful!")
    
    return unpacked_data_path


def get_path_to_manifest(unpacked_data_path):
    pth = os.path.join(unpacked_data_path, "AndroidManifest.xml")
    return pth


def get_path_to_smali_code(unpacked_data_path):
    pth = os.path.join(unpacked_data_path, "smali")
    return pth


def get_path_to_instrumentation_metadata_dir(result_dir):
    pth = os.path.join(result_dir, "metadata")
    return pth


def get_path_to_insrumented_apk(apk_path, result_dir):
    apk_dir, apk_fname = os.path.split(apk_path)
    new_apk_fname = "{}_{}".format("instr", apk_fname)
    pth = os.path.join(result_dir, new_apk_fname)
    return pth


def get_path_to_instrumented_package(apk_path, result_dir):
    apk_dir, apk_fname = os.path.split(apk_path)
    path = os.path.join(result_dir, apk_fname)
    return path


def get_pickle_path(file_name, result_dir):
    metadata_dir = get_path_to_instrumentation_metadata_dir(result_dir)
    return os.path.join(metadata_dir, "{}.pickle".format(file_name))


def instrument_manifest(manifest_path):
    manifest_instrumenter.instrumentAndroidManifestFile(manifest_path, addSdCardPermission=True)


@timeit
def instrument_smali_code(input_smali_dir, pickle_path, package, granularity, dbg_start=None, dbg_end=None, mem_stats=None, ignore_filter=None):
    smali_tree = SmaliTree(input_smali_dir)
    if ignore_filter:
        apply_ignore_filter(smali_tree, ignore_filter)
    smali_instrumenter = Instrumenter(smali_tree, granularity, package, dbg_start, dbg_end, mem_stats)
    smali_instrumenter.save_instrumented_smali(input_smali_dir)
    smali_instrumenter.save_pickle(pickle_path)


def apply_ignore_filter(smali_tree, ignore_filter):
    if not os.path.exists(ignore_filter):
        return
    with open(ignore_filter, 'r') as f:
        lines = f.readlines()
        smali_tree.update_class_ref_dict()
        for l in lines:
            parts = l.strip().split('->')
            klass = parts[0]
            if klass in smali_tree.class_ref_dict:
                if len(parts) == 2 and parts[1] in smali_tree.class_ref_dict[klass].meth_ref_dict:
                    smali_tree.class_ref_dict[klass].meth_ref_dict[parts[1]].ignore = True
                else:
                    smali_tree.class_ref_dict[klass].ignore = True


def sign_align_apk(instrumented_package_path, output_apk):
    aligned_apk_path = instrumented_package_path.replace('.apk', '_signed_tmp.apk')
    align_cmd = '"{}" -f 4 "{}" "{}"'.format(config.zipalign, instrumented_package_path, aligned_apk_path)
    request_pipe(align_cmd)

    apksigner_cmd = '{} sign --ks {} --ks-pass pass:{} --out {} {}'\
        .format(config.apksigner_path, config.keystore_path, config.keystore_password, output_apk, aligned_apk_path)
    request_pipe(apksigner_cmd)
    os.remove(aligned_apk_path)


def build_apk(apktool, apkdata_dir, new_apk_path):
    apktool.build(srcPath=apkdata_dir, finalApk=new_apk_path, forceAll=True, 
                  debug=False)


class apkinfo(object):
    """Properties of the apk file."""
    def __init__(self, package=None, sdkversion=None, targetsdkverion=None):
        self.package = package
        self.sdkversion = sdkversion
        self.targetsdkversion = targetsdkverion

    def __repr__(self):
        return "%s %s %s" % (self.package, self.sdkversion, self.targetsdkversion)
