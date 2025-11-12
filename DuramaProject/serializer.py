from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import *
from DuramaProject.models import Panier


User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'password']   # on enlève username
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        return value  

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(email=validated_data['email'])
        user.set_password(password)  
        user.is_active = False   
        user.save()
        return user


class CategorieSerialized(serializers.ModelSerializer):
    class Meta:
        model=Categorie
        fields='__all__'

class UserSerialized(serializers.ModelSerializer):
    class Meta:
        model=User
        fields='__all__'
    

class SousCategorieSerialized(serializers.ModelSerializer):
    categorie_principale=CategorieSerialized(read_only=True)
    class Meta:
        model=SubCategorie
        fields=['categorie_principale','id','nom','courte_description','longue_description','created_at','updated_at']

class TypeAttributSerialized(serializers.ModelSerializer):
    class Meta:
        model=TypeAttribut
        fields='__all__'
class AttributSerialized(serializers.ModelSerializer):
    typeAttribut=TypeAttributSerialized(read_only=True)
    class Meta:
        model=Attribut
        fields=['id','typeAttribut','valeur','code_Couleur','created_at','updated_at']

class EtiquetteSerailized(serializers.ModelSerializer):
    class Meta:
        model=Etiquette
        fields='__all__'
        
class ProduitSerialized(serializers.ModelSerializer):
    # Relations en lecture
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
            "nom_vendeur",
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
class ImageProduitSerialized(serializers.ModelSerializer):
    produit=ProduitSerialized(read_only=True)
    class Meta:
        model=ImageProduit
        fields=['id','produit','image','created_at','updated_at']

class ProduitVariableSerialized(serializers.ModelSerializer):
    produit=ProduitSerialized(read_only=True)
    class Meta:
        model=ProduitVariable
        fields=['produit','prix_fournisseur','prix_vente','prix_promo','quantite','created_at','updated_at']

class ProduitVariableImageSerialized(serializers.ModelSerializer):
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

class AvisProduitSerialized(serializers.ModelSerializer):
    produit=ProduitSerialized(read_only=True)
    user=UserSerialized(read_only=True)
    class Meta:
        model=AvisProduit
        fields=['id','produit','user','texte','note','created_at','updated_at']
    def create(self, validated_data):
        user=self.context['request'].user
        return AvisProduit.objects.create(user=user,**validated_data)

class ProduitVariableAttributSerialized(serializers.ModelSerializer):
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

class PanierSerialized(serializers.ModelSerializer):
    user=UserSerialized(read_only=True)
    class Meta:
        model=Panier
        fields=['id','user','created_at','updated_at']
    def create(self, validated_data):
        user=self.context['request'].user
        return Panier.objects.create(user=user,**validated_data)
    





class PanierItemSerialized(serializers.ModelSerializer):
    # --- Champs en lecture seule (pour GET) ---
    panier = PanierSerialized(read_only=True)
    produit = ProduitSerialized(read_only=True)
    produit_variable = ProduitVariableSerialized(read_only=True)
    attribut_valeur = AttributSerialized(read_only=True)

    # --- Champs en écriture (pour POST/PUT/PATCH) ---
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
    attribut_valeur_id = serializers.PrimaryKeyRelatedField(
        queryset=Attribut.objects.all(),
        source="attribut_valeur",
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = ContenuPanier
        fields = [
            "id",
            "panier",
            "produit",
            "produit_variable",
            "attribut_valeur",
            "quantite",
            "is_variable",
            "created_at",
            "updated_at",
            # champs écriture
            "produit_id",
            "produit_variable_id",
            "attribut_valeur_id",
        ]



        
        
class CommandeSerialized(serializers.ModelSerializer):
    user = UserSerialized(read_only=True)
    panier = PanierSerialized(read_only=True)

    # Pour la création, on autorise juste l’ID du panier
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
            "total_produits",
            "frais_livraison",
            "montant_total",
            "adresse_livraison",
            "notes",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["total_produits", "montant_total", "created_at", "updated_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        commande = Commande.objects.create(user=user, **validated_data)
        
        commande.calculer_totaux()
        return commande
class CommandeItemSerialized(serializers.ModelSerializer):
    commande=CommandeSerialized(read_only=True)
    produit=ProduitSerialized(read_only=True)
    produit_variable=ProduitVariableSerialized(read_only=True)
    class Meta:
        model=CommandeItem
        fields=['commande','produit','produit_variable','quantite','prix_unitaire']

class PaiementSerialized(serializers.ModelSerializer):
    commande=CommandeSerialized(read_only=True)
    class Meta:
        model=Paiement
        fields=['id','commande','method','transaction_id','montant','date_paiement']


class LivraisonSerialized(serializers.ModelSerializer):
    commande=CommandeSerialized(read_only=True)
    class Meta:
        model=Livraison
        fields=['id','commande','transporteur','numero_suivi','date_expedition','date_livraison']

class AdresseSerialized(serializers.ModelSerializer):
    user=UserSerialized(read_only=True)
    class Meta:
        model=Addresse
        fields=['id','user','address','ville','pays','telephone','latitude','longitude','location_url','is_default','created_at','updated_at']

class FavoriSerialized(serializers.ModelSerializer):
    user=UserSerialized(read_only=True)
    produit=ProduitSerialized(read_only=True)
    class Meta:
        model=Favori
        fields=['id','user','produit','created_at','updated_at']
    def created(self,**validated_data):
        user=self.context['request'].user
        return Favori.objects.create(user=user,**validated_data)