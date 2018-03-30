'''
Utility functions
'''

import os

def unset_proxy():
    os.system("unset http_proxy")
    os.system("unset https_proxy")
