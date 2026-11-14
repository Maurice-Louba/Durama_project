"""
URL configuration for Durama project.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

admin.site.site_header = "Administration Durama"
admin.site.site_title = "Durama"
admin.site.index_title = "Gestion de la marketplace"

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include('DuramaProject.urls')),
]

# Documentation de l'API : publique en local, désactivée en production sauf SWAGGER_PUBLIC=1
if settings.SWAGGER_PUBLIC:
    schema_view = get_schema_view(
        openapi.Info(
            title="API BTP e-commerce",
            default_version='v1',
            description="Documentation interactive de l'API BTP",
        ),
        public=True,
        permission_classes=(permissions.AllowAny,),
        authentication_classes=[],
    )
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  # interface Swagger
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]

# Images (produits, profils, vendeurs). Avant, elles n'étaient servies qu'avec DEBUG=True :
# désactiver DEBUG en production aurait cassé toutes les images.
if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
