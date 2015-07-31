# -*- coding: utf-8 -*-
from gevent.pool import Pool
import logging
import time

CONCURRENCY = 200 # run 200 greenlets at once or whatever you want
pool = Pool(CONCURRENCY)
count = 0

def do_work_function(param1,param2, index):
   print "Index: ", index, "Result: ", param1 + param2



total_count = 10000
t = time.time()
for i in range(0, 10000):
    logging.info(count)
    pool.spawn(do_work_function, i * i, i + 1, i) # blocks here when pool size == CONCURRENCY

pool.join() #blocks here until the last 200 are complete

t = time.time() - t
print "Elasped Time: ", t / total_count

