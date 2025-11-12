from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from django.conf import settings  
import random
import random
import string
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models
from django.template.defaultfilters import slugify
from django.utils import timezone
# Create your models here.

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'email doit être défini")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superuser doit avoir is_superuser=True.')
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):


    username = None  # Pas de username, on utilise email
    email = models.EmailField(unique=True)
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    photo=models.FileField(null=True,blank=True,default=None,upload_to="profil/")
    bio = models.TextField(blank=True, null=True)
    is_confirmed = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


# ---------------------------
# OTP Email
# ---------------------------
class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))
        self.save()

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)


class Categorie(models.Model):
    GROS_CATEGORIE=[
        ('gros-oeuvres','Gros Oeuvres'),
        ('second-oeuvres','Second Oeuvres'),
        ('outillage','Outillage'),
        ('securité','Sécurité')
    ]
    
    nom=models.CharField(max_length=150,unique=True)
    courte_description=models.TextField(max_length=550)
    longue_description=models.TextField(max_length=1500)
    photo=models.FileField(upload_to='imageCategorie/',blank=True,null=True)
    is_parent=models.BooleanField(default=True)
    gros_categorie=models.CharField(max_length=150,choices=GROS_CATEGORIE,blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updeated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.nom} est une catégorie"

class SubCategorie(models.Model):
    categorie_principale=models.ForeignKey(Categorie,on_delete=models.CASCADE,related_name="categorie_principale")
    nom=models.CharField(max_length=150)
    courte_description=models.TextField(max_length=550,blank=True,null=True)
    longue_description=models.TextField(max_length=1500,blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.nom} est une sous catégorie de {self.categorie_principale.nom}"

class TypeAttribut(models.Model):
    
    nom=models.CharField(max_length=150)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)


class Attribut(models.Model):
    typeAttribut=models.ForeignKey(TypeAttribut,on_delete=models.CASCADE,related_name="type_d_attribut")
    valeur=models.CharField(max_length=150)
    code_Couleur=models.CharField(max_length=50,blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.typeAttribut.nom}: {self.valeur}"


class Etiquette(models.Model):
    name=models.CharField(max_length=150)
    slug=models.SlugField()
    description=models.TextField(max_length=1500)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.name}"
# ================================
# PRODUIT
# ================================
class Produit(models.Model):

    TYPE_PRODUIT = [
        ('simple', 'Simple'),
        ('variable', 'Variable'),
    ]
    ETAT_STOCK = [
        ('en stock', 'En stock'),
        ('rupture stock', 'Rupture de stock'),
        ('sur commande', 'Sur commande'),
    ]
    STATUS_RECOMMANDATION = [
        ('en_vedette', 'En vedette'),
        ('recommande', 'Est recommandé'),
        ('publie', 'Publié'),
    ]

    nom = models.CharField(max_length=150, validators=[MinLengthValidator(1)])
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True)
    sku = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        error_messages={
            'null': 'Le SKU ne doit pas être null',
            'unique': "Le SKU doit être unique"
        }
    )
    type_produit = models.CharField(max_length=50, choices=TYPE_PRODUIT)

    nom_vendeur = models.CharField(max_length=150, blank=True, null=True)
    description_courte = models.TextField(max_length=1500, blank=False, null=False, default="...")
    description_longue = models.TextField(max_length=5000, blank=False, null=False, default="...")

    prix_fournisseur = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0, message="Le prix fournisseur ne peut pas être négatif")],
        help_text="Prix d'achat du produit chez le fournisseur"
    )
    prix_promo = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_vente = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, help_text="Prix de vente calculé automatiquement")

    quantite = models.IntegerField(default=10)
    etat_stock = models.CharField(max_length=50, choices=ETAT_STOCK, default="en_stock")

    largeur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    longueur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    poids = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hauteur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    superficie = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    taille = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    materiau = models.CharField(max_length=150, blank=True, null=True)
    est_publie = models.BooleanField(default=True)
    est_original = models.BooleanField(default=True)
    caracteristiques = models.JSONField(default=dict, blank=True, null=True)
    livraison_gratuite=models.BooleanField(default=False)

    status = models.CharField(max_length=50, choices=STATUS_RECOMMANDATION, default="publie")

    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name="produits")
    sous_categorie = models.ForeignKey(SubCategorie, blank=True, null=True, on_delete=models.CASCADE, related_name="produits")
    etiquette = models.ForeignKey(Etiquette, on_delete=models.CASCADE, related_name="produits")

    image_principale = models.ImageField(upload_to="produits/principales/", null=True, blank=True)

    vues = models.PositiveIntegerField(default=0)
    nombres_ventes = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ================================
    # Méthodes
    # ================================
    def __str__(self):
        return f"{self.nom} ({self.type_produit})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        if not self.sku:
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)

    def generate_sku(self, length: int = 6) -> str:
        """Génère un SKU unique basé sur le nom du produit et un suffixe aléatoire"""
        prefix = slugify(self.nom)[:3].upper()
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        return f"{prefix}-{suffix}"

    def clean(self):
        if self.prix_promo and self.prix_vente and self.prix_promo > self.prix_vente:
            raise ValidationError("Le prix promo ne peut pas être supérieur au prix de vente")

    def increment_views(self):
        self.vues += 1
        self.save(update_fields=['vues'])


# ================================
# IMAGES
# ================================
class ImageProduit(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="produits/images/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Image du produit {self.produit.nom}"


# ================================
# PRODUIT VARIABLE
# ================================
class ProduitVariable(models.Model):
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name="variantes"
    )
    prix_fournisseur = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_vente = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    prix_promo = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    quantite = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.prix_vente:
            self.prix_vente = self.prix_fournisseur * 1.2
        super().save(*args, **kwargs)

    def __str__(self):
        attrs = ", ".join([str(val.attribut) for val in self.attributs.all()])
        return f"{self.produit.nom} ({attrs})"


class ProduitVariableAttribut(models.Model):
    produit_variable = models.ForeignKey(
        ProduitVariable,
        on_delete=models.CASCADE,
        related_name="attributs"
    )
    attribut = models.ForeignKey(
        Attribut,
        on_delete=models.CASCADE,
        related_name="variantes"
    )

    class Meta:
        unique_together = ('produit_variable', 'attribut')

    def __str__(self):
        return f"{self.produit_variable} - {self.attribut}"



class ProduitVariableImage(models.Model):
    produit_variable = models.ForeignKey(ProduitVariable, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="produits/variantes/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Image de la variante {self.produit_variable}"


# ================================
# AVIS PRODUIT
# ================================
class AvisProduit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="avis")
    texte = models.TextField(max_length=1500)
    note = models.PositiveIntegerField(default=5)  # 1 à 5 étoiles

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Avis de {self.user} sur {self.produit.nom} : {self.texte[:20]}..."

class Panier(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="utilisateur_detenteur_du_panier",help_text="Utilisateur propriétaire du panier")
    actif = models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.user.username}..."

class ContenuPanier(models.Model):
    panier=models.ForeignKey(Panier,on_delete=models.CASCADE,related_name="contenu")
    produit=models.ForeignKey(Produit,on_delete=models.CASCADE,related_name="contenus_panier")
    produit_variable=models.ForeignKey(ProduitVariable,on_delete=models.CASCADE,related_name="produit_variable",null=True,blank=True)
    attribut_valeur=models.ForeignKey(Attribut,on_delete=models.CASCADE,related_name="Valeur_d_attribut",null=True,blank=True)
    quantite=models.IntegerField(default=1)
    is_variable=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.panier}..."

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

class Commande(models.Model):
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('acceptee', 'Acceptée'),
        ('preparee', 'Préparée'),
        ('expediee', 'Expédiée'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commandes")
    
    panier = models.ForeignKey(Panier, on_delete=models.SET_NULL, blank=True, null=True)

    numero = models.CharField(max_length=50, unique=True, help_text="Numéro unique de la commande")
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="en_attente")

    total_produits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_livraison = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    adresse_livraison = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculer_totaux(self):
        total = sum([item.sous_total() for item in self.items.all()])
        self.total_produits = total
        self.montant_total = total + self.frais_livraison
        self.save()
    
    
    def save(self, *args, **kwargs):
        if not self.numero:
            # Exemple simple avec UUID
            self.numero = str(uuid.uuid4()).split('-')[0].upper()  # CMD unique court
        if not self.adresse_livraison:
            # Si l'utilisateur a une adresse par défaut, on la récupère automatiquement
            try:
                self.adresse_livraison = self.user.adresses.get(is_default=True).adresse
            except:
                self.adresse_livraison = ""
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Commande {self.numero} - {self.acheteur.username} ({self.statut})"


class CommandeItem(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name="items")
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    produit_variable = models.ForeignKey(ProduitVariable, on_delete=models.SET_NULL, blank=True, null=True)
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)

    def sous_total(self):
        return self.quantite * self.prix_unitaire

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} (Commande {self.commande.numero})"

class Favori(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="favori_utilisateur")
    produit=models.ForeignKey(Produit,on_delete=models.CASCADE,related_name="produit_favoriser")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('user', 'produit') 




class Paiement(models.Model):
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('effectue', 'Effectué'),
        ('echoue', 'Échoué'),
    ]

    METHODE_CHOICES = [
        ('carte_bancaire', 'Carte bancaire'),
        ('paypal', 'PayPal'),
        ('virement', 'Virement bancaire'),
        ('cash_on_delivery', 'Paiement à la livraison'),
        ('orange_money', 'Orange Money'),
        ('mtn_momo', 'MTN MoMo'),
    ]

    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name="paiement")
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="en_attente")
    methode = models.CharField(max_length=30, choices=METHODE_CHOICES, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date_paiement = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Paiement {self.commande.numero} - {self.statut}"

class Livraison(models.Model):
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name="livraison")
    transporteur = models.CharField(max_length=100, blank=True, null=True)
    numero_suivi = models.CharField(max_length=100, blank=True, null=True)
    date_expedition = models.DateTimeField(blank=True, null=True)
    date_livraison = models.DateTimeField(blank=True, null=True)

    statut = models.CharField(max_length=50, default="En préparation")

    def __str__(self):
        return f"Livraison de {self.commande.numero} - {self.statut}"


class Addresse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address = models.CharField(max_length=255)
    ville = models.CharField(max_length=255)
    pays = models.CharField(max_length=255)
    telephone = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_url = models.URLField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)




class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True, blank=False, null=False, help_text="Code promotionnel unique à utiliser pour bénéficier de la remise.")
    discount_type = models.CharField(max_length=10, choices=[('fixed', 'Fixed'), ('percent', 'Percent')], default='percent', help_text="Type de remise : Fixe (montant) ou Pourcentage.")
    discount_value = models.DecimalField(max_digits=10, default=2, decimal_places=2, validators=[MinValueValidator(0)], help_text="Montant de la remise. Exemple : 10.00 pour une réduction de 10 € ou 10.00 pour une remise de 10 %.")
    max_discount = models.DecimalField(max_digits=10, default=10000, decimal_places=2, blank=True, null=True, help_text="Limite pour une remise en pourcentage. Exemple : Si la remise est de 20 %, la réduction totale ne dépassera pas ce montant.")
    minimum_order_amount = models.DecimalField(max_digits=10, default=10000, decimal_places=2, blank=True, null=True, help_text="Montant minimum de commande pour appliquer ce code promo.")
    
    # Gestion des utilisations
    max_uses = models.PositiveIntegerField(blank=True, null=True, help_text="Nombre maximum d'utilisations du code promo. Laisser vide pour un usage illimité.")
    current_uses = models.PositiveIntegerField(default=0, db_default=0, help_text="Nombre actuel d'utilisations du code promo.")
    max_uses_per_user = models.PositiveIntegerField(blank=True, null=True, help_text="Nombre maximum d'utilisations par utilisateur.")
    
    # Ciblage
    eligible_users = models.ManyToManyField(User, blank=True, help_text="Utilisateurs éligibles pour ce code promo. Laisser vide pour tous les utilisateurs.")
    target_products = models.ManyToManyField(Produit, blank=True, help_text="Produits ciblés par ce code promo.")
    target_categories = models.ManyToManyField(Categorie, blank=True, help_text="Catégories ciblées par ce code promo.")
    
    is_active = models.BooleanField(default=True, help_text="Indique si le code promo est actuellement actif ou désactivé.")
    start_date = models.DateTimeField(help_text="Date et heure de début de validité du code promo.")
    end_date = models.DateTimeField(help_text="Date et heure de fin de validité du code promo.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date et heure de création du code promo.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Date et heure de la dernière mise à jour du code promo.")

    def clean(self):
        if self.discount_type == 'percent' and (self.discount_value < 0 or self.discount_value > 100):
            raise ValidationError({'discount_value': 'La valeur du pourcentage doit être entre 0 et 100.'})
        if self.start_date >= self.end_date:
            raise ValidationError({'start_date': 'La date de début doit être avant la date de fin.'})
        if self.max_uses and self.current_uses > self.max_uses:
            raise ValidationError({'current_uses': 'Le nombre d\'utilisations actuelles ne peut pas dépasser le maximum autorisé.'})

    def is_valid(self):
        from django.utils.timezone import now
        return (
            self.is_active and 
            self.start_date <= now() <= self.end_date and
            (self.max_uses is None or self.current_uses < self.max_uses)
        )

    def can_be_used_by_user(self, user):
        """Vérifie si un utilisateur peut utiliser ce code promo"""
        if not self.is_valid():
            return False
        
        # Vérifier si l'utilisateur est éligible
        if self.eligible_users.exists() and user not in self.eligible_users.all():
            return False
        
        # Vérifier le nombre d'utilisations par utilisateur
        if self.max_uses_per_user:
            user_uses = PromoCodeUsage.objects.filter(promo_code=self, user=user).count()
            if user_uses >= self.max_uses_per_user:
                return False

        return True

    def get_usage_stats(self):
        """Retourne les statistiques d'utilisation"""
        return {
            'total_uses': self.current_uses,
            'max_uses': self.max_uses,
            'remaining_uses': self.max_uses - self.current_uses if self.max_uses else None,
            'usage_percentage': (self.current_uses / self.max_uses * 100) if self.max_uses else None,
            'unique_users': PromoCodeUsage.objects.filter(promo_code=self).values('user').distinct().count()
        }

    def __str__(self):
        return f'Code : {self.code} - Type : {self.discount_type} - Value : {self.discount_value}'

class PromoCodeUsage(models.Model):
    """Modèle pour suivre l'utilisation des codes promo"""
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Commande, on_delete=models.CASCADE, blank=True, null=True)
    used_at = models.DateTimeField(auto_now_add=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, help_text="Montant de la remise appliquée")

    class Meta:
        pass
        #unique_together = ['promo_code', 'order']  # Un code promo ne peut être utilisé qu'une fois par commande

    def __str__(self):
        return f'{self.user} - {self.promo_code.code} - {self.used_at}'