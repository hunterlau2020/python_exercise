# -*- coding: utf-8 -*
"""
    CopyLeft!2020 by hunter
    转载请保留此文件头
    用途：
        异步tcp client，基于python 2.7
"""

import socket, select
import errno


class TCPClient(object):
    def __init__(self, host, port,  handler=None):
        self.host = host
        self.port = port
        self.handler = handler
        self.sock_server = None

    def connect(self, timeout):
        try:
            self.sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_server.setblocking(False)
            err_code = self.sock_server.connect_ex((self.host, self.port))
            if err_code != errno.EINPROGRESS and err_code != errno.EWOULDBLOCK:
                print errno
                return False
            if err_code == 0:
                return True

            inputs = [self.sock_server]
            while True:
                infds, outfds, errfds = select.select(inputs, inputs, inputs, timeout)
                #timeout
                if len(infds) == 0 and len(outfds) == 0 and len(errfds) == 0:
                    return False
                if len(errfds) != 0:
                    return False
                if len(infds) != 0:
                    break
                if len(outfds) != 0:
                    break

            return True
        except Exception as e:
            print('Connect Error. %s' % e)
            return False

    def stop(self):
        if self.sock_server is not None:
            self.sock_server.close()

    def send(self, msg, timeout):
        try:
            outputs = [self.sock_server]
            total_sent = 0
            msg_len = len(msg)
            while total_sent < msg_len:
                infds, outfds, errfds = select.select([], outputs, outputs, timeout)
                #timeout
                if len(infds) == 0 and len(outfds) == 0 and len(errfds) == 0:
                    raise RuntimeError("timeout.")
                if len(outfds) != 0:
                    sent = self.sock_server.send(msg[total_sent:])
                    if sent == 0:
                        raise RuntimeError("socket connection broken")
                    total_sent = total_sent + sent
                if len(errfds) != 0:
                    raise RuntimeError("send exception.")
            return True
        except Exception as e:
            print('Send Error. %s' % e)
            return False

    def receive(self, pkg_max_len, timeout):
        try:
            chunks = []
            bytes_recd = 0
            inputs = [self.sock_server]
            while bytes_recd < pkg_max_len:
                infds, outfds, errfds = select.select(inputs, [], inputs, timeout)
                #timeout
                if len(infds) == 0 and len(outfds) == 0 and len(errfds) == 0:
                    raise RuntimeError("timeout.")
                if len(infds) > 0:
                    chunk = self.sock_server.recv(min(pkg_max_len - bytes_recd, 2048))
                    if chunk == '':
                        raise RuntimeError("socket connection broken")
                    chunks.append(chunk)
                    bytes_recd = bytes_recd + len(chunk)
                if len(errfds) != 0:
                    raise RuntimeError("send exception.")
            return ''.join(chunks)
        except Exception as e:
            print('Recv Error. %s' % e)
            return None

