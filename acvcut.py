import os
import sys
import yaml
import shutil
import logging
import argparse

from logging import config as logging_config
from smiler.config import config
from smiler import reporter
from smiler import instrumenting
from smiler.instrumenting.apktool_interface import ApktoolInterface
from smiler.libs.libs import Libs
from smiler import smiler

def setup_logging():
    with open(config.logging_yaml) as f:
        logging_config.dictConfig(yaml.safe_load(f.read()))

# def prepare_apktool_dir(apktool_dir, app_path):
#     apktool = r"c:\distr\android\apktool.jar"
#     cmd = "java -jar {} d {} -o {} -f".format(apktool, app_path, apktool_dir)
#     os.system(cmd)


def clean_smali_dir(smali_path, original_smali_path):
    if os.path.exists(smali_path):
        shutil.rmtree(smali_path)
    shutil.copytree(original_smali_path, smali_path)


def rm_file(path):
    if os.path.exists(path):
        os.remove(path)


def remove_not_covered_instructions(smalitree):
    i = 0
    j = 0
    insns_amount = lambda classes: sum([sum([len(m.insns) for m in cl.methods]) for cl in classes])
    insns_orig = insns_amount(smalitree.classes)
    print("insns: {}".format(insns_orig))
    for cl in smalitree.classes:
        for m in cl.methods:
            for insn in m.insns:
                if insn.covered:
                    m.insns.remove(insn)
    insns_new = insns_amount(smalitree.classes)
    print("insns: {}".format(insns_new))

    print("left classes: {}".format(len(smalitree.classes)))
    print("removed {} classes".format(i))
    print("removed {} methods, left {}".format(j, sum([len(cl.methods) for cl in smalitree.classes])))


def remove_methods_in_not_covered_classes(smalitree):
    i = 0
    j = 0

    for cl in smalitree.classes:
        if cl.not_covered():
            print("{} {}".format(cl.name, cl.covered()))
            for m in cl.methods:
                if m.not_covered():
                    cl.methods.remove(m)
                    j+=1
            #smalitree.classes.remove(cl)
            i += 1
    print("left classes: {}".format(len(smalitree.classes)))
    print("removed {} classes".format(i))
    print("removed {} methods, left {}".format(j, sum([len(cl.methods) for cl in smalitree.classes])))


def get_all_method_invokes(smalitree):
    invokes = set()
    for cl in smalitree.classes:
        for m in cl.methods:
            for insn in m.insns:
                if insn.opcode_name.startswith("invoke"):
                    invokes.add(insn.obj.method_desc)
    return invokes

def get_all_methods_desc(smalitree):
    signatures = set()
    for cl in smalitree.classes:
        for m in cl.methods:
            signatures.add("{}->{}".format(cl.name, m.descriptor))
    return signatures


def main():
    pickle = r"C:\projects\droidmod\acvcut\wd\metadata\app.pickle"
    ec = r"C:\projects\droidmod\acvcut\reports\original_io.pilgun.multidexapp\ec_files\onstop_coverage_1578628898500.ec"
    #app_path = r"C:\projects\droidmod\acvtool-benchmark\apks\simple_apps\app.apk"
    decompiled_app_dir = r"C:\projects\droidmod\acvcut\wd\orig_apktool"
    original_smali_path = r"C:\projects\droidmod\acvcut\wd\orig_apktool_copy\smali"
    out_apk_raw = r"C:\projects\droidmod\acvcut\wd\short_raw.apk"
    out_apk = r"C:\projects\droidmod\acvcut\wd\short.apk"
    smali_path = os.path.join(decompiled_app_dir, "smali")
    #clean_smali_dir(smali_path, original_smali_path)
    rm_file(out_apk)
    rm_file(out_apk_raw)
    
    smalitree = reporter.get_covered_smalitree([ec], pickle)
    invoked_methods = get_all_method_invokes(smalitree)
    defined_methods = get_all_methods_desc(smalitree)
    #print(methods_list)
    #print(len(methods_list))
    print(list(invoked_methods)[0])
    print(list(defined_methods)[0])
    print(len(invoked_methods))
    print(len(defined_methods))
    print("not called methods: {}".format(len(defined_methods - invoked_methods)))
    print("methods are not in app: {}".format(len(invoked_methods - defined_methods)))
    print("\n".join(sorted(list(invoked_methods))))
    
    #remove_not_covered_instructions(smalitree)
    #remove_methods_in_not_covered_classes(smalitree)
    # print(smalitree.classes[0].name)
    # print(smalitree.classes[0].methods[0].name)
    # print(smalitree.classes[0].methods[0].descriptor)
    # print(smalitree.classes[0].methods[0].insns[0].buf)
    # print(smalitree.classes[0].methods[0].insns[0].obj.method_desc)

    return

    instrumenter = instrumenting.smali_instrumenter.Instrumenter(smalitree, "method", "io.pilgun.multidexapp")
   
    instrumenter.save_instrumented_smali(smali_path, instrument=False)
    apktool = ApktoolInterface(javaPath = config.APKTOOL_JAVA_PATH,
                               javaOpts = config.APKTOOL_JAVA_OPTS,
                               pathApktool = Libs.APKTOOL_PATH,
                               jarApktool = Libs.APKTOOL_PATH)

    smiler.build_apk(apktool, decompiled_app_dir, out_apk_raw)
    smiler.sign_align_apk(out_apk_raw, out_apk)
    os.remove(out_apk_raw)
    smiler.uninstall("io.pilgun.multidexapp")
    smiler.install(out_apk)
    os.system("adb shell monkey -p io.pilgun.multidexapp 1")



if __name__ == "__main__":
    setup_logging()
    main()