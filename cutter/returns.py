from smiler.instrumenting.apkil.insnnode import InsnNode

constructor_ins1 = InsnNode(r"invoke-direct/range {p0 .. p0}, Ljava/lang/Object;-><init>()V")
constructor_ins2 = InsnNode("return-void")
default_constructor_insns = [constructor_ins1, constructor_ins2]

ret_obj_ins1 = InsnNode(r"const/4 v0, 0x0")
ret_obj_ins2 = InsnNode(r"return-object v0")
default_ret_object_insns = [ret_obj_ins1, ret_obj_ins2]

ret_zero_ins1 = InsnNode(r"const/4 v0, 0x0")
ret_zero_ins2 = InsnNode(r"return v0")
default_ret_zero_insns = [ret_zero_ins1, ret_zero_ins2]

ret_wide_ins1 = InsnNode(r"const-wide v0, 0x0")
ret_wide_ins2 = InsnNode(r"return-wide v0")
default_ret_wide_insns = [ret_wide_ins1, ret_wide_ins2]


basic_returns = {
    "V": [InsnNode("return-void")],
    'Z': default_ret_zero_insns,
    'B': default_ret_zero_insns,
    'S': default_ret_zero_insns,
    'C': default_ret_zero_insns,
    'I': default_ret_zero_insns,
    'J': default_ret_wide_insns,
    'F': default_ret_zero_insns,
    'D': default_ret_wide_insns
}


def set_defaults(method, ret_type):
    if ret_type in basic_returns:
        method.insns = basic_returns[ret_type]
    else:
        method.insns = default_ret_object_insns
    method.labels = {}


def set_default_constructor_for(method):
    method.insns = default_constructor_insns
    method.labels = {}


def get_return_type(descriptor):
    index = descriptor.rfind(')')+1
    rtype = descriptor[index:]
    return rtype
