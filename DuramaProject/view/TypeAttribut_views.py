from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import TypeAttribut
from ..serializer import TypeAttributSerialized


@swagger_auto_schema(
    method='post',
    request_body=TypeAttributSerialized,
    responses={
        201: TypeAttributSerialized,
        400: 'Bad Request'
    }
)
@api_view(['POST'])
@permission_classes([IsAdminUser])  # avant : aucune permission, n'importe qui pouvait créer
def faireUnTypeAttribut(request):
    data = TypeAttributSerialized(data=request.data)
    if data.is_valid():
        data.save()
        return Response(data.data, status=status.HTTP_201_CREATED)
    return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def VoirTousTypeAttribut(request):
    type_attribut = TypeAttribut.objects.all().order_by('nom')
    type_attributSeria = TypeAttributSerialized(type_attribut, many=True)
    return Response(type_attributSeria.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def detailUnTypeAttribut(request, pk):
    try:
        type_attribut = TypeAttribut.objects.get(pk=pk)
    except TypeAttribut.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    type_attributSeria = TypeAttributSerialized(type_attribut)
    return Response(type_attributSeria.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def changerTypeAttribut(request, pk):
    try:
        type_attribut = TypeAttribut.objects.get(pk=pk)
    except TypeAttribut.DoesNotExist:
        return Response({'error': 'type attribut non existante'}, status=status.HTTP_404_NOT_FOUND)

    data = TypeAttributSerialized(type_attribut, data=request.data, partial=(request.method == 'PATCH'))
    if data.is_valid():
        data.save()
        return Response(data.data, status=status.HTTP_200_OK)
    return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def SupprimerUnTypeAttribut(request, pk):
    try:
        type_attribut = TypeAttribut.objects.get(pk=pk)
    except TypeAttribut.DoesNotExist:
        return Response({'error': 'type attribut non existante'}, status=status.HTTP_404_NOT_FOUND)
    type_attribut.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
