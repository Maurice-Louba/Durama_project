from ..models import Etiquette
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import EtiquetteSerailized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creerAttribut(request):
    data=EtiquetteSerailized(data=request.data)
    if data.is_valid():
        data.save()
        return Response(status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)
@api_view(['GET'])
@permission_classes([AllowAny])
def TousEtiquette(request):
    etiquettes=Etiquette.objects.all()
    etiquettesSeria=EtiquetteSerailized(etiquettes,many=True)
    return Response(etiquettesSeria.data)
@api_view(['GET'])
@permission_classes([AllowAny])
def detailEtiquette(request,pk):
    try:
        etiquette=Etiquette.objects.get(pk=pk)
    except Etiquette.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    etiquetteSerial=EtiquetteSerailized(etiquette)
    return Response(etiquetteSerial.data)
