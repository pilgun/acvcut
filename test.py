import os, re, sys
import acvcut
from cutter import invokes
from cutter import methods
from cutter import classes


ins_examples = [
    r"check-cast v0, Landroid/support/v7/widget/Toolbar$LayoutParams;",
    r"instance-of p0, p0, Landroid/support/v7/widget/VectorEnabledTintResources;",
    r"new-instance v0, Landroid/support/v7/widget/TooltipCompatHandler$2;",
    r"new-array p1, p1, [I",
    r"new-array v2, v2, [Ljava/lang/Class;",
    r"filled-new-array {v0, v1, v2}, [Ljava/lang/String;",
    r"iget v1, v7, Landroid/support/v7/widget/Toolbar;->mTitleMarginEnd:I",
    r"iget-object v0, v7, Landroid/support/v7/widget/Toolbar;->mTitleTextView:Landroid/widget/TextView;",
    r"sget-object v0, Landroid/support/v7/widget/ViewUtils;->sComputeFitSystemWindowsMethod:Ljava/lang/reflect/Method;",
    r"sget v0, Landroid/os/Build$VERSION;->SDK_INT:I",
    r"invoke-direct {p0}, Ljava/lang/Object;-><init>()V",
    r"invoke-static {p0}, Landroid/support/v4/view/ViewCompat;->getLayoutDirection(Landroid/view/View;)I",
    r"invoke-virtual {v2, v1}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z",
    r"invoke-static {}, Landroid/support/v7/app/AppCompatDelegate;->isCompatVectorFromResourcesEnabled()Z",
    r"iput-object p1, p0, Landroid/support/v7/widget/AppCompatTextView;->mTextHelper:Landroid/support/v7/widget/AppCompatTextHelper;",
    r"iput v0, p0, Landroid/support/v7/widget/AppCompatTextViewAutoSizeHelper;->mAutoSizeTextType:I",
]



#smalitree = acvcut.load_pickle(acvcut.cut_smalitree_path)
# classes.get_mentioned(smalitree, "iput")
# counter = 0
# c2 = 0
# for cl in smalitree.classes:
#     for m in cl.methods:
#         for ins in m.insns:
#             res = re.search(classes.ref_only, ins.buf)
#             if res:
#                 ref = res.group("ref")
#                 if not ref.startswith("L"):
#                     print(ref)
#                     c2+=1
#                 counter +=1
# print("c2: "+str(c2))
# print("counter: " + str(counter))

counter = 0
refs = []
for ins in ins_examples:
    res = re.search(classes.ref_ins_regex, ins)
    if res:
        #print("YES " + res.group())
        field = res.group("field")
        meth = res.group("meth")
        arg = res.group("arg")
        # print(ref)
        counter += 1
        if arg:
            print("ARG: " + arg)
        # if meth:
        #     print("METH: " + meth)
        # if field:
        #     print("FIELD: " + field)
        refs.append(res.group("cl_ref"))
        assert(res.group() == ins)
    else:
        print("NO " + ins)
print(len(ins_examples))
print(counter)
print(len(refs))
print("\n".join(refs))

# instructions having references to fields/classes
# const-string vAA, string@BBBB
# const-string/jumbo vAA, string@BBBBBBBB
# const-class vAA, type@BBBB
# check-cast vAA, type@BBBB	
# instance-of vA, vB, type@CCCC
# new-instance vAA, type@BBBB	
# new-array vA, vB, type@CCCC
# filled-new-array {vC, vD, vE, vF, vG}, type@BBBB
# filled-new-array/range {vCCCC .. vNNNN}, type@BBBB
# iget/iput #iinstanceop vA, vB, field@CCCC
# sget/sput #sstaticop vAA, field@BBBB
# invoke-kind {vC, vD, vE, vF, vG}, meth@BBBB
# invoke-kind/range {vCCCC .. vNNNN}, meth@BBBB
# invoke-polymorphic {vC, vD, vE, vF, vG}, meth@BBBB, proto@HHHH
# invoke-polymorphic/range {vCCCC .. vNNNN}, meth@BBBB, proto@HHHH	
# invoke-custom {vC, vD, vE, vF, vG}, call_site@BBBB
# invoke-custom/range {vCCCC .. vNNNN}, call_site@BBBB
# const-method-handle vAA, method_handle@BBBB
# const-method-type vAA, proto@BBBB

# type@
# const-class vAA, type@BBBB
# check-cast vAA, type@BBBB	
# instance-of vA, vB, type@CCCC
# new-instance vAA, type@BBBB	
# new-array vA, vB, type@CCCC
#filled-new-array 

# field@
# iget*
# iput*
# sget*
# sput*

# meth@
# invoke*

# proto@
# invoke-polymorphic
# const-method-type

# call_site@
# invoke-custom*