import time
import acvcut
from cutter import methods
from cutter import invokes

start = time.time()

smalitree = acvcut.load_pickle(acvcut.cut_smalitree_path)
invokes.remove_methods_by_invokes(smalitree)
#methods.remove_static(smalitree)
acvcut.save_smali(acvcut.smali_path, smalitree, acvcut.package)
acvcut.build_apk(acvcut.out_apk)
acvcut.test_apk(acvcut.out_apk, acvcut.package)

end = time.time()
print("--- {} sec ---".format(end-start))
