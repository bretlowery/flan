from flanexport import FlanExport, timeout_after
import os
import ast

try:
    from boto.sqs import connection
    from boto.sqs.message import Message
except:
    pass


class AWSSQS(FlanExport):

    def __init__(self, meta, config):
        name = self.__class__.__name__
        super().__init__(name, meta, config)

    @timeout_after(10)
    def prepare(self):
        aws_access_key_id = self._getsetting('aws_access_key_id', checkenv=True)
        aws_secret_access_key = self._getsetting('aws_secret_access_key', checkenv=True)
        is_secure = self._getsetting('is_secure', erroronnone=False, defaultvalue=True)
        port = self._getsetting('port', erroronnone=False)
        proxy = self._getsetting('proxy', erroronnone=False)
        proxy_port = self._getsetting('proxy_port', erroronnone=False)
        proxy_user = self._getsetting('proxy_user', erroronnone=False)
        proxy_pass = self._getsetting('proxy_pass', erroronnone=False)
        region = self._getsetting('region', erroronnone=False)
        path = self._getsetting('region', defaultvalue="/")
        security_token = self._getsetting('security_token', erroronnone=False)
        validate_certs = self._getsetting('region', defaultvalue=True)
        profile_name = self._getsetting('profile_name', erroronnone=False)
        queue_name = self._getsetting('queue_name', erroronnone=True, defaultvalue="flan")
        sqs_message_attributes = self._getsetting('sqs_message_attributes', erroronnone=False)
        if sqs_message_attributes:
            self.sqs_message_attributes = ast.literal_eval(sqs_message_attributes)
        else:
            self.sqs_message_attributes = {}
        try:
            self.conn = connection.SQSConnection(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    is_secure=is_secure,
                    port=port,
                    proxy=proxy,
                    proxy_port=proxy_port,
                    proxy_user=proxy_user,
                    proxy_pass=proxy_pass,
                    region=region,
                    path=path,
                    security_token=security_token,
                    validate_certs=validate_certs,
                    profile_name=profile_name
            )
            self.sender = self.conn.create_queue(queue_name, self._getsetting('timeout'))
        except Exception as e:
            self.logerr('Flan->%s connection to %s:%s failed: %s' %
                          (self.name, self.config["host"], self.config["port"], str(e)))
            os._exit(1)

    @timeout_after(10)
    def send(self, data):
        try:
            m = Message()
            m.message_attributes = self.sqs_message_attributes
            m.set_body(data)
            self.sender.write(m)
        except Exception as e:
            self.logerr('Flan->%s delivery failed: %s' % (self.name, str(e)))
            pass
        return

    @property
    def closed(self):
        return False

    @timeout_after(10)
    def close(self):
        try:
            self.conn.close()
        except:
            pass
        return