from ..models import AvisProduit,Produit
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import AvisProduitSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tousAvis(request):
    avis=AvisProduit.objects.all().order_by('-created_at')
    avisSerial=AvisProduitSerialized(avis,many=True)
    return Response(avisSerial.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def AvisSurUnProduit(request,produit_id):
    try:
        avis_produit=AvisProduit.objects.filter(produit_id=produit_id)
    except AvisProduit.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    avis_produitSeria=AvisProduitSerialized(avis_produit,many=True)
    return Response(avis_produitSeria.data)



@swagger_auto_schema(
    method='post', 
    request_body=AvisProduitSerialized,
    responses={
        201: AvisProduitSerialized,
        400: 'Bad Request'
    }
)
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def faireAvis(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AvisProduitSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(produit=produit)  
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT','PATCH'])
@permission_classes([IsAuthenticated])
def modifierAvisProduit(request,produit_id):
    try:
        produit=Produit.objects.get(produit=produit_id)
    except Produit.DoesNotExist:
        return Response({'error':'produit non trouver'},status=status.HTTP_404_NOT_FOUND)
    serializer=AvisProduitSerialized(produit,data=request.data,context={'request':request},partial=(request.method=='PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteAvisProduit(request,produit_id):
    try:
        produit=Produit.objects.filter(produit_id=produit_id,user=request.user)
    except Produit.DoesNotExist:
        return Response({'error':'produit non trouver'},status=status.HTTP_404_NOT_FOUND)   
    produit.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([AllowAny])
def detailAvisSurProduit(request,pk):
    try:
        avis=AvisProduit.objects.get(pk=pk)
    except AvisProduit.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    avisSerializ=AvisProduitSerialized(avis)
    return Response(avisSerializ.data)