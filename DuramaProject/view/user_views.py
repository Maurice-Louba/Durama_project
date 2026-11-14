from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..serializer import UserSerialized

TAILLE_MAX_PHOTO = 3 * 1024 * 1024  # 3 Mo
EXTENSIONS_PHOTO = ('.jpg', '.jpeg', '.png', '.webp')


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user

    if request.method == "GET":
        serializer = UserSerialized(user, context={'request': request})
        return Response(serializer.data)

    photo = request.FILES.get('photo')
    if photo is not None:
        # photo est un FileField (pas ImageField) : on contrôle nous-mêmes type et taille
        if not photo.name.lower().endswith(EXTENSIONS_PHOTO):
            return Response({'photo': ["Format accepté : jpg, jpeg, png, webp."]}, status=status.HTTP_400_BAD_REQUEST)
        if photo.size > TAILLE_MAX_PHOTO:
            return Response({'photo': ["La photo ne doit pas dépasser 3 Mo."]}, status=status.HTTP_400_BAD_REQUEST)

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
@permission_classes([IsAuthenticated])  # avant : AllowAny + requête invalide (User.objects.get(user=...))
def deleteUser(request):
    request.user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
