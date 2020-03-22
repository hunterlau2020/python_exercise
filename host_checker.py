# -*- coding: utf-8 -*
"""
    CopyLeft!2020 by hunter
    转载请保留此文件头
    用途：
        测试服务器网络层连通性能
            DNS
            PING
            TCP_CONNECT
            SEND
            RECV
"""
import ping
import simple_tcp_client
import dns.resolver
import time
import re
import copy
import functools


# 可以统计类成员方法执行速度的装饰器 decorator
def time_cal_decorator(stage_name):
    def inner_decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kw):
            self.FUNC_EXEC_TIME = self.config_dict['max_timeout']
            s_time = time.time()
            result = func(self, *args, **kw)
            self.FUNC_EXEC_TIME = (time.time() - s_time) * 1000
            #print 'stage[%s] Function [%s] run time is %.2f' % (stage_name, func.__name__, self.FUNC_EXEC_TIME)
            self.STAGE_TIME_DICT[stage_name] = self.FUNC_EXEC_TIME
            return result

        return wrapper

    return inner_decorator


class HostChecker(object):
    _CONNECT_TIMEOUT = 3
    _SEND_TIMEOUT = 3
    _RECV_TIMEOUT = 3
    _PING_TIMEOUT = 3
    _FAILED_TIME = 99999.0

    FUNC_EXEC_TIME = _FAILED_TIME
    STAGE_TIME_DICT = {"name_lookup": _FAILED_TIME, "connect": _FAILED_TIME, "start_transfer": _FAILED_TIME,
                       "send": _FAILED_TIME, "recv": _FAILED_TIME, "ping_delay": _FAILED_TIME,
                       "loss_percent": _FAILED_TIME, "address": "unknown"}

    def __init__(self, name_server, config_dict):

        self._name_server = name_server
        self.config_dict = copy.deepcopy(config_dict)
        if "send_timeout" not in self.config_dict:
            self.config_dict['send_timeout'] = self._SEND_TIMEOUT
        if "connect_timeout" not in self.config_dict:
            self.config_dict['connect_timeout'] = self._CONNECT_TIMEOUT
        if "recv_timeout" not in self.config_dict:
            self.config_dict['recv_timeout'] = self._RECV_TIMEOUT
        if "ping_timeout" not in self.config_dict:
            self.config_dict['ping_timeout'] = self._PING_TIMEOUT
        if "max_timeout" not in self.config_dict:
            self.config_dict['max_timeout'] = self._FAILED_TIME
        self._resolver = dns.resolver.Resolver(configure=False)
        self._resolver.nameservers = [self._name_server]

        send_data = ['f'] * 102400
        self._send_data_str = ''.join(send_data)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self._resolver

    @staticmethod
    def is_ipv4(addr):
        return bool(
            re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", addr))

    @staticmethod
    def is_ipv6(addr):
        return bool(re.match(r"^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$", addr, re.I))

    def init_stage_time_dict(self, host_name):
        for key in ("name_lookup", "connect", "start_transfer", "ping_delay", "loss_percent", "send", "recv"):
            self.STAGE_TIME_DICT[key] = self.config_dict['max_timeout']
        self.STAGE_TIME_DICT['address'] = host_name

    @time_cal_decorator("name_lookup")
    def check_dns_resolve(self, host_name):
        if self.is_ipv4(host_name) or self.is_ipv6(host_name):
            return host_name

        answer = self._resolver.query(host_name, 'A')

        if isinstance(answer[0], dns.rdtypes.IN.A.A):
            ip_address = answer[0].address
        elif isinstance(answer[0], dns.rdtypes.ANY.CNAME.CNAME):
            ip_address = 'CNAME: %s' % answer[0]
        else:
            ip_address = 'unknown type: %s' % answer[0]
        return ip_address

    @time_cal_decorator("ping_delay")
    def check_ping(self, address):
        """
        Send >count< ping to >dest_addr< with the given >timeout< and display
        the result.
        """
        ping_result = {"loss_percent": 0, "ping_delay": 0.0}
        # print "ping %s..." % address,
        success_count = 0
        total_count = 7
        delay_array = []
        for i in xrange(total_count):
            try:
                delay = ping.do_one(address, self.config_dict['ping_timeout'])
                if delay is None:
                    # print "failed. (timeout within %ssec.)" % timeout
                    continue
                else:
                    delay = delay * 1000
                    delay_array.append(delay)
                    success_count = success_count + 1

            except ping.socket.gaierror, e:
                print "failed. (socket error: '%s')" % e[1]
                break
        if len(delay_array) > 0:
            average = reduce(lambda x, y: x + y, delay_array) / len(delay_array)
            # print delay_array
        else:
            average = self.config_dict['max_timeout']
        loss_percent = (total_count - success_count) / total_count * 100
        ping_result['loss_percent'] = loss_percent
        ping_result['ping_delay'] = average
        # print ' total: %d , loss: %0.2f, delay: %0.3f' % (total_count, loss_percent, average)
        return ping_result

    @time_cal_decorator("connect")
    def _check_connect(self, client):
        return client.connect(self.config_dict['connect_timeout'])

    @time_cal_decorator("send")
    def _check_tcp_send(self, client, send_data):
        return client.send(send_data, self.config_dict['send_timeout'])

    @time_cal_decorator("recv")
    def _check_tcp_recv(self, client, recv_buf_len):
        return client.receive(recv_buf_len, self.config_dict['recv_timeout'])

    @time_cal_decorator("start_transfer")
    def check_tcp_transfer(self, address, port):

        with simple_tcp_client.TCPClient(address, port) as client:
            if self._check_connect(client) is True:
                print "connect [%s] ok" % address

                if self._check_tcp_send(client, self._send_data_str):
                    if self._check_tcp_recv(client, 10):
                        print "do_tcp_transfer ok"
                        return True
                    # else: # socket connection broken or Errno 10054 都说明服务器处理了请求
                    #    STAGE_TIME_DICT['recv'] = FAILED_TIME
                else:
                    self.STAGE_TIME_DICT['send'] = self.config_dict['max_timeout']
            else:
                # print "connect [%s] failed" % address
                self.STAGE_TIME_DICT['connect'] = self.config_dict['max_timeout']
        return False

    def whole_check(self, address, port):
        self.init_stage_time_dict(address)

        # 测试DNS解析速度
        self.STAGE_TIME_DICT['ip'] = address
        self.STAGE_TIME_DICT['ip'] = self.check_dns_resolve(address)
        address = self.STAGE_TIME_DICT['ip']

        # 测试ping
        if True:
            ping_result = self.check_ping(address)
            self.STAGE_TIME_DICT["ping_delay"] = ping_result['ping_delay']
            self.STAGE_TIME_DICT["loss_percent"] = ping_result['loss_percent']

        # 测试tcp连接速度
        if self.check_tcp_transfer(address, port) is False:
            self.STAGE_TIME_DICT['start_transfer'] = self.STAGE_TIME_DICT['connect'] + self.STAGE_TIME_DICT['send'] + \
                                                     self.STAGE_TIME_DICT['recv']

        return copy.deepcopy(self.STAGE_TIME_DICT)






