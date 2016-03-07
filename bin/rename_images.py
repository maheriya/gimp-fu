#!/usr/bin/env python

import os
import sys

if False:
    src = "sup"
    tgt = "stairs_up"
else:
    src = "sdown"
    tgt = "stairs_dn"

ifiles = os.listdir(src)
idx = 1
for fname in ifiles:
    nfname = '{t}_{i:0>3}.jpg'.format(t=tgt, i=idx)
    print fname, " -> ", nfname
    os.system("cp {} {}".format(os.path.join(src, fname), os.path.join(tgt, nfname)))
    idx+=1

