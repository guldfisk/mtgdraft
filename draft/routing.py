from django.conf.urls import url

from draft import consumers


websocket_urlpatterns = [
    url('^ws/draft/(?P<draft_id>\w+)/$', consumers.DraftConsumer),
]
