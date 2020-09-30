import os, sys
import returns
from smiler.instrumenting.apkil.constants import BASIC_TYPES


def clean_not_executed_methods(smalitree):
    stub_methods = set()
    for cl in smalitree.classes:
        for m in cl.methods:
            if m.is_constructor and not m.called:
                stub(m)
                full_name = "{}->{}".format(cl.name, m.descriptor)
                stub_methods.add(full_name)
            if not m.is_constructor and not m.called:# and not m.synchronized:
                ret_type = returns.get_return_type(m.descriptor)
                stub(m, ret_type)
                full_name = "{}->{}".format(cl.name, m.descriptor)
                stub_methods.add(full_name)
    return stub_methods


def remove_static(smalitree):
    i = 0
    for cl in smalitree.classes:
        for m in cl.methods[:]:
            if not m.called and "static" in m.access:
                cl.methods.remove(m)
                i += 1
    print("{} static methods removed".format(i))


def stub(method, ret_type=None):
    method.labels = {}
    method.tries = []
    method.insns = []
    if ret_type:
        returns.set_defaults(method, ret_type)
    else:
        returns.set_default_constructor_for(method)
    method.ignore = True