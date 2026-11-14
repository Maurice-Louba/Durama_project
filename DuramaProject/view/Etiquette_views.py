from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import Etiquette
from ..serializer import EtiquetteSerailized


# (nom historique « creerAttribut » conservé : il est référencé dans urls.py)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def creerAttribut(request):
    data = EtiquetteSerailized(data=request.data)
    if data.is_valid():
        data.save()
        return Response(data.data, status=status.HTTP_201_CREATED)
    return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def TousEtiquette(request):
    etiquettes = Etiquette.objects.all().order_by('name')
    etiquettesSeria = EtiquetteSerailized(etiquettes, many=True)
    return Response(etiquettesSeria.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def detailEtiquette(request, pk):
    try:
        etiquette = Etiquette.objects.get(pk=pk)
    except Etiquette.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    etiquetteSerial = EtiquetteSerailized(etiquette)
    return Response(etiquetteSerial.data)
