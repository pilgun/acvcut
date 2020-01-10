import os
import sys
import yaml
import logging
import argparse

from logging import config as logging_config
from smiler.config import config
from smiler import reporter

def setup_logging():
    with open(config.logging_yaml) as f:
        logging_config.dictConfig(yaml.safe_load(f.read()))





def main():
    pickle = r"C:\projects\droidmod\acvcut\wd\metadata\app.pickle"
    ec = r"C:\projects\droidmod\acvcut\reports\original_io.pilgun.multidexapp\ec_files\onstop_coverage_1578628898500.ec"
    decompiled_app_dir = r"C:\projects\droidmod\acvcut\wd\apktool"
    smalitree = reporter.get_covered_smalitree([ec], pickle)
    
    load_smalitree(ec)
    cut_smali()
    build_app()


if __name__ == "__main__":
    setup_logging()
    main()