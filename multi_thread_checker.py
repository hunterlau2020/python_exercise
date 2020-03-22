# -*- coding: utf-8 -*
"""
    CopyLeft!2020 by hunter
    转载请保留此文件头
    用途：
        多线程并发测试服务器连通速率
"""
import host_checker
import fastthreadpool
import threading
import copy
from time import sleep


class MultiThreadChecker:

    def __init__(self, name_server, max_thread_num, config_dict, handler=None):
        self._max_thread_num = max_thread_num
        self._config_dict = copy.deepcopy(config_dict)
        self._result_list = []
        self._pool = None

    def __enter__(self):
        self._pool = fastthreadpool.Pool(self._max_thread_num)

        self.host_check_list = []
        for i in range(self._max_thread_num):
            self.host_check_list.append(host_checker.HostChecker('202.96.134.133', self._config_dict))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._pool:
            self._pool.shutdown()

    @staticmethod
    def do_check(address, port, checker):
        try:
            check_result = checker.whole_check(address, port)
            return check_result
        except Exception as e:
            print "do_check exception %s" % e
            return {}

    def update_check_result(self, result_dict):
        # should add lock?
        # print result_dict
        self._result_list.append(result_dict)

    def check_all(self, host_list):

        loop_count = 0
        for host in host_list:
            address = host['add']
            port = int(host['port'])
            checker = self.host_check_list[(loop_count % self._max_thread_num)]
            job_id = self._pool.submit_done(self.do_check, self.update_check_result, address, port, checker)

            loop_count += 1
            if loop_count > 30:
                break

        last_pending = self._pool.pending
        while self._pool.pending > 0:
            sleep(0.5)
            if last_pending != self._pool.pending:
                print "pending %d %d %d %d" % (self._pool.alive, self._pool.child_cnt, self._pool.busy, self._pool.pending)
                last_pending = self._pool.pending

        shutdown_result = self._pool.shutdown(1, True)
        del self._pool
        self._pool = None
        return copy.deepcopy(self._result_list)

