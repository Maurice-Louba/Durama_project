from ..models import Attribut,TypeAttribut
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import AttributSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creerAttribut(request,typeAttribut):
    try:
        type_attribut=TypeAttribut.objects.get(pk=typeAttribut)
    except TypeAttribut.DoesNotExist:
        return Response({'error':'Type non existant'},status=status.HTTP_404_NOT_FOUND)
    data=AttributSerialized(data=request.data)
    if data.is_valid():
        data.save(typeAttribut=type_attribut)
        return Response(status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)
@api_view(['GET'])
@permission_classes([AllowAny])
def TousLesAttribut(request,typeAttribut_id):
    attributs=Attribut.objects.filter(typeAttribut_id=typeAttribut_id)
    if request.method=='GET':
        attributs_seria=AttributSerialized(attributs,many=True)
        return Response(attributs_seria.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def DetailsAttribut(request,pk):
    try:
        attribut=Attribut.objects.get(pk=pk)
    except Attribut.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    attribut_seria=AttributSerialized(attribut)
    return Response(attribut_seria.data)
@api_view(['PUT','PATCH'])
@permission_classes([IsAuthenticated])
def changerUnAttribut(request,pk):
    try:
        attribut=Attribut.objects.get(pk=pk)
    except Attribut.DoesNotExist:
        return Response({'error':'Attribut non trouver'},status=status.HTTP_404_NOT_FOUND)
    data=AttributSerialized(attribut,data=request.data,partial=(request.method=='PATCH'))
    if data.is_valid():
        data.save()
        return Response(status=status.HTTP_201_CREATED)
    return Response({'message':'mauvais format'},status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def DeleteAttribut(request,pk):
    try:
        attribut=Attribut.objects.get(pk=pk)
    except Attribut.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    attribut.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)