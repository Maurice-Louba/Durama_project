from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import Attribut, TypeAttribut
from ..serializer import AttributSerialized


@api_view(['POST'])
@permission_classes([IsAdminUser])
def creerAttribut(request, typeAttribut):
    try:
        type_attribut = TypeAttribut.objects.get(pk=typeAttribut)
    except TypeAttribut.DoesNotExist:
        return Response({'error': 'Type non existant'}, status=status.HTTP_404_NOT_FOUND)
    data = AttributSerialized(data=request.data)
    if data.is_valid():
        data.save(typeAttribut=type_attribut)
        return Response(data.data, status=status.HTTP_201_CREATED)
    return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def TousLesAttribut(request, typeAttribut_id):
    attributs = Attribut.objects.filter(typeAttribut_id=typeAttribut_id).select_related('typeAttribut')
    attributs_seria = AttributSerialized(attributs, many=True)
    return Response(attributs_seria.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def DetailsAttribut(request, pk):
    try:
        attribut = Attribut.objects.select_related('typeAttribut').get(pk=pk)
    except Attribut.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    attribut_seria = AttributSerialized(attribut)
    return Response(attribut_seria.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def changerUnAttribut(request, pk):
    try:
        attribut = Attribut.objects.get(pk=pk)
    except Attribut.DoesNotExist:
        return Response({'error': 'Attribut non trouver'}, status=status.HTTP_404_NOT_FOUND)
    data = AttributSerialized(attribut, data=request.data, partial=(request.method == 'PATCH'))
    if data.is_valid():
        data.save()
        return Response(data.data, status=status.HTTP_200_OK)
    return Response({'message': 'mauvais format', 'errors': data.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def DeleteAttribut(request, pk):
    try:
        attribut = Attribut.objects.get(pk=pk)
    except Attribut.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    attribut.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
