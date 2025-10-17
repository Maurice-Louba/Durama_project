from ..models import TypeAttribut
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import TypeAttributSerialized
from drf_yasg.utils import swagger_auto_schema
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response



@swagger_auto_schema(
    method='post', 
    request_body=TypeAttributSerialized,
    responses={
        201: TypeAttributSerialized,
        400: 'Bad Request'
    }
)
@api_view(['POST'])

def faireUnTypeAttribut(request):
    data=TypeAttributSerialized(data=request.data)
    if data.is_valid():
        data.save()
        return Response(status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def VoirTousTypeAttribut(request):
    type_attribut=TypeAttribut.objects.all()
    if request.method=='GET':
        type_attributSeria=TypeAttributSerialized(type_attribut,many=True)
        return Response(type_attributSeria.data)
@api_view(['GET'])
@permission_classes([AllowAny])
def detailUnTypeAttribut(request,pk):
    try:
        type_attribut=TypeAttribut.objects.get(pk=pk)
    except TypeAttribut.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method=='GET':
        type_attributSeria=TypeAttributSerialized(type_attribut)
        return Response(type_attributSeria.data)
@api_view(['PUT','PATCH'])
@permission_classes([IsAuthenticated])
def changerTypeAttribut(request,pk):
    try:
        type_attribut=TypeAttribut.objects.get(pk=pk)
    except TypeAttribut.DoesNotExist:
        return Response({'error':'type attribut non existante'},status=status.HTTP_404_NOT_FOUND)
    
    data=TypeAttributSerialized(type_attribut,data=request.data,partial=(request.method=='PATCH'))
    if data.is_valid():
        data.save()
        return Response(status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def SupprimerUnTypeAttribut(request,pk):
    type_attribut=TypeAttribut.objects.get(pk=pk)
    type_attribut.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
    
        