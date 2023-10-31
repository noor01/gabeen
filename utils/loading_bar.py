import time
from tqdm.auto import tqdm

def loading_bar_wait(seconds):
    for i in tqdm(range(int(seconds))):
        time.sleep(1)