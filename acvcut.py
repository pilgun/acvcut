import os
import sys
import yaml
import shutil
import logging
import argparse
import cPickle as pickle

from logging import config as logging_config
from smiler.config import config
from smiler import reporter
from smiler import instrumenting
from smiler.instrumenting.apktool_interface import ApktoolInterface
from smiler.libs.libs import Libs
from smiler import smiler
from cutter import cutter
from cutter import basic_block
from cutter import methods
from cutter import invokes

parser = argparse.ArgumentParser(description='Runs the shrinking routine.')
parser.add_argument("apk_path", metavar="apk_path", help="path to the original apk")
parser.add_argument("--wd", metavar="wd", help="path to the working directory")
parser.add_argument("--package", metavar="package", help="app package name")

args = parser.parse_args()
wd_path = args.wd # acvcut.wd_path
apk_path = args.apk_path # acvcut.apk_path
package = args.package # acvcut.package

def setup_logging():
    with open(config.logging_yaml) as f:
        logging_config.dictConfig(yaml.safe_load(f.read()))


def clean_smali_dir(smali_path):
    if os.path.exists(smali_path):
        shutil.rmtree(smali_path)


def rm_file(path):
    if os.path.exists(path):
        os.remove(path)

def get_ec_file(dir_path):
    paths = [os.path.join(dir_path, n) for n in os.listdir(dir_path) if n.endswith(".ec")]
    return paths

def save_pickle(path, smalitree):
    if not os.path.exists(path):
        with open(path, 'wb') as f:
                pickle.dump(smalitree, f, pickle.HIGHEST_PROTOCOL)
        print('pickle file saved: {0}'.format(path))

def load_pickle(path):
    st = None
    with open(path, 'rb') as f:
        st = pickle.load(f)
    return st

app_name = os.path.basename(apk_path)
instr_pickle_path = os.path.join(wd_path, "metadata", app_name[:-3]+'pickle')
ec_dir = os.path.join(wd_path, package, "ec_files")
decompiled_app_dir = os.path.join(wd_path, "dec_apk")
original_smali_path = os.path.join(wd_path, "smali_orig")
out_apk_raw = os.path.join(wd_path, "short_raw.apk")
out_apk = os.path.join(wd_path, "short.apk")
smali_path = os.path.join(decompiled_app_dir, "smali")
original_smalitree_path = os.path.join(wd_path, "original_smalitree.pickle")
cut_smalitree_path = os.path.join(wd_path, "cut_smalitree.pickle")

stub_methods_outpath = os.path.join(wd_path, "stubs.txt")

def main():
    rm_file(out_apk)
    rm_file(out_apk_raw)
    rm_file(original_smalitree_path)
    rm_file(cut_smalitree_path)
    
    clean_smali_dir(smali_path)
    
    smalitree = reporter.get_smalitree(instr_pickle_path)
    ec = get_ec_file(ec_dir)
    for ec_file in ec:
        coverage = reporter.read_ec(ec_file)
        reporter.cover_smalitree(smalitree, coverage)
    orig_invokes = invokes.get_invoke_direct_methods(smalitree)
    insns_stats(smalitree)

    basic_block.remove_blocks_from_selected_method(smalitree)
    stub_methods = methods.clean_not_executed_methods(smalitree)
    save_list(stub_methods_outpath, stub_methods)
    methods.remove_static(smalitree)
    result_invokes = invokes.get_invoke_direct_methods(smalitree)
    to_remove_invokes = orig_invokes - result_invokes
    invokes.remove_methods_by_invokes(smalitree, to_remove_invokes)
    
    insns_stats(smalitree)
    save_smali(smali_path, smalitree, package)
    
    build_apk(out_apk)
    test_apk(out_apk, package)
    

def save_list(path, entities_list):
    str_list = "\n".join(entities_list)
    with open(path, 'w') as f:
        f.write(str_list)


def clean_smalitree_coverage(smalitree):
    for cl in smalitree.classes:
        for m in cl.methods:
            m.called = False
            m.cover_code = -1
            for insn in m.insns:
                insn.cover_code = -1
                insn.covered = False
            for l in m.labels.values():
                l.cover_code = -1
                l.covered = False


def insns_stats(smalitree):
    methods = sum([len(cl.methods) for cl in smalitree.classes])
    print("total methods: {}".format(methods))
    sync_methods = sum([sum(1 for m in ms if m.synchronized) for ms in [cl.methods for cl in smalitree.classes]])
    print("sync methods: {}".format(sync_methods))
    ignored_methods = sum([sum(1 for m in ms if m.ignore) for ms in [cl.methods for cl in smalitree.classes]])
    print("ignored methods: {}".format(ignored_methods))
    insns_sum = sum([sum([len(m.insns) for m in ms]) for ms in [cl.methods for cl in smalitree.classes]])
    print("total insns: {}".format(insns_sum))


def save_smali(smali_path, smalitree, package):
    instrumenter = instrumenting.smali_instrumenter.Instrumenter(smalitree, "method", package)
    instrumenter.save_instrumented_smali(smali_path, instrument=False)


def build_apk(out_apk_path):
    apktool = ApktoolInterface(javaPath = config.APKTOOL_JAVA_PATH,
                               javaOpts = config.APKTOOL_JAVA_OPTS,
                               pathApktool = Libs.APKTOOL_PATH,
                               jarApktool = Libs.APKTOOL_PATH)
    print("output apk: {}".format(out_apk_path))
    print("decompiled app dir: {}".format(decompiled_app_dir))
    smiler.build_apk(apktool, decompiled_app_dir, out_apk_raw)
    smiler.sign_align_apk(out_apk_raw, out_apk_path)
    os.remove(out_apk_raw)


def test_apk(apk_path, package):
    smiler.uninstall(package)
    smiler.install(apk_path)
    os.system("adb logcat -c")
    os.system("adb shell monkey -p {} 1".format(package))


if __name__ == "__main__":
    setup_logging()
    main()