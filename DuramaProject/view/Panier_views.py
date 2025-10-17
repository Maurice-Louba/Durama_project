from ..models import Panier
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import PanierSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def liste_paniers(request):
    paniers = Panier.objects.filter(user=request.user)
    serializer = PanierSerialized(paniers, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def creer_panier(request):
    serializer = PanierSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def panier_detail(request, pk):
    panier = get_object_or_404(Panier, pk=pk, user=request.user)

    if request.method == 'GET':
        serializer = PanierSerialized(panier)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = PanierSerialized(panier, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        panier.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
