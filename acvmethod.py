import os, sys
import acvcut
from cutter import invokes
from cutter import methods


smalitree_orig = acvcut.load_pickle(acvcut.original_smalitree_path)
print("original loaded")
smalitree_cut = acvcut.load_pickle(acvcut.cut_smalitree_path)
print("cut loaded")

orig_invokes = invokes.get_invoke_static_methods(smalitree_orig)
print("orig direct invokes {}".format(len(orig_invokes)))
cut_invokes = invokes.get_invoke_static_methods(smalitree_cut)
print("cut direct invokes {}".format(len(cut_invokes)))
removed_invokes = orig_invokes - cut_invokes
print("diff: {} methods to be removed".format(len(removed_invokes)))

invokes.remove_methods_by_invokes(smalitree_cut, removed_invokes)
print("not invoked anymore methods were removed")

#sys.exit()
acvcut.save_smali(acvcut.smali_path, smalitree_cut, acvcut.package)
acvcut.build_apk(acvcut.out_apk)
acvcut.test_apk(acvcut.out_apk, acvcut.package)
