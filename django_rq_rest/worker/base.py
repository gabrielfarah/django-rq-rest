import os

from redis import StrictRedis
# Load python-rq libs
from rq import Connection, Worker


class BaseWorker:

    def __init__(self, queue_names, redis_url=os.environ.get('REDIS_URL')):
        """
        Creates a new BaseWorker instance. After init call work.
        :param queue_names: queue name or list of queue to listen to.
        :param redis_url: the Redis service uri
        """
        self.redis_url = redis_url
        self.queue_names = list(queue_names)

    @staticmethod
    def get_redis_client(redis_url):
        if not redis_url:
            raise RuntimeError(
                'Redis url must either be declares in the class constructor '
                'or as a enviroment variables with name "REDIS_URL".')
        if 'redis://' not in redis_url:
            return StrictRedis.from_url('redis://' + redis_url)
        return StrictRedis.from_url(redis_url)

    def work(self):
        redis_conn = self.get_redis_client(self.redis_url)
        with Connection(connection=redis_conn):
            qs = self.queue_names or ['default']
            worker = Worker(qs)
            worker.work()
