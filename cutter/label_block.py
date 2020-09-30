
class LBlock(object):

    def __init__(self, start_i, covered, labels, end_i=0, is_switch=False, is_array=False):
        self.start_i = start_i
        self.covered = covered
        self.labels = labels
        self.end_i = end_i
        self.is_switch = is_switch
        self.is_array = is_array
        self.monitor_exit = False
        self.is_try = False