import os, sys
import acvcut
from cutter import invokes
from cutter import methods
from cutter import classes


smalitree = acvcut.load_pickle(acvcut.cut_smalitree_path)

# #invokes.get_references(smalitree)
# classes.remove_not_covered(smalitree)

# acvcut.save_smali(acvcut.smali_path, smalitree, acvcut.package)
# acvcut.build_apk(acvcut.out_apk)
# acvcut.test_apk(acvcut.out_apk, acvcut.package)
