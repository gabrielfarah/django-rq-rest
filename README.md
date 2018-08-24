### Usage

##### 1. Create a new async rest view
First, we create a new viw inside our **`views.py`** file. 
```
from django_rq_rest.views import AsyncView

class ImageClassifierView(AsyncView):
    """
    This view receives a base 64 encoded image inside 
    the payload with key "b64_image" and the worker returns a 
    classification label.
    """
    renderer_classes = (JSONRenderer,)
    permission_classes = (IsAuthenticated,)

    job_file = 'jobs'
    queue_name = settings.ML_QUEUE # settings.py defined queue 
    job_name = 'image_face_recognition'
    job_params = ['b64_image']
    view_name = 'image-recognition'
```
We add it to our **`urls.py`** like any other view. 

```
urlpatterns = [
    ...
    url(r'^face-classifier/$', 
    ImageClassifierView.as_view(), name=ImageClassifierView.view_name)
    ...
```

In this example we selected that:
 1. We will have a **`jobs.py`** file in our worker.
 2. Inside our **`jobs.py`** file there will be a function called  **`image_face_recognition`**.
 3. The function **`image_face_recognition`** will have one parameter called **`b64_image`**. 
 4. This function will perform the task and return the result when polled.

##### 2. Creating the taks
Lets create and define **`jobs.py`** as our worker task.
```
import base64
import json
import awesome_custom_ml_lib

def image_face_recognition(b64_image):
    ... your code here ...
    return json.dumps(classified_img)
``` 
In this example what matters is that we have followed the conventions 
defined in the **`ImageClassifierView`** view.

##### 3. Creating the worker
To create the worker that listen to Redis, we create a file (in my case **`worker.py`**)
and we add the following:

```
from django_rq_rest.worker.base import BaseWorker
worker = BaseWorker('ml_queue', redis_url='localhost:6379/1')
worker.work()
```
once we run **`python worker.py`** we should start being able to run our service.
