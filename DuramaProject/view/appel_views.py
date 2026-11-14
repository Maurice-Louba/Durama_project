from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import DemandeAppelExpert
from ..serializer import DemandeAppelExpertSerializer

# NB : DRF authentifie déjà l'utilisateur (JWT) grâce à IsAuthenticated : request.user suffit.
# L'ancienne fonction get_user_from_request relisait le JWT à la main pour rien.

LIMITE_MAX = 200


def _demande(demande_id):
    return DemandeAppelExpert.objects.select_related('user').filter(id=demande_id).first()


def _non_trouvee():
    return Response({"error": "Demande d'appel non trouvée"}, status=404)


def _filtrer(request, demandes):
    statut = request.query_params.get('statut')
    if statut:
        demandes = demandes.filter(statut=statut)
    return demandes


def _limiter(request, demandes):
    limit = request.query_params.get('limit')
    if limit:
        try:
            return demandes[:max(1, min(int(limit), LIMITE_MAX))]
        except ValueError:
            pass
    return demandes


# ─── CRUD DEMANDES APPEL EXPERT ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_demande_appel(request):
    """
    Créer une nouvelle demande d'appel expert
    POST /demandes-appel/creer/
    """
    serializer = DemandeAppelExpertSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()  # l'utilisateur est toujours request.user
        return Response(
            {
                "message": "Demande d'appel expert créée avec succès",
                "data": serializer.data
            },
            status=201
        )
    return Response({"errors": serializer.errors}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def liste_demandes_appel(request):
    """
    Liste des demandes d'appel expert.
    GET /demandes-appel/
    Staff : toutes les demandes. Client : uniquement les siennes (données personnelles).
    """
    demandes = DemandeAppelExpert.objects.select_related('user').order_by('-created_at')
    if not request.user.is_staff:
        demandes = demandes.filter(user=request.user)
    demandes = _limiter(request, _filtrer(request, demandes))

    serializer = DemandeAppelExpertSerializer(demandes, many=True, context={'request': request})
    return Response({
        "count": len(serializer.data),
        "results": serializer.data
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mes_demandes_appel(request):
    """
    Récupérer les demandes d'appel de l'utilisateur connecté
    GET /demandes-appel/mes-demandes/
    """
    demandes = _filtrer(request, DemandeAppelExpert.objects.select_related('user')
                        .filter(user=request.user).order_by('-created_at'))
    serializer = DemandeAppelExpertSerializer(demandes, many=True, context={'request': request})
    return Response({
        "count": len(serializer.data),
        "results": serializer.data
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detail_demande_appel(request, demande_id):
    """
    Récupérer les détails d'une demande d'appel expert spécifique
    GET /demandes-appel/<int:demande_id>/
    """
    demande = _demande(demande_id)
    if demande is None:
        return _non_trouvee()

    # (admin ou propriétaire de la demande)
    if not request.user.is_staff and demande.user_id != request.user.id:
        return Response({"error": "Vous n'êtes pas autorisé à voir cette demande"}, status=403)

    serializer = DemandeAppelExpertSerializer(demande, context={'request': request})
    return Response(serializer.data, status=200)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modifier_demande_appel(request, demande_id):
    """
    Modifier une demande d'appel expert
    PUT / PATCH /demandes-appel/<int:demande_id>/modifier/
    """
    user = request.user
    demande = _demande(demande_id)
    if demande is None:
        return _non_trouvee()

    if not user.is_staff and demande.user_id != user.id:
        return Response({"error": "Vous n'êtes pas autorisé à modifier cette demande"}, status=403)

    # Si la demande est déjà traitée, ne pas autoriser la modification
    if demande.statut in ['traitee', 'annulee'] and not user.is_staff:
        return Response({"error": f"Impossible de modifier une demande {demande.statut}"}, status=400)

    serializer = DemandeAppelExpertSerializer(
        demande,
        data=request.data,
        partial=request.method == 'PATCH',
        context={'request': request}
    )
    if serializer.is_valid():
        serializer.save()  # statut / notes internes ignorés si l'utilisateur n'est pas staff
        return Response({
            "message": "Demande d'appel expert mise à jour avec succès",
            "data": serializer.data
        }, status=200)
    return Response({"errors": serializer.errors}, status=400)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_demande_appel(request, demande_id):
    """
    Supprimer une demande d'appel expert
    DELETE /demandes-appel/<int:demande_id>/supprimer/
    """
    user = request.user
    demande = _demande(demande_id)
    if demande is None:
        return _non_trouvee()

    if not user.is_staff and demande.user_id != user.id:
        return Response({"error": "Vous n'êtes pas autorisé à supprimer cette demande"}, status=403)

    # Si la demande est déjà traitée, ne pas autoriser la suppression (sauf admin)
    if demande.statut == 'traitee' and not user.is_staff:
        return Response({"error": "Impossible de supprimer une demande déjà traitée"}, status=400)

    demande.delete()
    return Response({"message": "Demande d'appel expert supprimée avec succès"}, status=200)


# ─── VUES SPÉCIFIQUES POUR LE CHANGEMENT DE STATUT ─────────────────────────

def _ajouter_notes(request, demande):
    notes = request.data.get('notes_interne')
    if notes and request.user.is_staff:
        demande.notes_interne = str(notes)[:5000]
        demande.save(update_fields=['notes_interne', 'updated_at'])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marquer_demande_traitee(request, demande_id):
    """
    Marquer une demande d'appel comme traitée
    POST /demandes-appel/<int:demande_id>/traiter/
    """
    if not request.user.is_staff:
        return Response({"error": "Seul un administrateur peut effectuer cette action"}, status=403)

    demande = _demande(demande_id)
    if demande is None:
        return _non_trouvee()

    if demande.statut == 'traitee':
        return Response({"message": "Cette demande est déjà traitée"}, status=200)

    demande.marquer_traitee()
    _ajouter_notes(request, demande)

    serializer = DemandeAppelExpertSerializer(demande, context={'request': request})
    return Response({
        "message": "Demande marquée comme traitée avec succès",
        "data": serializer.data
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marquer_demande_planifiee(request, demande_id):
    """
    Marquer une demande d'appel comme planifiée
    POST /demandes-appel/<int:demande_id>/planifier/
    """
    if not request.user.is_staff:
        return Response({"error": "Seul un administrateur peut effectuer cette action"}, status=403)

    demande = _demande(demande_id)
    if demande is None:
        return _non_trouvee()

    if demande.statut == 'planifiee':
        return Response({"message": "Cette demande est déjà planifiée"}, status=200)
    if demande.statut in ('traitee', 'annulee'):
        return Response({"error": f"Impossible de planifier une demande {demande.statut}"}, status=400)

    demande.marquer_planifiee()
    _ajouter_notes(request, demande)

    serializer = DemandeAppelExpertSerializer(demande, context={'request': request})
    return Response({
        "message": "Demande marquée comme planifiée avec succès",
        "data": serializer.data
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def annuler_demande_appel(request, demande_id):
    """
    Annuler une demande d'appel expert
    POST /demandes-appel/<int:demande_id>/annuler/
    """
    user = request.user
    demande = _demande(demande_id)
    if demande is None:
        return _non_trouvee()

    # L'utilisateur peut annuler sa propre demande ou un admin
    if not user.is_staff and demande.user_id != user.id:
        return Response({"error": "Vous n'êtes pas autorisé à annuler cette demande"}, status=403)

    if demande.statut == 'annulee':
        return Response({"message": "Cette demande est déjà annulée"}, status=200)

    # Si la demande est déjà traitée, ne pas autoriser l'annulation (sauf admin)
    if demande.statut == 'traitee' and not user.is_staff:
        return Response({"error": "Impossible d'annuler une demande déjà traitée"}, status=400)

    demande.annuler()
    _ajouter_notes(request, demande)  # admin seulement

    serializer = DemandeAppelExpertSerializer(demande, context={'request': request})
    return Response({
        "message": "Demande d'appel annulée avec succès",
        "data": serializer.data
    }, status=200)


# ─── STATISTIQUES ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistiques_demandes_appel(request):
    """
    Obtenir les statistiques des demandes d'appel expert
    GET /demandes-appel/statistiques/
    """
    if not request.user.is_staff:
        return Response({"error": "Seul un administrateur peut voir les statistiques"}, status=403)

    par_statut = dict(DemandeAppelExpert.objects.values_list('statut').annotate(n=Count('id')))
    dernieres = DemandeAppelExpert.objects.select_related('user').order_by('-created_at')[:5]
    dernieres_serializer = DemandeAppelExpertSerializer(dernieres, many=True, context={'request': request})

    return Response({
        "total": sum(par_statut.values()),
        "en_attente": par_statut.get('en_attente', 0),
        "traitees": par_statut.get('traitee', 0),
        "annulees": par_statut.get('annulee', 0),
        "planifiees": par_statut.get('planifiee', 0),
        "dernieres_demandes": dernieres_serializer.data
    }, status=200)
