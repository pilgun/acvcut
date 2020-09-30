import re, sys
from operator import attrgetter

from label_block import LBlock
from smiler.instrumenting.apkil.insnnode import InsnNode

# matched examples
#.catch Landroid/content/res/Resources$NotFoundException; {:try_start_0 .. :try_end_0} :catch_0
#if-ne v4, v5, :cond_5
#goto/16 :goto_a
labels_rx = r'^(?:goto[/1632]{0,3}|if-[a-z]*|\.catch)\s(?:(?:.*\s{:(?P<trystart>\w+)\s\.\.\s:(?P<tryend>\w+)}\s)|(?:(?:[vp]\d+,\s?)+))?:(?P<label>\w+)$'

def remove_blocks_from_selected_method(smalitree):
    for cl in smalitree.classes:#[518:519]
        # if cl.name != "Landroidx/coordinatorlayout/widget/CoordinatorLayout$LayoutParams;":#"Landroidx/core/view/ViewConfigurationCompat;":#"Lme;":#"Lcom/google/firebase/iid/ad;":#"Lkw;": #"Lcom/crashlytics/android/core/CrashlyticsCore;": #"Lme;":
        #     continue
        for m in cl.methods:
            # if m.descriptor != "<init>(Landroid/content/Context;Landroid/util/AttributeSet;)V":
            #     continue
            if m.called:# and m.descriptor == "<init>(Landroid/content/Context;Landroid/util/AttributeSet;)V":
                #print("{}: {}".format(i, m.descriptor))
                #if not m.synchronized:
                #if m.descriptor == "d(Landroid/content/Intent;)V":#"onStartCommand(Landroid/content/Intent;II)I":
                #if m.synchronized:
                remove_blocks(m)
                # if m.synchronized and not is_monitor_enter_covered(m):
                #     remove_blocks(m)
                #     m.tries = []


def remove_blocks(method):
    #if method.descriptor == "a(I[B)Z":
    #  clean_tries(method)
    if method.synchronized:
        remove_single_not_called_try(method)
    #remove_not_called_tries(method)
    align_tries(method)
    select_covered_l_blocks(method)
    remove_ifs(method)
    update_tries(method)
    remove_extra_tries(method)
    #remove_catchs(method)
    remove_array_data(method)
    merge_goto(method)
    clean_switch(method)

# def clean_tries(method):
#     for tr in method.tries:
#         tr.end.

def align_tries(method):
    ''' Puts try_start towards first executed instruction if the label appeared in
    not covered block, but try_end was executed'''
    for tr in method.tries:
        if not tr.start.covered and tr.end.covered:
            i = tr.start.index
            while not method.insns[i].covered and i < tr.end.index:
                i += 1
            tr.start.index = i
            tr.start.covered = True


def remove_single_catch_ins(catch_line, label_index, label_name, insns, labels):
    '''Removes single catch instruction under try_end_n label.'''
    for c_ins in insns[label_index:label_index+len(labels[label_name].tries)]:
        if c_ins.buf == catch_line:
            insns.remove(c_ins)
            break

def remove_single_not_called_try(method): #this is only for sync method
    # remove the whole try if no catches executed. Otherwise leave as it is.
    for tr in method.tries[:]:
        if not tr.handler.covered and tr.end.name in method.labels:
            keep_tr = any([tr_.handler.covered for tr_ in method.labels[tr.end.name].tries])
            if not keep_tr:
                tr_index = tr.end.index
                remove_single_catch_ins(tr.buf, tr.end.index, tr.end.name, method.insns, method.labels)
                method.labels[tr.end.name].tries.remove(tr)
                if len(method.labels[tr.end.name].tries) == 0:
                    method.labels.pop(tr.end.name)
                    method.labels.pop(tr.start.name)
                method.tries.remove(tr)
                recalculate_label_indexes(method.labels, tr_index, tr_index+1)


def remove_not_called_tries(method):
    #if method.descriptor == "doInBackground()Ljava/lang/Void;":
    for tr in method.tries[:]:
        if not tr.handler.covered:
            tr_index = tr.end.index
            remove_single_catch_ins(tr.buf, tr.end.index, tr.end.name, method.insns, method.labels)
            method.labels[tr.end.name].tries.remove(tr)
            if len(method.labels[tr.end.name].tries) == 0:
                if tr.end.name in method.labels:
                    method.labels.pop(tr.end.name)
                if tr.start.name in method.labels:
                    method.labels.pop(tr.start.name)
            method.tries.remove(tr)
            recalculate_label_indexes(method.labels, tr_index, tr_index+1)
    

def remove_extra_tries(method):
    #if method.descriptor == "doInBackground()Ljava/lang/Void;":
    for tr in method.tries[:]:
        if tr.handler.name not in method.labels:
            tr_index = tr.end.index
            remove_single_catch_ins(tr.buf, tr.end.index, tr.end.name, method.insns, method.labels)
            method.labels[tr.end.name].tries.remove(tr)
            if len(method.labels[tr.end.name].tries) == 0:
                if tr.end.name in method.labels:
                    method.labels.pop(tr.end.name)
                if tr.start.name in method.labels:
                    method.labels.pop(tr.start.name)
            method.tries.remove(tr)
            recalculate_label_indexes(method.labels, tr_index, tr_index+1)
    

def update_tries(method):
    '''Synchronizing method tries with labels.tries.'''
    #if method.descriptor == "doInBackground()Ljava/lang/Void;":
    for tr in method.tries[:]:
        if tr.end.name not in method.labels:
            if tr.start.name in method.labels:
                method.labels.pop(tr.start.name)
            method.tries.remove(tr)
        elif tr.start.name not in method.labels:
            method.labels.pop(tr.end.name)
        

def clean_switch(method):
    if is_switch_in(method):
        for i, ins in enumerate(method.insns[:]):
            if ins.opcode_name.startswith("packed-switch"):
                j_start = method.insns.index(ins)+1
                if j_start < len(method.insns):
                    current = method.insns[j_start]
                    if has_label_by_index(method.labels, j_start):
                        continue
                    if current.covered:
                        continue
                    if current.cover_code > -1 and not current.covered:
                        if current.opcode_name.startswith("invoke") and method.insns[j_start+1].covered:
                            continue
                        j_end = j_start
                        while j_end < len(method.insns) and \
                            not has_label_by_index(method.labels, j_end) and \
                            not method.insns[j_end].opcode_name.startswith("goto") and \
                            not method.insns[j_end].opcode_name.startswith("return"):
                                j_end += 1
                        del method.insns[j_start:j_end]
                        recalculate_label_indexes(method.labels, j_start, j_end)


def is_switch_in(method):
    for l in method.labels.values():
        if l.switch != None and l.switch.type_ == ".packed-switch":
            return True
    return False


class GotoLabel(object):
    def __init__(self, label):
        self.label = ""
        self.indexes = []


def scan_gotos(method):
    references = {}
    for i, insn in enumerate(method.insns):
        if insn.buf.startswith("goto") or insn.buf.startswith("if-"):
            l_index = insn.buf.rfind(':') + 1
            label = insn.buf[l_index:]
            #label = insn.buf.split()[1][1:]
            if label not in references:
                references[label] = []
            references[label].append(i)
    return references


def merge_goto(method):
    gotos = scan_gotos(method)
    rm_labels = []
    rm_insns = set()

    for lb, indexes in gotos.items():
        if lb not in method.labels:
            for ind in indexes:
                rm_insns.add(ind)
        if lb in method.labels and method.labels[lb].index-1 in indexes:
            rm_insns.add(method.labels[lb].index-1)
            if len(indexes) == 1:
                rm_labels.append(lb)
    for lb in rm_labels:
        del method.labels[lb]
    for i in sorted(list(rm_insns), reverse=True):
        del method.insns[i]
    recalculate_labels_by_array(method.labels, rm_insns)


def recalculate_labels_by_array(m_labels, rm_insns_set):
    labels = sorted(m_labels.values(), key=attrgetter('lid'))
    i = 0
    rm_insns = sorted(list(rm_insns_set))
    for l in labels:
        while i < len(rm_insns) and rm_insns[i] < l.index:
            i += 1
        m_labels[l.name].index -= i


def get_referenced_array_labels(method):
    labels = set()
    for ins in method.insns:
        if ins.opcode_name == "fill-array-data":
            index = ins.buf.rfind(':')
            label = ins.buf[index+1:]
            labels.add(label)
    return labels


def remove_array_data(method):
    referenced_array_labels = get_referenced_array_labels(method)
    array_labels = set([l.name for l in method.labels.values() if l.array_data])
    to_remove = array_labels - referenced_array_labels
    for l_name in to_remove:
        method.labels.pop(l_name)


def first_insn_is_covered(insns):
    if insns[0].covered:
        return True
    if insns[0].buf.startswith('invoke'):
        return insns[1].covered
    return False


def get_label_blocks(method):
    label_blocks = []
    first_covered = first_insn_is_covered(method.insns)
    block = LBlock(0, first_covered, [])
    for label in sorted(method.labels.values(), key=attrgetter('lid')):
        if label.index != block.start_i:
            block.end_i = label.index
            label_blocks.append(block)
            is_switch = label.switch != None
            is_array = label.array_data != None
            block = LBlock(label.index, 
                label.covered, 
                [label.name], 
                is_switch=is_switch,
                is_array=is_array)
        else:
            block.labels.append(label.name)
        if label.name.startswith("try_start_") and label.covered:
            block.is_try = True
        if label.name.startswith("try_end_") and method.labels[label.name.replace("end", "start")].covered:
            block.is_try = True
    block.end_i = len(method.insns)
    label_blocks.append(block)
    return label_blocks


def mark_synchronized_not_covered_lblocks(lblocks, method):
    for lb in lblocks:
        if not lb.covered and not lb.is_array and not lb.is_switch:
            if (method.insns[lb.start_i].opcode_name == "move-exception" and \
                method.insns[lb.start_i+1].opcode_name == "monitor-exit") or \
                (method.insns[lb.start_i].opcode_name == "monitor-exit" and \
                method.insns[lb.start_i-1].opcode_name == "move-exception"):
                lb.monitor_exit = True


def select_covered_l_blocks(method):
    lblocks = get_label_blocks(method)
    if method.synchronized:
        mark_synchronized_not_covered_lblocks(lblocks, method)
    insns = []
    labels = {}
    for lb in lblocks:
        if lb.covered or lb.is_switch or lb.is_array or lb.monitor_exit or lb.is_try:
            for ln in lb.labels:
                method.labels[ln].index = len(insns)
                labels[ln] = method.labels[ln]
                if lb.is_switch:
                    adjust_switch(labels, ln)
            insns.extend(method.insns[lb.start_i:lb.end_i])
    if len(insns) == 0 and len(method.insns) > 0:
        last_insn = method.insns[-1]
        if last_insn.buf.startswith("return"):
            insns.append(last_insn)
        else:
            for insn in reversed(method.insns):
                if insn.buf.startswith("return"):
                    insns.append(insn)
    method.insns = insns
    method.labels = labels


def adjust_switch(labels, ln):
    sw = labels[ln].switch
    if sw.type_ == ".packed-switch":
        packed_labels = []
        last_pl = ""
        for pl in sw.packed_labels:
            if pl[1:] in labels:
                packed_labels.append(pl)
                last_pl = pl
            else: #copy the last found labels instead of removing (impacts execution logic)
                packed_labels.append(last_pl)
        # if labels in the begining were removed, find the first existing and copy
        for i, pl in enumerate(packed_labels):
            if pl:
                break
        for j in range(0, i):
            packed_labels[j] = packed_labels[i]
        sw.packed_labels = packed_labels
    else:
        sparse_dict = {}
        for k, v in sw.sparse_dict.items():
            if v in labels:
                sparse_dict[k] = v
        sw.sparse_dict = sparse_dict
    sw.reload()


def remove_ifs(method):
    lock = False
    start_ = 0
    end_ = 0
    i = 0
    while i < len(method.insns):
        insn = method.insns[i]
        if lock and has_label_by_index(method.labels, i):
            end_ = i
            del method.insns[start_+1:end_]
            recalculate_label_indexes(method.labels, start_+1, end_)
            i -= end_ - start_ + 1
            lock = False
            continue
        if not lock and insn.opcode_name.startswith('if-'):
            lbl_name = insn.buf[insn.buf.rfind(':')+1:]
            if insn.covered:
                if lbl_name not in method.labels:
                    del method.insns[i:i+1]
                    recalculate_label_indexes(method.labels, i, i+1)
                    continue
            else:
                method.insns[i] = InsnNode("goto/32 :{}".format(lbl_name))
                start_ = i
                lock = True
        i += 1


def get_tryend_labels(method):
    tryends = []
    i = 0
    tryend_lmd = lambda x: "try_end_{}".format(hex(i)[2:])
    tryend_name = tryend_lmd(i)
    while tryend_name in method.labels:
        tryends.append(tryend_name)
        i += 1
        tryend_name = tryend_lmd(i)
    return tryends


def get_sequential_catches(insns, i):
    catches_indexes = []
    while insns[i].buf.startswith(".catch"):
        catches_indexes.append(i)
        i += 1
    return catches_indexes

# def catchs_groupby_tryend(to_remove):
#     tryend_dict = {}
#     for tr in to_remove:
#         tryend_dict[tr.]


# #def sync

# def remove_catchs2(method):
#     sync_method_n_label_tries(method)
#     to_remove = []
#     for tr in method.tries:
#         if tr.handler.name not in method.labels:
#             to_remove.append(tr)
#     groupped = catchs_groupby_tryend(to_remove)


def remove_catchs(method):
    # when code in the method is executed without exceptions, then remove .catch
    # instruction together with :try_start_ and :try_end_ labels
    tryends = get_tryend_labels(method)
    for tr in tryends:
        try_lbl = method.labels[tr]
        if try_lbl.covered:
            catch_indexes = get_sequential_catches(method.insns, try_lbl.index)
            rm_indexes = []
            try_start = method.insns[catch_indexes[0]].buf.split()[-4][2:]
            for ci in catch_indexes:
                catch_str_index = method.insns[ci].buf.rfind(':')
                catch_name = method.insns[ci].buf[catch_str_index+1:]
                if catch_name not in method.labels:
                    rm_indexes.append(ci)
            if len(rm_indexes) == len(catch_indexes):
                del method.labels[try_start]
                del method.labels[tr]
            for i in reversed(rm_indexes):
                del method.insns[i]
            recalculate_label_indexes(method.labels, catch_indexes[0], catch_indexes[0]+len(rm_indexes))


def recalculate_label_indexes(labels, start_, end_):
    d = end_ - start_
    if d == 0:
        return
    for (k, v) in labels.items():
        if v.index >= end_:
            v.index -= d


def get_referenced_labels(method):
    labels = set()
    for i, ins in enumerate(method.insns):
        if (ins.buf.startswith("goto") or ins.buf.startswith("if")
                or ins.buf.startswith(".catch")) and branch_ins_executed(
                    method, i):
            lbl_match = re.match(labels_rx, ins.buf)
            if lbl_match:
                labels.add(lbl_match.group("label"))
                if lbl_match.group("trystart"):
                    labels.add(lbl_match.group("trystart"))
                    labels.add(lbl_match.group("tryend"))
    return labels


def branch_ins_executed(method, i):
    if i == 0 and method.covered:
        return True
    if method.insns[i].covered:
        return True
    lbls = get_labels_by_index(method.labels, i)
    if lbls and lbls[0].covered:  #both labels covered
        return True
    if not lbls and method.insns[i - 1].covered:
        return True
    return False


def has_covered_lbl(labels, index):
    for (k, v) in labels.items():
        if v.index == index:
            return v.covered
    return False


def has_label_by_index(labels, index):
    for (k, v) in labels.items():
        if v.index == index:
            return True
    return False


def get_labels_by_index(labels, index):
    found_labels = []
    for k, l in labels.items():
        if l.index == index:
            found_labels.append(l)
    return found_labels


def is_monitor_enter_covered(method):
    for ins in method.insns:
        if ins.opcode_name.startswith("monitor-enter") and ins.covered:
            return True
    return False