from ..models import User
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import UserSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])  
def current_user(request):
    user = request.user  

    if request.method == "GET":
        serializer = UserSerialized(user)
        return Response(serializer.data)

    elif request.method == "PUT":  
        serializer = UserSerialized(
            user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['DELETE'])
@permission_classes([AllowAny])
def deleteUser(request):
    try:
        user=User.objects.get(user=request.user)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)