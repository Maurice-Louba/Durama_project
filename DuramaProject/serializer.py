import re

from django.contrib.auth import get_user_model
from django.db import models as django_models
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Addresse, Attribut, AvisProduit, Categorie, Commande, CommandeItem, ContenuPanier,
    DemandeAppelExpert, Etiquette, Favori, ImageProduit, Livraison, MateriauDevis, Paiement,
    Panier, Produit, ProduitVariable, ProduitVariableAttribut, ProduitVariableImage,
    ProjetDevis, SubCategorie, TypeAttribut, Vendeur, MessageContact,
)


User = get_user_model()


class CheminMediaField(serializers.ImageField):
    """
    Renvoie toujours un chemin relatif (« /media/... »), même quand la requête est dans le contexte.
    Le frontend préfixe lui-même l'URL de l'API : une URL absolue donnait « http://hotehttp://hote/... ».
    """

    def to_representation(self, value):
        if not value:
            return None
        try:
            return value.url
        except ValueError:
            return None


class CheminFichierField(CheminMediaField, serializers.FileField):
    pass


class BaseModelSerializer(serializers.ModelSerializer):
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        django_models.ImageField: CheminMediaField,
        django_models.FileField: CheminFichierField,
    }

TELEPHONE_REGEX = re.compile(r"^\+?[0-9 ().-]{6,20}$")


def utilisateur_courant(serializer):
    request = serializer.context.get('request')
    user = getattr(request, 'user', None)
    return user if user is not None and user.is_authenticated else None


def est_staff(serializer):
    user = utilisateur_courant(serializer)
    return bool(user and user.is_staff)


def valider_telephone(value):
    # Un FormData envoie « null » / « undefined » pour un champ vide côté frontend
    if value is None or value.strip().lower() in ("", "null", "undefined"):
        return ""
    if not TELEPHONE_REGEX.match(value.strip()):
        raise serializers.ValidationError("Numéro de téléphone invalide.")
    return value.strip() if value else value


class RegisterSerializer(BaseModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['email', 'password']   # on enlève username
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        try:
            # Applique AUTH_PASSWORD_VALIDATORS (mot de passe trop courant, que des chiffres...)
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False,
        )


class CategorieSerialized(BaseModelSerializer):
    class Meta:
        model = Categorie
        fields = '__all__'


class UserSerialized(BaseModelSerializer):
    """
    Profil de l'utilisateur. Ne JAMAIS utiliser '__all__' ici : cela exposait le hash du
    mot de passe et permettait à un utilisateur de se donner is_staff / is_superuser.
    """
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number', 'address',
            'photo', 'bio', 'is_confirmed', 'is_staff', 'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'email', 'is_confirmed', 'is_staff', 'date_joined', 'last_login']

    def validate_phone_number(self, value):
        return valider_telephone(value)


class UserPublicSerialized(BaseModelSerializer):
    """Infos visibles par tout le monde (ex : auteur d'un avis) : pas d'email ni de téléphone."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'photo']
        read_only_fields = fields


class SousCategorieSerialized(BaseModelSerializer):
    categorie_principale = CategorieSerialized(read_only=True)
    categorie_principale_id = serializers.PrimaryKeyRelatedField(
        queryset=Categorie.objects.all(),
        source='categorie_principale',
        write_only=True,
        required=False,
    )

    class Meta:
        model = SubCategorie
        fields = ['categorie_principale', 'categorie_principale_id', 'id', 'nom', 'courte_description', 'longue_description', 'created_at', 'updated_at']


class TypeAttributSerialized(BaseModelSerializer):
    class Meta:
        model = TypeAttribut
        fields = '__all__'


class AttributSerialized(BaseModelSerializer):
    typeAttribut = TypeAttributSerialized(read_only=True)
    typeAttribut_id = serializers.PrimaryKeyRelatedField(
        queryset=TypeAttribut.objects.all(),
        source='typeAttribut',
        write_only=True,
        required=False,
    )

    class Meta:
        model = Attribut
        fields = ['id', 'typeAttribut', 'typeAttribut_id', 'valeur', 'code_Couleur', 'created_at', 'updated_at']


class EtiquetteSerailized(BaseModelSerializer):
    class Meta:
        model = Etiquette
        fields = '__all__'
        extra_kwargs = {'slug': {'required': False}}


class VendeurSerialized(BaseModelSerializer):
    class Meta:
        model = Vendeur
        fields = "__all__"
        # Ces champs ne doivent être modifiés que par l'administration
        read_only_fields = ['est_verifie', 'note', 'created_at', 'updated_at']
        extra_kwargs = {'slug': {'required': False}}

    def validate_telephone(self, value):
        return valider_telephone(value)


class ProduitSerialized(BaseModelSerializer):
    # Relations en lecture
    vendeur = VendeurSerialized(read_only=True)

    vendeur_id = serializers.PrimaryKeyRelatedField(
        queryset=Vendeur.objects.all(),
        source="vendeur",
        write_only=True
    )
    categorie = CategorieSerialized(read_only=True)
    sous_categorie = SousCategorieSerialized(read_only=True)
    etiquette = EtiquetteSerailized(read_only=True)

    # Relations en écriture (ID seulement)
    categorie_id = serializers.PrimaryKeyRelatedField(
        queryset=Categorie.objects.all(),
        source="categorie",
        write_only=True
    )
    sous_categorie_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategorie.objects.all(),
        source="sous_categorie",
        write_only=True,
        required=False,
        allow_null=True
    )
    etiquette_id = serializers.PrimaryKeyRelatedField(
        queryset=Etiquette.objects.all(),
        source="etiquette",
        write_only=True
    )

    class Meta:
        model = Produit
        fields = [
            "id",
            "nom",
            "slug",
            "sku",
            "type_produit",
            "vendeur",
            "vendeur_id",
            "livraison_gratuite",
            "description_courte",
            "description_longue",
            "prix_fournisseur",
            "prix_promo",
            "prix_vente",
            "quantite",
            "etat_stock",
            "largeur",
            "longueur",
            "poids",
            "hauteur",
            "superficie",
            "taille",
            "materiau",
            "est_publie",
            "est_original",
            "caracteristiques",
            "status",
            "categorie",          # lecture
            "sous_categorie",     # lecture
            "etiquette",          # lecture
            "categorie_id",       # écriture
            "sous_categorie_id",  # écriture
            "etiquette_id",
            "image_principale",
            "vues",
            "nombres_ventes",
            "created_at",
            "updated_at",
        ]
        # slug, compteurs et dates sont gérés par le serveur
        read_only_fields = ["slug", "vues", "nombres_ventes", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Le prix d'achat fournisseur est une donnée commerciale confidentielle :
        # il n'est renvoyé qu'aux membres du staff (la vue doit passer context={'request': request}).
        if not est_staff(self):
            data.pop("prix_fournisseur", None)
        return data

    def validate(self, attrs):
        instance = self.instance
        prix_vente = attrs.get('prix_vente', getattr(instance, 'prix_vente', None))
        prix_promo = attrs.get('prix_promo', getattr(instance, 'prix_promo', None))
        if prix_promo and prix_vente and prix_promo > prix_vente:
            raise serializers.ValidationError({'prix_promo': "Le prix promo ne peut pas être supérieur au prix de vente."})

        categorie = attrs.get('categorie', getattr(instance, 'categorie', None))
        sous_categorie = attrs.get('sous_categorie', getattr(instance, 'sous_categorie', None))
        if categorie and sous_categorie and sous_categorie.categorie_principale_id != categorie.id:
            raise serializers.ValidationError({'sous_categorie_id': "Cette sous-catégorie n'appartient pas à la catégorie choisie."})

        caracteristiques = attrs.get('caracteristiques')
        if caracteristiques is not None and not isinstance(caracteristiques, dict):
            raise serializers.ValidationError({'caracteristiques': "Les caractéristiques doivent être un objet JSON."})
        return attrs


class ImageProduitSerialized(BaseModelSerializer):
    produit = ProduitSerialized(read_only=True)

    class Meta:
        model = ImageProduit
        fields = ['id', 'produit', 'image', 'created_at', 'updated_at']


class ProduitVariableSerialized(BaseModelSerializer):
    produit = ProduitSerialized(read_only=True)

    class Meta:
        model = ProduitVariable
        fields = ['id', 'produit', 'prix_fournisseur', 'prix_vente', 'prix_promo', 'quantite', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not est_staff(self):
            data.pop("prix_fournisseur", None)
        return data

    def validate(self, attrs):
        instance = self.instance
        prix_vente = attrs.get('prix_vente', getattr(instance, 'prix_vente', None))
        prix_promo = attrs.get('prix_promo', getattr(instance, 'prix_promo', None))
        if prix_promo and prix_vente and prix_promo > prix_vente:
            raise serializers.ValidationError({'prix_promo': "Le prix promo ne peut pas être supérieur au prix de vente."})
        return attrs


class ProduitVariableImageSerialized(BaseModelSerializer):
    produit_variable = ProduitVariableSerialized(read_only=True)

    class Meta:
        model = ProduitVariableImage
        fields = [
            "id",
            "produit_variable",
            "image",
            "created_at",
            "updated_at"
        ]


class AvisProduitSerialized(BaseModelSerializer):
    produit = ProduitSerialized(read_only=True)
    user = UserPublicSerialized(read_only=True)
    note = serializers.IntegerField(min_value=1, max_value=5, default=5)

    class Meta:
        model = AvisProduit
        fields = ['id', 'produit', 'user', 'texte', 'note', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_texte(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("L'avis ne peut pas être vide.")
        return value

    def create(self, validated_data):
        user = utilisateur_courant(self)
        if user is None:
            raise serializers.ValidationError("Vous devez être connecté pour laisser un avis.")
        produit = validated_data.get('produit')
        if produit is not None and AvisProduit.objects.filter(user=user, produit=produit).exists():
            raise serializers.ValidationError("Vous avez déjà donné un avis sur ce produit.")
        validated_data['user'] = user
        return super().create(validated_data)


class ProduitVariableAttributSerialized(BaseModelSerializer):
    produit_variable = ProduitVariableSerialized(read_only=True)
    attribut = AttributSerialized(read_only=True)

    # Pour écrire (création/modif), on utilise juste les IDs
    produit_variable_id = serializers.PrimaryKeyRelatedField(
        queryset=ProduitVariable.objects.all(),
        source="produit_variable",
        write_only=True
    )
    attribut_id = serializers.PrimaryKeyRelatedField(
        queryset=Attribut.objects.all(),
        source="attribut",
        write_only=True
    )

    class Meta:
        model = ProduitVariableAttribut
        fields = [
            "id",
            "produit_variable",
            "attribut",
            "produit_variable_id",
            "attribut_id"
        ]

    def validate(self, attrs):
        variante = attrs.get('produit_variable', getattr(self.instance, 'produit_variable', None))
        attribut = attrs.get('attribut', getattr(self.instance, 'attribut', None))
        if variante and attribut:
            doublon = ProduitVariableAttribut.objects.filter(produit_variable=variante, attribut=attribut)
            if self.instance:
                doublon = doublon.exclude(pk=self.instance.pk)
            if doublon.exists():
                raise serializers.ValidationError("Cet attribut est déjà associé à cette variante.")
        return attrs


class PanierSerialized(BaseModelSerializer):
    user = UserSerialized(read_only=True)

    class Meta:
        model = Panier
        fields = ['id', 'user', 'actif', 'created_at', 'updated_at']
        read_only_fields = ['actif', 'created_at', 'updated_at']

    def create(self, validated_data):
        user = utilisateur_courant(self)
        if user is None:
            raise serializers.ValidationError("Vous devez être connecté.")
        # Un seul panier actif par utilisateur : on renvoie l'existant s'il y en a un
        return Panier.panier_actif(user)


class PanierItemSerialized(BaseModelSerializer):
    # Lecture seulement
    panier = PanierSerialized(read_only=True)
    produit = ProduitSerialized(read_only=True)
    produit_variable = ProduitVariableSerialized(read_only=True)
    attributs = AttributSerialized(many=True, read_only=True)

    # Écriture seulement
    produit_id = serializers.PrimaryKeyRelatedField(
        queryset=Produit.objects.all(),
        source="produit",
        write_only=True,
        required=True
    )
    produit_variable_id = serializers.PrimaryKeyRelatedField(
        queryset=ProduitVariable.objects.all(),
        source="produit_variable",
        write_only=True,
        required=False,
        allow_null=True
    )
    attributs_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        default=list
    )
    quantite = serializers.IntegerField(min_value=1, max_value=10000, default=1)

    class Meta:
        model = ContenuPanier
        fields = [
            "id", "panier", "produit", "produit_variable", "attributs",
            "quantite", "is_variable", "created_at", "updated_at",
            "produit_id", "produit_variable_id", "attributs_ids"
        ]
        # is_variable est déduit automatiquement de produit_variable
        read_only_fields = ["panier", "is_variable", "created_at", "updated_at"]

    def validate_attributs_ids(self, value):
        ids = list(dict.fromkeys(value))  # supprime les doublons en gardant l'ordre
        existants = set(Attribut.objects.filter(id__in=ids).values_list('id', flat=True))
        manquants = [i for i in ids if i not in existants]
        if manquants:
            raise serializers.ValidationError(f"Attribut(s) introuvable(s) : {manquants}")
        return ids

    def validate(self, attrs):
        instance = self.instance
        produit = attrs.get('produit', getattr(instance, 'produit', None))
        variante = attrs.get('produit_variable', getattr(instance, 'produit_variable', None))

        if produit is not None:
            if not produit.est_publie:
                raise serializers.ValidationError({'produit_id': "Ce produit n'est pas disponible."})
            if produit.etat_stock == 'rupture stock':
                raise serializers.ValidationError({'produit_id': "Ce produit est en rupture de stock."})
            if variante is not None and variante.produit_id != produit.id:
                raise serializers.ValidationError({'produit_variable_id': "Cette variante n'appartient pas à ce produit."})
        return attrs

    def create(self, validated_data):
        attributs_ids = validated_data.pop('attributs_ids', [])

        # Le panier doit être dans validated_data (venant de la vue)
        if 'panier' not in validated_data:
            user = utilisateur_courant(self)
            if user is None:
                raise serializers.ValidationError("Vous devez être connecté pour ajouter au panier.")
            validated_data['panier'] = Panier.panier_actif(user)

        panier_item = ContenuPanier.objects.create(**validated_data)
        if attributs_ids:
            panier_item.attributs.set(attributs_ids)

        return ContenuPanier.objects.prefetch_related('attributs').get(id=panier_item.id)

    def update(self, instance, validated_data):
        attributs_ids = validated_data.pop('attributs_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if attributs_ids is not None:
            instance.attributs.set(attributs_ids)

        return ContenuPanier.objects.prefetch_related('attributs').get(id=instance.id)


class CommandeItemLigneSerialized(BaseModelSerializer):
    """Ligne de commande (sans la commande parente, pour l'imbriquer dans CommandeSerialized)."""
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    produit_slug = serializers.CharField(source='produit.slug', read_only=True)
    produit_image = CheminMediaField(source='produit.image_principale', read_only=True)
    attributs = AttributSerialized(many=True, read_only=True)
    sous_total = serializers.SerializerMethodField()

    class Meta:
        model = CommandeItem
        fields = ['id', 'produit', 'produit_nom', 'produit_slug', 'produit_image', 'produit_variable',
                  'quantite', 'attributs', 'prix_unitaire', 'sous_total']
        read_only_fields = fields

    def get_sous_total(self, obj):
        return str(obj.sous_total())


class CommandeSerialized(BaseModelSerializer):
    user = UserSerialized(read_only=True)
    panier = PanierSerialized(read_only=True)
    items = CommandeItemLigneSerialized(many=True, read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    # Pour la création, on autorise juste l'ID du panier
    panier_id = serializers.PrimaryKeyRelatedField(
        queryset=Panier.objects.all(),
        source="panier",
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Commande
        fields = [
            "id",
            "user",
            "panier",
            "panier_id",
            "numero",
            "statut",
            "statut_display",
            "total_produits",
            "frais_livraison",
            "montant_total",
            "adresse_livraison",
            "latitude",
            "longitude",
            "notes",
            "items",
            "created_at",
            "updated_at"
        ]
        # Le client ne fixe ni le numéro, ni le statut, ni les montants
        read_only_fields = ["numero", "statut", "total_produits", "frais_livraison", "montant_total", "created_at", "updated_at"]

    def validate_panier_id(self, panier):
        user = utilisateur_courant(self)
        if panier is not None and (user is None or panier.user_id != user.id):
            raise serializers.ValidationError("Ce panier ne vous appartient pas.")
        return panier

    def validate(self, attrs):
        lat, lng = attrs.get('latitude'), attrs.get('longitude')
        if lat is not None and not -90 <= lat <= 90:
            raise serializers.ValidationError({'latitude': "Latitude invalide."})
        if lng is not None and not -180 <= lng <= 180:
            raise serializers.ValidationError({'longitude': "Longitude invalide."})
        return attrs

    def create(self, validated_data):
        user = utilisateur_courant(self)
        if user is None:
            raise serializers.ValidationError("Vous devez être connecté pour commander.")
        commande = Commande.objects.create(user=user, **validated_data)
        commande.calculer_totaux()
        return commande


class CommandeStatutSerialized(BaseModelSerializer):
    """Réservé au staff : changer le statut et les frais de livraison d'une commande."""
    TRANSITIONS = {
        'en_attente': {'acceptee', 'annulee'},
        'acceptee': {'preparee', 'annulee'},
        'preparee': {'expediee', 'annulee'},
        'expediee': {'livree'},
        'livree': set(),
        'annulee': set(),
    }

    class Meta:
        model = Commande
        fields = ['id', 'numero', 'statut', 'frais_livraison', 'montant_total']
        read_only_fields = ['id', 'numero', 'montant_total']

    def validate_statut(self, value):
        actuel = self.instance.statut if self.instance else 'en_attente'
        if value != actuel and value not in self.TRANSITIONS.get(actuel, set()):
            raise serializers.ValidationError(f"Passage de « {actuel} » à « {value} » non autorisé.")
        return value

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if 'frais_livraison' in validated_data:
            instance.calculer_totaux()
        return instance


class CommandeItemSerialized(BaseModelSerializer):
    commande = CommandeSerialized(read_only=True)
    produit = ProduitSerialized(read_only=True)
    produit_variable = ProduitVariableSerialized(read_only=True)
    attributs = AttributSerialized(many=True, read_only=True)

    class Meta:
        model = CommandeItem
        fields = ['id', 'commande', 'produit', 'produit_variable', 'quantite', 'attributs', 'prix_unitaire']
        read_only_fields = ['prix_unitaire']


class PaiementSerialized(BaseModelSerializer):
    commande = CommandeSerialized(read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Paiement
        # 'method' n'existait pas (le champ s'appelle 'methode') : le serializer plantait à chaque appel
        fields = ['id', 'commande', 'methode', 'statut', 'statut_display', 'transaction_id', 'montant', 'date_paiement']
        # Le client choisit seulement la méthode ; statut, montant et transaction viennent du serveur
        read_only_fields = ['statut', 'transaction_id', 'montant', 'date_paiement']
        extra_kwargs = {'methode': {'required': True, 'allow_null': False, 'allow_blank': False}}

    def create(self, validated_data):
        commande = validated_data.get('commande')
        if commande is None:
            raise serializers.ValidationError("La commande est obligatoire.")
        if Paiement.objects.filter(commande=commande).exists():
            raise serializers.ValidationError("Un paiement existe déjà pour cette commande.")
        if commande.statut == 'annulee':
            raise serializers.ValidationError("Impossible de payer une commande annulée.")
        # Le montant est toujours celui de la commande, jamais celui envoyé par le client
        validated_data['montant'] = commande.montant_total
        return super().create(validated_data)


class PaiementAdminSerialized(PaiementSerialized):
    """Réservé au staff : confirmer / refuser un paiement."""

    class Meta(PaiementSerialized.Meta):
        read_only_fields = ['montant']
        extra_kwargs = {}

    def update(self, instance, validated_data):
        if validated_data.get('statut') == 'effectue' and instance.statut != 'effectue' and not validated_data.get('date_paiement'):
            validated_data['date_paiement'] = timezone.now()
        return super().update(instance, validated_data)


class LivraisonSerialized(BaseModelSerializer):
    commande = CommandeSerialized(read_only=True)

    class Meta:
        model = Livraison
        fields = ['id', 'commande', 'transporteur', 'numero_suivi', 'statut', 'date_expedition', 'date_livraison']

    def validate(self, attrs):
        instance = self.instance
        expedition = attrs.get('date_expedition', getattr(instance, 'date_expedition', None))
        livraison = attrs.get('date_livraison', getattr(instance, 'date_livraison', None))
        if expedition and livraison and livraison < expedition:
            raise serializers.ValidationError({'date_livraison': "La date de livraison ne peut pas précéder la date d'expédition."})
        return attrs

    def create(self, validated_data):
        commande = validated_data.get('commande')
        if commande is not None and Livraison.objects.filter(commande=commande).exists():
            raise serializers.ValidationError("Une livraison existe déjà pour cette commande.")
        return super().create(validated_data)


class AdresseSerialized(BaseModelSerializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90, required=False, default=0.0)
    longitude = serializers.FloatField(min_value=-180, max_value=180, required=False, default=0.0)

    class Meta:
        model = Addresse
        fields = ['id', 'address', 'ville', 'pays', 'telephone', 'latitude', 'longitude', 'location_url', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'location_url']

    def validate_telephone(self, value):
        return valider_telephone(value)

    def validate(self, data):
        # Avant : en PATCH sans latitude/longitude, les coordonnées existantes étaient écrasées par 0.0.
        # Les valeurs par défaut des champs ne s'appliquent qu'à la création (partial=False).
        lat = data.get('latitude', getattr(self.instance, 'latitude', None))
        lng = data.get('longitude', getattr(self.instance, 'longitude', None))
        if lat is not None and lng is not None:
            data['location_url'] = f"https://www.google.com/maps?q={lat},{lng}"
        return data


class FavoriSerialized(BaseModelSerializer):
    user = UserSerialized(read_only=True)
    produit = ProduitSerialized(read_only=True)

    class Meta:
        model = Favori
        fields = ['id', 'user', 'produit', 'created_at', 'updated_at']

    def create(self, validated_data):
        # (s'appelait 'created' : la méthode n'était jamais appelée)
        if 'user' not in validated_data:
            user = utilisateur_courant(self)
            if user is None:
                raise serializers.ValidationError("Vous devez être connecté.")
            validated_data['user'] = user
        produit = validated_data.get('produit')
        existant = Favori.objects.filter(user=validated_data['user'], produit=produit).first()
        return existant or super().create(validated_data)


class MateriauDevisSerializer(BaseModelSerializer):
    """Serializer pour les matériaux d'un devis"""
    produit_nom = serializers.CharField(source='produit.nom', read_only=True, default='')

    class Meta:
        model = MateriauDevis
        fields = [
            'id', 'nom', 'quantite', 'unite',
            'prix_unitaire', 'prix_total', 'produit', 'produit_nom'
        ]


class ProjetDevisSerializer(BaseModelSerializer):
    """Serializer pour les projets de devis avec leurs matériaux"""
    materiaux = MateriauDevisSerializer(many=True, read_only=True)
    prix_estime = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = ProjetDevis
        fields = [
            'id', 'nom_projet', 'ville', 'quartier', 'type_projet',
            'surface', 'nombre_etages', 'structure', 'type_sol',
            'finition', 'toiture', 'options', 'budget', 'objectif',
            'prix_estime', 'created_at', 'updated_at', 'materiaux'
        ]
        read_only_fields = ['prix_estime', 'created_at', 'updated_at', 'materiaux']

    def validate_options(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list) or not all(isinstance(o, str) for o in value):
            raise serializers.ValidationError("Les options doivent être une liste de textes.")
        return value


class DemandeAppelExpertSerializer(BaseModelSerializer):
    """
    Serializer pour les demandes d'appel expert.
    L'utilisateur est toujours celui de la requête ; statut et notes internes sont réservés au staff.
    """
    user = UserSerialized(read_only=True)

    # Affichage lisible du statut et de la disponibilité
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    disponibilite_display = serializers.CharField(source='get_disponibilite_display', read_only=True)

    # Calcul automatique du temps d'attente
    temps_attente_heures = serializers.SerializerMethodField()

    CHAMPS_STAFF = ('statut', 'notes_interne')

    class Meta:
        model = DemandeAppelExpert
        fields = [
            'id',
            'user',
            'nom',
            'email',
            'telephone',
            'sujet',
            'message',
            'disponibilite',
            'disponibilite_display',
            'date_appel',
            'statut',
            'statut_display',
            'notes_interne',
            'date_traitement',
            'created_at',
            'updated_at',
            'temps_attente_heures',
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
            'date_traitement',
            'statut_display',
            'disponibilite_display',
            'temps_attente_heures'
        ]
        extra_kwargs = {
            'notes_interne': {'required': False, 'allow_blank': True},
            'date_appel': {'required': False, 'allow_null': True},
            'statut': {'required': False},
        }

    def get_temps_attente_heures(self, obj):
        """Calculer le temps d'attente en heures"""
        return round(obj.get_duree_attente(), 2)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not est_staff(self):
            data.pop('notes_interne', None)
        return data

    def validate_email(self, value):
        return value.strip().lower()

    def validate_telephone(self, value):
        return valider_telephone(value)

    def validate_date_appel(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("La date d'appel ne peut pas être dans le passé.")
        return value

    def validate(self, attrs):
        # Un utilisateur normal ne peut pas changer le statut ni écrire des notes internes
        if not est_staff(self):
            for champ in self.CHAMPS_STAFF:
                attrs.pop(champ, None)
        return attrs

    def create(self, validated_data):
        """
        Créer une nouvelle demande d'appel expert
        """
        user = utilisateur_courant(self)
        if user is not None:
            validated_data['user'] = user
        return DemandeAppelExpert.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Mettre à jour une demande d'appel expert
        """
        ancien_statut = instance.statut

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Comparaison avec l'ANCIEN statut (avant, la comparaison se faisait après setattr
        # et date_traitement n'était jamais remplie)
        if instance.statut == 'traitee' and ancien_statut != 'traitee':
            instance.date_traitement = timezone.now()

        instance.save()
        return instance


class MessageContactSerializer(serializers.ModelSerializer):
    """Formulaire de la page Contact (l'utilisateur éventuel est ajouté par la vue)."""

    class Meta:
        model = MessageContact
        fields = ['nom', 'email', 'telephone', 'sujet', 'message']
        extra_kwargs = {'nom': {'required': False}, 'telephone': {'required': False}}

    def validate_email(self, value):
        return value.strip().lower()

    def validate_telephone(self, value):
        return valider_telephone(value)

    def validate_sujet(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Indiquez un sujet.")
        return value

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Votre message est trop court (10 caractères minimum).")
        return value
