import os

def _get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += _get_dir_size(entry.path)
    return total

# switch drives to save to if next acquisition won't fit on current drive
def _get_save_dir(buffer_dir):
    # get accounting of current drive space
    for save_dir in self.save_directories.keys():
        free_space = shutil.disk_usage(save_dir)[2]
        self.save_directories[save_dir] = free_space
    acq_size = self._get_dir_size(buffer_dir)
    n = 0
    save_dirs = list(self.save_directories.keys())
    while True:
        if acq_size > self.save_directories[save_dirs[n]]:
            n += 1
            continue
        else:
            final_save_dir = save_dirs[n]
            break
    return final_save_dir

def data_transfer(self,filename):
    def _move_files(start_dir,target_dir,filename):
        files = os.listdir(start_dir)
        for f in files:
            if filename in f:
                try:
                    shutil.move(start_dir + f, target_dir + f)
                except:
                    continue
            else:
                continue
    start_folder = self.default_dir
    print(start_folder)
    self._clean_folder(start_folder)
    save_dir = self._get_save_dir(start_folder)
    #self.th = threading.Thread(target=_move_files, args=(start_folder,save_dir,filename))
    #self.th.start() # we'll wait for this thread to be complete by the time we get to our next imaging sesh