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
    attributs_ids = serializers.PrimaryKeyRelatedField(
        queryset=Attribut.objects.all(),
        many=True,
        write_only=True,
        required=False
        # NOTE: On enlève source='attributs' pour éviter le problème
    )

    class Meta:
        model = ContenuPanier
        fields = [
            "id", "panier", "produit", "produit_variable", "attributs",
            "quantite", "is_variable", "created_at", "updated_at",
            "produit_id", "produit_variable_id", "attributs_ids"
        ]
        read_only_fields = ["panier", "created_at", "updated_at"]

    def create(self, validated_data):
        print("=== CREATE PANIER ITEM ===")
        print(f"Validated data AVANT extraction: {validated_data}")
        
        # IMPORTANT: attributs_ids contient des OBJETS Attribut, pas des IDs
        attributs_objects = validated_data.pop('attributs_ids', [])
        print(f"Attributs objets extraits: {[str(a) for a in attributs_objects]}")
        
        # Extraire les IDs des objets Attribut
        attributs_ids = [attr.id for attr in attributs_objects]
        print(f"Attributs IDs extraits: {attributs_ids}")
        
        # Le panier doit être dans validated_data (venant de la vue)
        if 'panier' not in validated_data:
            # Si absent, le récupérer depuis l'utilisateur
            request = self.context.get('request')
            if request and request.user:
                panier, _ = Panier.objects.get_or_create(user=request.user)
                validated_data['panier'] = panier
        
        print(f"Validated data APRÈS extraction: {validated_data}")
        
        # Créer l'item de panier
        panier_item = ContenuPanier.objects.create(**validated_data)
        print(f"Panier item créé: {panier_item.id}")
        
        # Ajouter les attributs ManyToMany avec les OBJETS (pas les IDs)
        if attributs_objects:
            # Utiliser directement les objets Attribut
            panier_item.attributs.set(attributs_objects)
            print(f"{len(attributs_objects)} attributs ajoutés")
        
        return panier_item

    def update(self, instance, validated_data):
        print("=== UPDATE PANIER ITEM ===")
        
        # Extraire les attributs_ids (objets Attribut)
        attributs_objects = validated_data.pop('attributs_ids', None)
        
        # Mettre à jour les autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Mettre à jour les attributs si fournis
        if attributs_objects is not None:
            instance.attributs.set(attributs_objects)
            print(f"Attributs mis à jour: {len(attributs_objects)}")
        
        return instance

    def to_representation(self, instance):
        """S'assurer que les attributs sont inclus dans la réponse"""
        representation = super().to_representation(instance)
        
        # S'assurer que les attributs sont bien sérialisés
        representation['attributs'] = AttributSerialized(
            instance.attributs.all(), 
            many=True
        ).data
        
        return representation


        
        
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