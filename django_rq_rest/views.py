import json

import django_rq
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.reverse import reverse_lazy
from rest_framework.views import APIView


class BaseAsyncView:
    """
    Base class for async kind of jobs. Exten this class if you need more
    flexibility of the logic inside.
    """
    FAILED_JOB = {"message": "Request failed to complete."}
    MISSING_JOB_ID = {
        "message": "The query param id must be present in request."
    }
    MISSING_JOB = {"message": "Invalid id"}
    EMPTY_JOB_RESULT = {
        "message": "Your request is currently being processed."
    }
    COMPLETED_JOB_RESULT = {
        "message": "Request completed"
    }
    BAD_REQUEST = {"message": "Invalid request"}

    def obtain_job_id(self, request):
        """
        Gets the "id" query param from the request
        :param request: the http request
        :return: the value of the query param "id" or a exception.
        """
        job_id = request.query_params.get('id', None)
        if job_id is None or job_id == "":
            raise ValidationError(
                self.MISSING_JOB_ID, code=status.HTTP_400_BAD_REQUEST)
        return job_id

    def get_job_response(self, job_id, queue_name):
        """

        :param job_id:
        :param queue_name:
        :return:
        """
        try:
            job_id = str(job_id)
            queue = django_rq.get_queue(queue_name)
            job = queue.fetch_job(job_id)
            if job:
                if job.is_failed:
                    raise ValidationError(
                        self.FAILED_JOB, code=status.HTTP_409_CONFLICT)
                else:
                    if job.result is None:
                        return Response(
                            self.EMPTY_JOB_RESULT, status=status.HTTP_200_OK)
                    else:
                        response = self.COMPLETED_JOB_RESULT
                        response['result'] = json.loads(job.result)
                        return Response(response, status=status.HTTP_200_OK)
            else:
                raise ValidationError(
                    self.MISSING_JOB, code=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            raise ValidationError(
                self.BAD_REQUEST, code=status.HTTP_400_BAD_REQUEST)

    def enqueue_job(
            self, queue_name, job_name, params, view_name, job_file='jobs',
            kwargs=None):
        """
        This function enqueue a new task.
        :param queue_name: The name of the queue to send the task to.
        :param job_file: The name of the remote python module with a function.
        :param job_name: The name of the remote function inside the file.
        :param params: The parameters of the remote function.
        :param view_name: The name of the REST view  endpoint.
        :param kwargs: Additional kwargs supported by django_rq in the
        enqueue function
        :return:
        """
        queue = django_rq.get_queue(queue_name)
        job = queue.enqueue('{}.{}'.format(job_file, job_name), ttl=43,
                            **params)
        if job.is_failed:
            return Response(
                self.FAILED_JOB, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            url = "{}?id={}".format(
                reverse_lazy(view_name, kwargs=kwargs), job.id)
            return Response({
                "message": "Request processed successfully",
                "url": url}, status=status.HTTP_202_ACCEPTED,
                headers={"Content-Location": url})


class AsyncView(APIView, BaseAsyncView):
    """
    A simple rest aync view utility. To create a instance of this view
    do the following:
        * Create a new view in your views.py adding this class to it.
        * Add the 5 obligatory attributes to the new view (job_file,
        queue_name, job_name, job_params, view_name).
        * Run your server and test.

    Example:

        class ImageClassifierView(AsyncView):
            renderer_classes = (JSONRenderer,)
            permission_classes = (IsAuthenticated,)

            job_file = 'jobs'
            queue_name = settings.SIMPLE_ML_QUEUE
            job_name = 'image_face_recognition'
            job_params = ['b64_image']
            view_name = 'face-recognition'
    """
    @property
    def queue_name(self):
        """
        This property is the name of the queue to send this job to.
        :return: The name of the queue to use.
        """
        raise NotImplementedError(
            "queue_name property should be set in async views "
            "and must be defined in settings.py")

    @property
    def job_file(self):
        """
        This property is the name of the file containing the function
        to be called from withing the worker process, usually this refers to
        "jobs" such that the name will be jobs.py.
        :return: The name of the function inside the worker jobs.py
        """
        raise NotImplementedError(
            "job_file property should be set in async views "
            "and must be a valid file inside of the worker")

    @property
    def job_name(self):
        """
        This property is the name of the function to be called from
        withing the worker process and is contained inside the jobs.py file.
        :return: The name of the function inside the worker jobs.py
        """
        raise NotImplementedError(
            "job_function_name property should be set in async views "
            "and must be a function inside the jobs.py file of the worker")

    @property
    def job_params(self):
        """
        This property is a list of parameters that must be contained in
        the JSON payload of the request.
        :return: The list of fields to validate the request against.
        """
        raise NotImplementedError(
            "job_params property should be set in async views "
            "and must be an expected parameter inside the worker function")

    @property
    def view_name(self):
        """
        This property represents the URL path of this view to be used as
        "name" in the urls.py.
        :return: The name of the view.
        """
        raise NotImplementedError(
            "view_name property should be set in async views "
            "and used in urls.py")

    def get(self, request):
        job_id = self.obtain_job_id(request)
        return self.get_job_response(job_id, self.queue_name)

    def post(self, request):
        params = {}
        for k in self.job_params:
            if k not in request.data:
                return Response({
                    "message": "Field {} must be set in the "
                               "request".format(k)
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                params[k] = request.data[k]
        return self.enqueue_job(
            self.queue_name, self.job_name, params, self.view_name,
            job_file=self.job_file)
