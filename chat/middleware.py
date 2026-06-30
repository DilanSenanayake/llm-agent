from django.utils.deprecation import MiddlewareMixin

from chat.services import ensure_user_id


class WorkspaceSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.user_id = ensure_user_id(request)
