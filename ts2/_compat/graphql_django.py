import json

from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseNotAllowed)
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from graphene_django.views import GraphQLView, HttpError, graphene_settings


class GraphQLView_(GraphQLView):
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        try:
            if request.method.lower() not in ("get", "post"):
                raise HttpError(
                    HttpResponseNotAllowed(
                        ["GET", "POST"], "GraphQL only supports GET and POST requests."
                    )
                )

            # Monkey patch
            # https://datatracker.ietf.org/doc/html/rfc7231#section-4.3.1
            # Ignore body on GET (to avoid JSON decode error)
            if request.method == 'POST':
                data = self.parse_body(request)
            else:
                data = {}
            show_graphiql = self.graphiql and self.can_display_graphiql(request, data)

            if show_graphiql:
                return self.render_graphiql(
                    request,
                    # Dependency parameters.
                    whatwg_fetch_version=self.whatwg_fetch_version,
                    whatwg_fetch_sri=self.whatwg_fetch_sri,
                    react_version=self.react_version,
                    react_sri=self.react_sri,
                    react_dom_sri=self.react_dom_sri,
                    graphiql_version=self.graphiql_version,
                    graphiql_sri=self.graphiql_sri,
                    graphiql_css_sri=self.graphiql_css_sri,
                    subscriptions_transport_ws_version=self.subscriptions_transport_ws_version,
                    subscriptions_transport_ws_sri=self.subscriptions_transport_ws_sri,
                    # The SUBSCRIPTION_PATH setting.
                    subscription_path=self.subscription_path,
                    # GraphiQL headers tab,
                    graphiql_header_editor_enabled=graphene_settings.GRAPHIQL_HEADER_EDITOR_ENABLED,
                )

            if self.batch:
                responses = [self.get_response(request, entry) for entry in data]
                result = "[{}]".format(
                    ",".join([response[0] for response in responses])
                )
                status_code = (
                    responses
                    and max(responses, key=lambda response: response[1])[1]
                    or 200
                )
            else:
                result, status_code = self.get_response(request, data, show_graphiql)

            return HttpResponse(
                status=status_code, content=result, content_type="application/json"
            )

        except HttpError as e:
            response = e.response
            response["Content-Type"] = "application/json"
            response.content = self.json_encode(
                request, {"errors": [self.format_error(e)]}
            )
            return response

    @staticmethod
    def get_graphql_params(request, data):
        if request.method == 'GET':
            query = request.GET.get("query")
            variables = request.GET.get("variables")
        else:
            query = data.get("query")
            variables = data.get("variables")
        id = request.GET.get("id") or data.get("id")

        if variables and isinstance(variables, str):
            try:
                variables = json.loads(variables)
            except Exception:
                raise HttpError(HttpResponseBadRequest("Variables are invalid JSON."))

        operation_name = request.GET.get("operationName") or data.get("operationName")
        if operation_name == "null":
            operation_name = None

        return query, variables, operation_name, id
