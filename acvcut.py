import os
import sys
import yaml
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





def main():
    pickle = r"C:\projects\droidmod\acvcut\wd\metadata\app.pickle"
    ec = r"C:\projects\droidmod\acvcut\reports\original_io.pilgun.multidexapp\ec_files\onstop_coverage_1578628898500.ec"
    decompiled_app_dir = r"C:\projects\droidmod\acvcut\wd\orig_apktool"
    smalitree = reporter.get_covered_smalitree([ec], pickle)
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

    instrumenter = instrumenting.smali_instrumenter.Instrumenter(smalitree, "method", "io.pilgun.multidexapp")
    smali_path = os.path.join(decompiled_app_dir, "smali")
    instrumenter.save_instrumented_smali(smali_path, instrument=False)
    apktool = ApktoolInterface(javaPath = config.APKTOOL_JAVA_PATH,
                               javaOpts = config.APKTOOL_JAVA_OPTS,
                               pathApktool = Libs.APKTOOL_PATH,
                               jarApktool = Libs.APKTOOL_PATH)
    out_apk_raw = r"C:\projects\droidmod\acvcut\wd\short_raw.apk"
    out_apk = r"C:\projects\droidmod\acvcut\wd\short.apk"
    smiler.build_apk(apktool, decompiled_app_dir, out_apk_raw)
    smiler.sign_align_apk(out_apk_raw, out_apk)
    os.remove(out_apk_raw)
    smiler.uninstall("io.pilgun.multidexapp")
    smiler.install(out_apk)
    os.system("adb shell monkey -p io.pilgun.multidexapp 1")



if __name__ == "__main__":
    setup_logging()
    main()