from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/course/(?P<course_id>[0-9a-f-]+)/$', consumers.CourseProgressConsumer.as_asgi()),
] 