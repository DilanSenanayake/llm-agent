from django.urls import path

from chat import views

app_name = "chat"

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload_documents, name="upload"),
    path("documents/remove/", views.remove_document, name="remove_document"),
    path("workspace/clear/", views.clear_workspace_view, name="clear_workspace"),
    path("settings/", views.update_settings, name="settings"),
    path("api/chat/stream/", views.chat_stream, name="chat_stream"),
]
