import secrets
import string
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import IntegrityError, models, transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import slugify

# Create your models here.

# Marge appliquée sur le prix fournisseur quand aucun prix de vente n'est fourni
MARGE_PAR_DEFAUT = Decimal("1.20")
DEUX_DECIMALES = Decimal("0.01")
OTP_VALIDITE_MINUTES = 5


def arrondir_prix(valeur):
    return Decimal(valeur).quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


def generer_slug_unique(instance, valeur, champ="slug", max_length=50):
    """Génère un slug unique pour le modèle de l'instance (ajoute -2, -3... si besoin)."""
    base = slugify(valeur)[: max_length - 6] or "item"
    slug = base
    compteur = 2
    qs = type(instance).objects.exclude(pk=instance.pk)
    while qs.filter(**{champ: slug}).exists():
        slug = f"{base}-{compteur}"
        compteur += 1
    return slug


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        # Connexion insensible à la casse : "Moussa@Gmail.com" == "moussa@gmail.com"
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username.strip()})

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'email doit être défini")
        email = self.normalize_email(email).lower()
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
    photo = models.FileField(null=True, blank=True, default=None, upload_to="profil/")
    bio = models.TextField(blank=True, null=True)
    is_confirmed = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

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
        # secrets est cryptographiquement sûr, contrairement à random
        self.otp_code = str(secrets.randbelow(900000) + 100000)
        self.save()

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=OTP_VALIDITE_MINUTES)


class Categorie(models.Model):
    GROS_CATEGORIE = [
        ('gros-oeuvres', 'Gros Oeuvres'),
        ('second-oeuvres', 'Second Oeuvres'),
        ('outillage', 'Outillage'),
        ('securité', 'Sécurité')
    ]

    nom = models.CharField(max_length=150, unique=True)
    courte_description = models.TextField(max_length=550)
    longue_description = models.TextField(max_length=1500)
    photo = models.FileField(upload_to='imageCategorie/', blank=True, null=True)
    is_parent = models.BooleanField(default=True)
    gros_categorie = models.CharField(max_length=150, choices=GROS_CATEGORIE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # NB: faute de frappe historique (updeated_at) conservée pour ne pas casser le frontend
    updeated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nom} est une catégorie"


class SubCategorie(models.Model):
    categorie_principale = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name="categorie_principale")
    nom = models.CharField(max_length=150)
    courte_description = models.TextField(max_length=550, blank=True, null=True)
    longue_description = models.TextField(max_length=1500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nom} est une sous catégorie de {self.categorie_principale.nom}"


class TypeAttribut(models.Model):

    nom = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom


class Attribut(models.Model):
    typeAttribut = models.ForeignKey(TypeAttribut, on_delete=models.CASCADE, related_name="type_d_attribut")
    valeur = models.CharField(max_length=150)
    code_Couleur = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.typeAttribut.nom}: {self.valeur}"


class Etiquette(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(max_length=1500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generer_slug_unique(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


class Vendeur(models.Model):

    nom_boutique = models.CharField(max_length=150)

    slug = models.SlugField(unique=True, blank=True)

    description = models.TextField(blank=True)

    logo = models.ImageField(
        upload_to="vendeurs/logo/",
        null=True,
        blank=True
    )

    couverture = models.ImageField(
        upload_to="vendeurs/couverture/",
        null=True,
        blank=True
    )

    telephone = models.CharField(max_length=20)

    email_commercial = models.EmailField(blank=True)

    adresse = models.TextField(blank=True)

    ville = models.CharField(max_length=100)

    pays = models.CharField(max_length=100, default="Guinée")

    est_verifie = models.BooleanField(default=False)

    actif = models.BooleanField(default=True)

    note = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generer_slug_unique(self, self.nom_boutique)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom_boutique


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

    vendeur = models.ForeignKey(
        Vendeur,
        on_delete=models.CASCADE,
        related_name="produits",
        null=True,
        blank=True
    )
    description_courte = models.TextField(max_length=1500, blank=False, null=False, default="...")
    description_longue = models.TextField(max_length=5000, blank=False, null=False, default="...")

    prix_fournisseur = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0, message="Le prix fournisseur ne peut pas être négatif")],
        help_text="Prix d'achat du produit chez le fournisseur"
    )
    prix_promo = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        validators=[MinValueValidator(0, message="Le prix promo ne peut pas être négatif")]
    )
    prix_vente = models.DecimalField(
        max_digits=15, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0, message="Le prix de vente ne peut pas être négatif")],
        help_text="Prix de vente (calculé automatiquement à partir du prix fournisseur s'il est vide)"
    )

    quantite = models.PositiveIntegerField(default=10)
    etat_stock = models.CharField(max_length=50, choices=ETAT_STOCK, default="en stock")

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
    livraison_gratuite = models.BooleanField(default=False)

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
            self.slug = generer_slug_unique(self, self.nom, max_length=150)
        if not self.sku:
            self.sku = self.generate_sku()
        if self.prix_vente is None and self.prix_fournisseur is not None:
            self.prix_vente = arrondir_prix(Decimal(self.prix_fournisseur) * MARGE_PAR_DEFAUT)
        super().save(*args, **kwargs)

    def generate_sku(self, length: int = 6) -> str:
        """Génère un SKU unique basé sur le nom du produit et un suffixe aléatoire"""
        prefix = (slugify(self.nom)[:3] or "PRD").upper()
        alphabet = string.ascii_uppercase + string.digits
        while True:
            suffix = ''.join(secrets.choice(alphabet) for _ in range(length))
            sku = f"{prefix}-{suffix}"
            if not Produit.objects.filter(sku=sku).exists():
                return sku

    def clean(self):
        erreurs = {}
        if self.prix_promo and self.prix_vente and self.prix_promo > self.prix_vente:
            erreurs['prix_promo'] = "Le prix promo ne peut pas être supérieur au prix de vente"
        if (self.sous_categorie_id and self.categorie_id
                and self.sous_categorie.categorie_principale_id != self.categorie_id):
            erreurs['sous_categorie'] = "La sous-catégorie n'appartient pas à cette catégorie"
        if erreurs:
            raise ValidationError(erreurs)

    @property
    def prix_effectif(self):
        """Prix réellement payé : le prix promo s'il est valide, sinon le prix de vente."""
        if self.prix_promo and self.prix_vente and 0 < self.prix_promo < self.prix_vente:
            return self.prix_promo
        return self.prix_vente

    def increment_views(self):
        # F() évite de perdre des vues quand plusieurs requêtes arrivent en même temps
        Produit.objects.filter(pk=self.pk).update(vues=F('vues') + 1)
        self.refresh_from_db(fields=['vues'])


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
    prix_fournisseur = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    prix_vente = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    prix_promo = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    quantite = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.prix_vente is None:
            # Decimal * float lève une TypeError : on reste en Decimal
            self.prix_vente = arrondir_prix(Decimal(self.prix_fournisseur or 0) * MARGE_PAR_DEFAUT)
        super().save(*args, **kwargs)

    def clean(self):
        if self.prix_promo and self.prix_vente and self.prix_promo > self.prix_vente:
            raise ValidationError({'prix_promo': "Le prix promo ne peut pas être supérieur au prix de vente"})

    @property
    def prix_effectif(self):
        if self.prix_promo and self.prix_vente and 0 < self.prix_promo < self.prix_vente:
            return self.prix_promo
        return self.prix_vente

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
    note = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # 1 à 5 étoiles

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Avis de {self.user} sur {self.produit.nom} : {self.texte[:20]}..."


class Panier(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="utilisateur_detenteur_du_panier", help_text="Utilisateur propriétaire du panier")
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Un seul panier actif par utilisateur (évite MultipleObjectsReturned)
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(actif=True),
                name='un_seul_panier_actif_par_user',
            ),
        ]

    @classmethod
    def panier_actif(cls, user):
        try:
            with transaction.atomic():
                panier, _ = cls.objects.get_or_create(user=user, actif=True)
        except IntegrityError:
            # Deux requêtes simultanées ont créé le panier : on récupère celui qui a gagné
            panier = cls.objects.get(user=user, actif=True)
        return panier

    def __str__(self):
        return f"Panier de {self.user.email}"


class ContenuPanier(models.Model):
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name="contenu")
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="contenus_panier")
    produit_variable = models.ForeignKey(ProduitVariable, on_delete=models.CASCADE, related_name="produit_variable", null=True, blank=True)
    attributs = models.ManyToManyField(Attribut, related_name="contenus_panier", blank=True)
    quantite = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_variable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # is_variable est toujours cohérent avec la présence d'une variante
        self.is_variable = self.produit_variable_id is not None
        super().save(*args, **kwargs)

    @property
    def prix_unitaire(self):
        if self.produit_variable_id:
            return self.produit_variable.prix_effectif
        return self.produit.prix_effectif

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} ({self.panier})"


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

    total_produits = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    frais_livraison = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    adresse_livraison = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculer_totaux(self):
        total = sum((item.sous_total() for item in self.items.all()), Decimal("0"))
        self.total_produits = arrondir_prix(total)
        self.montant_total = arrondir_prix(total + (self.frais_livraison or 0))
        self.save(update_fields=['total_produits', 'montant_total', 'updated_at'])

    @staticmethod
    def generer_numero():
        while True:
            numero = secrets.token_hex(4).upper()
            if not Commande.objects.filter(numero=numero).exists():
                return numero

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generer_numero()
        if not self.adresse_livraison and self.user_id:
            # Si l'utilisateur a une adresse par défaut, on la récupère automatiquement
            adresse = self.user.addresses.filter(is_default=True).first()
            if adresse:
                self.adresse_livraison = f"{adresse.address}, {adresse.ville}, {adresse.pays}"
                if self.latitude is None and self.longitude is None:
                    self.latitude = adresse.latitude
                    self.longitude = adresse.longitude
            else:
                self.adresse_livraison = ""
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Commande {self.numero} - {self.user.email} ({self.statut})"


class CommandeItem(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name="items")
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    produit_variable = models.ForeignKey(ProduitVariable, on_delete=models.SET_NULL, blank=True, null=True)
    quantite = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    attributs = models.ManyToManyField(Attribut, related_name="lesattributs", blank=True)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    def sous_total(self):
        return self.quantite * (self.prix_unitaire or Decimal("0"))

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} (Commande {self.commande.numero})"


class Favori(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favori_utilisateur")
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="produit_favoriser")
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
    montant = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
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

    def clean(self):
        if self.date_expedition and self.date_livraison and self.date_livraison < self.date_expedition:
            raise ValidationError({'date_livraison': "La date de livraison ne peut pas précéder la date d'expédition"})

    def __str__(self):
        return f"Livraison de {self.commande.numero} - {self.statut}"


class Addresse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address = models.CharField(max_length=255)
    ville = models.CharField(max_length=255)
    pays = models.CharField(max_length=255)
    telephone = models.CharField(max_length=255)
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    location_url = models.URLField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_default:
                # Une seule adresse par défaut par utilisateur
                Addresse.objects.filter(user_id=self.user_id, is_default=True).exclude(pk=self.pk).update(is_default=False)
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address}, {self.ville} ({self.user})"


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
        if self.discount_type == 'percent' and self.discount_value is not None and not (0 <= self.discount_value <= 100):
            raise ValidationError({'discount_value': 'La valeur du pourcentage doit être entre 0 et 100.'})
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({'start_date': 'La date de début doit être avant la date de fin.'})
        if self.max_uses and self.current_uses > self.max_uses:
            raise ValidationError({'current_uses': 'Le nombre d\'utilisations actuelles ne peut pas dépasser le maximum autorisé.'})

    def is_valid(self):
        return (
            self.is_active and
            self.start_date <= timezone.now() <= self.end_date and
            (self.max_uses is None or self.current_uses < self.max_uses)
        )

    def can_be_used_by_user(self, user):
        """Vérifie si un utilisateur peut utiliser ce code promo"""
        if not self.is_valid():
            return False

        # Vérifier si l'utilisateur est éligible
        if self.eligible_users.exists() and not self.eligible_users.filter(pk=user.pk).exists():
            return False

        # Vérifier le nombre d'utilisations par utilisateur
        if self.max_uses_per_user:
            user_uses = PromoCodeUsage.objects.filter(promo_code=self, user=user).count()
            if user_uses >= self.max_uses_per_user:
                return False

        return True

    def calculer_remise(self, montant):
        """Retourne le montant de la remise applicable sur `montant` (0 si non applicable)."""
        montant = Decimal(montant)
        if self.minimum_order_amount and montant < self.minimum_order_amount:
            return Decimal("0")
        if self.discount_type == 'percent':
            remise = montant * self.discount_value / Decimal("100")
            if self.max_discount:
                remise = min(remise, self.max_discount)
        else:
            remise = self.discount_value
        return arrondir_prix(min(remise, montant))

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

    def __str__(self):
        return f'{self.user} - {self.promo_code.code} - {self.used_at}'


class ProjetDevis(models.Model):

    TYPE_PROJET = [
        ('maison', 'Maison'),
        ('immeuble', 'Immeuble'),
        ('commerce', 'Commerce'),
        ('entrepot', 'Entrepôt'),
    ]

    TYPE_STRUCTURE = [
        ('beton', 'Béton armé'),
        ('brique', 'Brique'),
        ('mixte', 'Mixte'),
    ]

    TYPE_SOL = [
        ('stable', 'Sol stable'),
        ('sableux', 'Sol sableux'),
        ('argileux', 'Sol argileux'),
        ('inconnu', 'Inconnu'),
    ]

    NIVEAU_FINITION = [
        ('basique', 'Basique'),
        ('moyen', 'Moyen'),
        ('haut', 'Haut standing'),
    ]

    TYPE_TOITURE = [
        ('tole', 'Tôle'),
        ('dalle', 'Dalle béton'),
        ('tuile', 'Tuile'),
    ]

    OBJECTIF = [
        ('construction', 'Construction immédiate'),
        ('planification', 'Planification'),
        ('estimation', 'Estimation simple'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projets")

    nom_projet = models.CharField(max_length=255, blank=True, null=True)
    ville = models.CharField(max_length=150)
    quartier = models.CharField(max_length=150, blank=True, null=True)

    type_projet = models.CharField(max_length=50, choices=TYPE_PROJET)
    surface = models.FloatField(validators=[MinValueValidator(1, message="La surface doit être d'au moins 1 m²")])
    nombre_etages = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])

    structure = models.CharField(max_length=50, choices=TYPE_STRUCTURE)
    type_sol = models.CharField(max_length=50, choices=TYPE_SOL, default="inconnu")
    finition = models.CharField(max_length=50, choices=NIVEAU_FINITION)
    toiture = models.CharField(max_length=50, choices=TYPE_TOITURE)

    options = models.JSONField(default=list, blank=True)  # garage, plomberie...

    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    objectif = models.CharField(max_length=50, choices=OBJECTIF)

    prix_estime = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Projet {self.nom_projet or self.id} - {self.user.email}"


class MateriauDevis(models.Model):

    projet = models.ForeignKey(ProjetDevis, on_delete=models.CASCADE, related_name="materiaux")

    produit = models.ForeignKey(Produit, on_delete=models.SET_NULL, null=True, blank=True)

    nom = models.CharField(max_length=150)
    quantite = models.FloatField(validators=[MinValueValidator(0)])
    unite = models.CharField(max_length=50)  # kg, m3, unité

    prix_unitaire = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    prix_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.prix_total is None and self.prix_unitaire is not None and self.quantite is not None:
            self.prix_total = arrondir_prix(Decimal(str(self.quantite)) * self.prix_unitaire)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} - {self.quantite} {self.unite}"


class DemandeAppelExpert(models.Model):
    """Modèle pour gérer les demandes d'appel expert"""

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('traitee', 'Traitée'),
        ('annulee', 'Annulée'),
        ('planifiee', 'Planifiée'),
    ]

    DISPONIBILITE_CHOICES = [
        ('matin', 'Matin (9h-12h)'),
        ('apres-midi', 'Après-midi (14h-17h)'),
        ('soiree', 'Soirée (18h-20h)'),
        ('flexible', 'Flexible'),
    ]

    # Informations du demandeur
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="demandes_appel_expert"
    )
    nom = models.CharField(max_length=150)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)

    # Détails de la demande
    sujet = models.CharField(max_length=255)
    message = models.TextField()

    # Préférences de contact
    disponibilite = models.CharField(
        max_length=20,
        choices=DISPONIBILITE_CHOICES,
        default="matin"
    )
    date_appel = models.DateField(null=True, blank=True)

    # Statut et suivi
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="en_attente"
    )
    notes_interne = models.TextField(blank=True, null=True)
    date_traitement = models.DateTimeField(null=True, blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande d'appel expert"
        verbose_name_plural = "Demandes d'appel expert"

    def __str__(self):
        return f"Demande de {self.nom} - {self.sujet[:30]}"

    def marquer_traitee(self):
        """Marquer la demande comme traitée"""
        self.statut = "traitee"
        self.date_traitement = timezone.now()
        self.save()

    def marquer_planifiee(self):
        """Marquer la demande comme planifiée"""
        self.statut = "planifiee"
        self.save()

    def annuler(self):
        """Annuler la demande"""
        self.statut = "annulee"
        self.save()

    def est_en_attente(self) -> bool:
        """Vérifier si la demande est en attente"""
        return self.statut == "en_attente"

    def get_duree_attente(self):
        """Calculer le temps d'attente en heures"""
        if self.created_at:
            delta = timezone.now() - self.created_at
            return delta.total_seconds() / 3600
        return 0
